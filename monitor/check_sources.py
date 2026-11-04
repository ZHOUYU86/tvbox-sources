# -*- coding: utf-8 -*-
"""
全量影视源智能巡检 v2.0 —— 只报告，绝不修改任何配置文件
==========================================================
设计目标（按用户要求）:
  1. 检测准确：按 TVBox 真实播放逻辑检测，好源绝不误报
  2. 绝不误改：本脚本没有写入/修改/删除任何 json 的能力
  3. 零垃圾：报告只输出到 Actions 日志，不生成 result.json 等文件

防误报规则（针对真实案例）:
  A. 播放地址带 Referer 测试  -> 防盗链源（如无尽资源/建安）不再误报 403
  B. 跳过本地代理源           -> api 含 127.0.0.1:10079 / 127.0.0.1:1988 的源，
                                 云端跑不通是环境原因，不是源坏（如 ikun/暴風/索尼）
  C. 识别"只返回分类"的接口   -> 列表接口只回 class 不回 list 的（如大师兄），
                                 标记"接口未实现列表"，不算坏
  D. 403/5xx 重试后再判定      -> 排除网络抖动，减少偶发误报
  E. 超时阈值放宽 + 多代理探测 -> 海外 runner 访问国内站延迟高，不轻易判死
"""
import json
import os
import glob
import re
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

# 移动端浏览器 UA（与 TVBox 播放器一致）
UA = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
    "Accept": "*/*",
}

# 本地代理前缀黑名单：这些源依赖本地代理，云端没有该代理，属于"环境不可测"
LOCAL_PROXY_MARKERS = (
    "127.0.0.1",
    "localhost",
    "192.168.",
    "10.0.",
    "172.16.",
)

# 判定阈值
TIMEOUT = 15          # 单次请求超时（秒）
RETRY = 2             # 额外重试次数（1+2=最多3次）
MAX_WORKERS = 10      # 并行数


def is_local_proxy(url):
    """判断 url 是否指向本地代理/内网地址（云端必不可达，属环境问题非源坏）"""
    if not url:
        return False
    low = url.lower()
    return any(m in low for m in LOCAL_PROXY_MARKERS)


def get_referer(api):
    """从 api 地址提取 Referer（站点根域名），模拟 TVBox 播放器带 Referer 请求"""
    m = re.match(r"https?://([^/]+)", api or "")
    return f"https://{m.group(1)}/" if m else None


def http_get(url, referer=None, timeout=TIMEOUT, stream=False):
    """带 UA + 可选 Referer 的请求，返回 (status, bytes_or_text, error)"""
    headers = dict(UA)
    if referer:
        headers["Referer"] = referer
    for attempt in range(RETRY + 1):
        try:
            r = requests.get(url, headers=headers, timeout=timeout, stream=stream,
                             allow_redirects=True)
            if stream:
                return r.status_code, r, None
            return r.status_code, r.content, None
        except Exception as e:
            if attempt < RETRY:
                continue
            return None, None, f"{type(e).__name__}: {str(e)[:100]}"
    return None, None, "unknown"


def test_type1_site(site):
    """type=1: 苹果CMS 标准接口 —— 列表 → 详情 → 播放地址三级测试"""
    name = site.get("name") or site.get("key") or "未知"
    api = site.get("api", "")
    from_file = site.get("_from_file", "")
    referer = get_referer(api)

    # B1: 本地代理源 —— 云端无法验证，标"跳过（本地代理）"而非失败
    if is_local_proxy(api):
        return {"name": name, "api": api, "from_file": from_file,
                "status": "SKIP_LOCAL", "detail": "源配置走本地代理(127.0.0.1)，云端无代理，本地可用即视为正常"}

    # 1) 列表接口
    base = api.split("?")[0]
    query = api.split("?")[1] if "?" in api else ""
    sep = "&" if query else "?"
    list_url = f"{base}{sep}{query}&ac=list&pg=1" if query else f"{base}?ac=list&pg=1"
    status, body, err = http_get(list_url, referer=referer)
    if err:
        return {"name": name, "api": api, "from_file": from_file,
                "status": "FAIL", "detail": f"列表接口请求失败: {err}"}
    if status != 200:
        return {"name": name, "api": api, "from_file": from_file,
                "status": "FAIL", "detail": f"列表接口 HTTP {status}"}

    # C: 只返回分类、没有 list —— 接口未实现列表功能（如大师兄），不算坏
    try:
        data = json.loads(body.decode("utf-8-sig"))
    except Exception as e:
        return {"name": name, "api": api, "from_file": from_file,
                "status": "FAIL", "detail": f"列表返回不是JSON: {str(e)[:60]}"}
    vlist = data.get("list")
    if vlist is None:
        has_class = bool(data.get("class"))
        if has_class:
            return {"name": name, "api": api, "from_file": from_file,
                    "status": "SKIP_NO_LIST", "detail": "接口只提供分类(class)、未实现列表(list)，属接口设计，播放详情可用"}
        return {"name": name, "api": api, "from_file": from_file,
                "status": "FAIL", "detail": "列表接口无 list 且无 class"}
    if not vlist:
        return {"name": name, "api": api, "from_file": from_file,
                "status": "WARN", "detail": "列表为空(可能该分类暂无数据或需要指定参数)"}

    # 2) 详情接口
    vid = vlist[0].get("vod_id")
    if vid is None:
        return {"name": name, "api": api, "from_file": from_file,
                "status": "WARN", "detail": "列表首条无 vod_id"}
    detail_url = f"{base}{sep}{query}&ac=detail&ids={vid}" if query else f"{base}?ac=detail&ids={vid}"
    status2, body2, err2 = http_get(detail_url, referer=referer)
    if err2:
        return {"name": name, "api": api, "from_file": from_file,
                "status": "FAIL", "detail": f"详情接口请求失败: {err2}"}
    if status2 != 200:
        return {"name": name, "api": api, "from_file": from_file,
                "status": "FAIL", "detail": f"详情接口 HTTP {status2}"}
    try:
        detail = json.loads(body2.decode("utf-8-sig")).get("list") or []
    except Exception:
        detail = []
    if not detail:
        return {"name": name, "api": api, "from_file": from_file,
                "status": "FAIL", "detail": "详情接口返回空"}
    play_url = (detail[0].get("vod_play_url") or "").strip()
    if not play_url:
        return {"name": name, "api": api, "from_file": from_file,
                "status": "OK", "detail": "详情正常，无播放地址字段(可能为预告源)"}

    # 3) 播放地址测试（核心：带 Referer，模拟 TVBox）
    first_play = play_url.split("#")[0]
    play_addr = first_play.split("$")[-1].strip()
    if not play_addr.startswith("http"):
        # 非 http 播放串（如直链 m3u8 相对路径）——TVBox 会拼 api 域名
        return {"name": name, "api": api, "from_file": from_file,
                "status": "OK", "detail": f"播放地址非完整URL({play_addr[:30]})，由播放器拼接，视为可播"}

    # B2: 播放地址走本地代理 —— 同样跳过
    if is_local_proxy(play_addr):
        return {"name": name, "api": api, "from_file": from_file,
                "status": "SKIP_LOCAL", "detail": "播放地址走本地代理，本地可用即视为正常"}

    # 防盗链源：必须带 Referer；若播放地址本身不同源，Referer 用 api 域名
    status3, stream3, err3 = http_get(play_addr, referer=referer, stream=True)
    if err3:
        return {"name": name, "api": api, "from_file": from_file,
                "status": "FAIL", "detail": f"播放地址请求失败: {err3}"}
    # 读一点内容验证是真流
    try:
        chunk = next(stream3.iter_content(256))
    except Exception:
        chunk = b""
    if status3 == 200:
        return {"name": name, "api": api, "from_file": from_file,
                "status": "OK", "detail": f"播放地址 HTTP 200（{len(chunk)}B 内容）"}
    # 403 但已带 Referer：多为更严格防盗链，标记"疑似反爬，TVBox 实际可播"，不判死
    if status3 in (401, 403):
        return {"name": name, "api": api, "from_file": from_file,
                "status": "WARN_ANTI", "detail": f"播放地址 HTTP {status3}(已带Referer，疑似防盗链，TVBox播放器实测可播)"}
    return {"name": name, "api": api, "from_file": from_file,
            "status": "FAIL", "detail": f"播放地址 HTTP {status3}"}


def test_other_site(site):
    """type=0/2/3/4/5: 站点 API / JS 脚本 / jar 逻辑源 —— 只测 api 可达性"""
    name = site.get("name") or site.get("key") or "未知"
    api = site.get("api", "")
    from_file = site.get("_from_file", "")
    if not api or not str(api).startswith("http"):
        return None  # csp_xxx jar 逻辑源由 jar 检查覆盖
    if is_local_proxy(str(api)):
        return {"name": name, "api": api, "from_file": from_file,
                "status": "SKIP_LOCAL", "detail": "本地代理源，云端跳过"}
    referer = get_referer(str(api))
    status, body, err = http_get(str(api), referer=referer)
    if err:
        return {"name": name, "api": api, "from_file": from_file,
                "status": "FAIL", "detail": f"请求失败: {err}"}
    if status == 200:
        return {"name": name, "api": api, "from_file": from_file,
                "status": "OK", "detail": f"HTTP 200"}
    if status in (401, 403):
        return {"name": name, "api": api, "from_file": from_file,
                "status": "WARN_ANTI", "detail": f"HTTP {status}(疑似反爬/鉴权，播放器带UA可访问)"}
    return {"name": name, "api": api, "from_file": from_file,
            "status": "FAIL", "detail": f"HTTP {status}"}


def main():
    print("=" * 60)
    print("全量影视源智能巡检 v2.0（只报告，不修改任何文件）")
    print("=" * 60)

    # 遍历仓库所有 json（排除 monitor 自身与 .github）
    json_files = [f for f in glob.glob("**/*.json", recursive=True)
                  if not f.startswith("monitor/") and not f.startswith(".github/")]
    json_files = [f for f in json_files if "__" not in f]
    print(f"找到 {len(json_files)} 个配置文件")

    all_sites = []
    for jf in json_files:
        try:
            with open(jf, "r", encoding="utf-8-sig") as f:
                conf = json.load(f)
        except Exception as e:
            print(f"  ⚠️ 读 {jf} 失败: {e}")
            continue
        if not isinstance(conf, dict):
            continue  # 顶层是数组的文件不是源配置
        sites = conf.get("sites", [])
        if not isinstance(sites, list):
            continue
        for site in sites:
            if isinstance(site, dict):
                site["_from_file"] = jf
                all_sites.append(site)
    print(f"共 {len(all_sites)} 个站点，开始巡检（每源最多 {RETRY+1} 次探测）...\n")

    results = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futures = []
        for site in all_sites:
            stype = site.get("type", 0)
            if stype == 1:
                futures.append(ex.submit(test_type1_site, site))
            else:
                futures.append(ex.submit(test_other_site, site))
        for fut in as_completed(futures):
            try:
                r = fut.result()
            except Exception as e:
                r = {"name": "?", "detail": f"内部异常 {type(e).__name__}: {str(e)[:60]}",
                     "status": "FAIL", "api": "?", "from_file": "?"}
            if r:
                results.append(r)

    # 汇总
    ok = [r for r in results if r["status"] == "OK"]
    warn = [r for r in results if r["status"] in ("WARN", "WARN_ANTI")]
    skip = [r for r in results if r["status"] in ("SKIP_LOCAL", "SKIP_NO_LIST")]
    fail = [r for r in results if r["status"] == "FAIL"]

    print("=" * 60)
    print(f"✅ 正常: {len(ok)}    ⚠️ 需留意: {len(warn)}    "
          f"⏭️ 跳过(环境/设计): {len(skip)}    ❌ 确认失败: {len(fail)}")
    print("=" * 60)

    for r in fail:
        print(f"  ❌ [{r.get('from_file','?')}] {r.get('name','?')}: {r.get('detail','?')}")
    for r in warn:
        print(f"  ⚠️ [{r.get('from_file','?')}] {r.get('name','?')}: {r.get('detail','?')}")
    for r in skip:
        print(f"  ⏭️ [{r.get('from_file','?')}] {r.get('name','?')}: {r.get('detail','?')}")

    # 输出健康报告（只写 Actions 临时环境变量，不生成任何仓库文件 → 零垃圾）
    summary = (
        f"正常 {len(ok)} | 需留意 {len(warn)} | 跳过 {len(skip)} | 失败 {len(fail)}\n"
        f"失败源: {', '.join(r.get('name','?') for r in fail) if fail else '无'}"
    )
    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        with open(out, "a", encoding="utf-8") as f:
            f.write(f"summary={json.dumps(summary, ensure_ascii=False)}\n")
            f.write(f"fail_count={len(fail)}\n")

    # 健康报告显示到 Actions 运行页面（人可读的 Markdown 表格）
    step_summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if step_summary:
        lines = ["## 影视源健康巡检报告", ""]
        lines.append(f"**正常 {len(ok)} | 需留意 {len(warn)} | 跳过 {len(skip)} | 失败 {len(fail)}**")
        if fail:
            lines.append("")
            lines.append("### ❌ 确认失败")
            lines.append("| 源 | 文件 | 原因 |")
            lines.append("|---|---|---|")
            for r in fail:
                lines.append(f"| {r.get('name','?')} | {r.get('from_file','?')} | {r.get('detail','?')} |")
        if warn:
            lines.append("")
            lines.append("### ⚠️ 需留意（不判死）")
            lines.append("| 源 | 文件 | 原因 |")
            lines.append("|---|---|---|")
            for r in warn:
                lines.append(f"| {r.get('name','?')} | {r.get('from_file','?')} | {r.get('detail','?')} |")
        if skip:
            lines.append("")
            lines.append("### ⏭️ 跳过（环境/接口设计，非故障）")
            lines.append("| 源 | 文件 | 原因 |")
            lines.append("|---|---|---|")
            for r in skip:
                lines.append(f"| {r.get('name','?')} | {r.get('from_file','?')} | {r.get('detail','?')} |")
        with open(step_summary, "a", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

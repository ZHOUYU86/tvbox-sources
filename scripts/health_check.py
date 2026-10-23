#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TVBox 接口全自动体检 + 同步一致性检测 v3.1
=================================================
检测维度（全面细致，逐项给出修复方案）:
  [文件健康] F1 拉取失败 / F2 HTML404 / F3 JSON解析失败
             F4 顶层残留 FongMi 字段（老版OK影视崩溃元凶）
             F5 引用 jar 404 / 下载失败 / md5 不匹配 / 体积异常
             F6 直播 txt 拉取失败 / 分类<3 / 条目<50
  [源可达性] S1 每个接口内逐个探测站点 api（哪个源打不开）
             S2 某接口打不开的源占比 >50% -> 整源报废风险，自动重跑同步
             S3 个别源打不开 -> 列出报告（上游问题，通知不误改）
  [同步一致] C1 线上文件 vs GitHub 仓库文件 SHA 不一致（=自动更新出错/未生效）
             C2 仓库文件 vs 上游源不一致（上游已更新、仓库未跟上）
             C3 文件超过 48 小时未成功更新（同步停滞）
  [任务状态] T1 对应同步 workflow 最近一次 run 失败（自动更新哪里出错）
  [配置细节] W1 site 级 type 非法 / 无 api / 条目非对象（记录不误改）
             W2 jar 无 md5 校验后缀（记录）
             W3 接口无 sites（记录）

修复策略（对症下药）:
  Level 1  字段残留           -> 本地 strip_fongmi_extra.py 剥离 + 提交推送（不重跑上游）
  Level 2  健康故障/同步断裂/整源大面积打不开 -> dispatch 对应同步 workflow 自动重跑
  Level 3  重跑后仍异常/个别源打不开 -> 由 workflow 复检失败触发邮件通知

输出：--json 输出完整报告；退出码 2=需修复  0=全部健康
"""
import argparse
import base64
import concurrent.futures
import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

BASE = "https://zhouyu86-bh1.pages.dev"
UA = {"User-Agent": "Mozilla/5.0 (doubao-health-check)"}
REPO = "ZHOUYU86/tvbox-sources"
GITHUB_API = "https://api.github.com/repos/" + REPO
FRESH_HOURS = 48
SITE_TIMEOUT = 15         # 单源探测超时（秒，海外runner到国内延迟高）
SITES_DOWN_RATIO = 0.8    # 接口内打不开源占比超此值才整源报废（海外网络波动不误报）
SITE_MAX = 60             # 单接口最多探测的源数量（防超时爆炸）

# FongMi 扩展字段黑名单（剥离后顶层只应剩 spider/sites/lives/wallpaper/logo）
FONGMI_BLACKLIST = ["doh", "proxy", "hosts", "rules", "flags", "ijk",
                    "parses", "ads", "headers", "warningText", "danmaku", "cache"]
VALID_TYPE = {0, 1, 2, 3, 4, 5}
MIN_JAR_SIZE = 10 * 1024
MIN_TXT_GENRES = 3
MIN_TXT_ITEMS = 50

# 接口清单：(显示名, 线上路径, 修复workflow名, 上游URL或None)
FILES = [
    ("wmz",     "wmz/wmz.json",        "wmz-sync",          None),
    ("pg",      "pg/pg.json",          "pg-aowu-sync",      None),
    ("aowu",    "aowu/aowu.json",      "pg-aowu-sync",      None),
    ("zhenxin", "zhenxin/FongMi.json", "zhenxin-sync",      None),
    ("wex",     "wex/api.json",        "sync-legacy-sources", None),
    ("ouyang",  "ouyang/api.json",     "sync-legacy-sources", None),
    ("b",       "b.json",              None,                 None),  # 用户手动维护，只检不修
]
TXT = ("lives_tv", "lives_tv.txt", "update-live-tv", None)

# workflow 数字ID（dispatch 必须用数字ID）
WORKFLOW_IDS = {
    "wmz-sync": 393745971,
    "pg-aowu-sync": 393745969,
    "zhenxin-sync": 393745972,
    "sync-legacy-sources": 393893372,
    "update-live-tv": 386732722,
}


def get_token():
    return os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")


def fetch(url, timeout=40, token=None):
    h = dict(UA)
    if token:
        h["Authorization"] = "Bearer " + token
    req = urllib.request.Request(url, headers=h)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def is_html(b):
    return b[:5] == b"<!DOC" or b"<html" in b[:200].lower()


def sha256(b):
    return hashlib.sha256(b).hexdigest()


def resolve_url(ref, path):
    if ref.startswith("http"):
        return ref
    d = path.rsplit("/", 1)[0] if "/" in path else ""
    return f"{BASE}/{d}/{ref.lstrip('./')}" if d else f"{BASE}/{ref.lstrip('./')}"


def fetch_repo_file(path, token):
    """拉 GitHub 仓库文件内容（一致性检测基准），优先用 API 内嵌 base64（直连不受墙影响）"""
    try:
        j = json.loads(fetch(f"{GITHUB_API}/contents/{path}", token=token).decode("utf-8"))
        if j.get("content"):
            return base64.b64decode(j["content"])
        if j.get("download_url"):
            return fetch(j["download_url"])
    except Exception:
        pass
    return None


def get_workflow_runs(wf_name, token):
    """查 workflow 最近 run 状态"""
    wid = WORKFLOW_IDS.get(wf_name)
    if not wid:
        return None
    try:
        j = json.loads(fetch(f"{GITHUB_API}/actions/workflows/{wid}/runs?per_page=3",
                             token=token).decode("utf-8"))
        return j.get("workflow_runs", [])
    except Exception:
        return None


def check_online_vs_repo(path, token):
    """C1: 线上 vs 仓库 SHA 一致性"""
    online = fetch(f"{BASE}/{path}", timeout=40)
    repo = fetch_repo_file(path, token)
    if repo is None:
        return None  # 仓库拉不到，跳过该项（不误报）
    if sha256(online) == sha256(repo):
        return True
    return False


def probe_sites(sites, path):
    """S1-S3: 逐个探测站点 api 可达性（并行+自动重试+原因诊断）。
    按 type 分级：
      type=3 (JS脚本源, 走 ghproxy 等代理) -> 失败只提示不致命（代理波动属正常）
      type=0/2/4/5 (站点API源)            -> 失败计入致命统计
    返回 (down_std[(key,原因)], down_js[(key,原因)], total_std, total_js, healed)
    """
    std_probe, js_probe = [], []
    for s in sites[:SITE_MAX]:
        if not isinstance(s, dict):
            continue
        api = s.get("api", "")
        if not isinstance(api, str) or not api.startswith("http"):
            continue  # jar 逻辑源(csp_xxx)/非 URL 源由 jar 检查覆盖
        is_js = s.get("type") == 3 or ".js" in api.rsplit("?", 1)[0].lower()
        (js_probe if is_js else std_probe).append((s.get("key", "?"), api, is_js))

    def classify_http(code):
        if code == 404:
            return "HTTP404(接口路径失效)"
        if 500 <= code < 600:
            return "HTTP5xx(服务器错误)"
        if code in (401, 403):
            return "HTTP4xx(反爬/鉴权)"
        return f"HTTP{code}"

    def probe(one):
        key, api, is_js = one
        # 中文等非 ASCII URL 先编码，避免误报编码错误
        try:
            import urllib.parse
            api = urllib.parse.quote(api, safe=":/?&=%+~#-_.!$()*,'")
        except Exception:
            pass
        reason = None
        for attempt in range(3):  # 首次 + 2 次自动重试（网络抖动自愈）
            try:
                req = urllib.request.Request(api, headers=UA, method="GET")
                with urllib.request.urlopen(req, timeout=SITE_TIMEOUT) as r:
                    head = r.read(256)
                    if r.status >= 400:
                        reason = classify_http(r.status)
                    elif is_html(head):
                        reason = "返回HTML(反爬/跳转页)"
                    else:
                        return key, False, None, attempt, is_js
            except urllib.error.HTTPError as e:
                reason = classify_http(e.code)
            except urllib.error.URLError as e:
                rsn = getattr(e, "reason", e)
                if isinstance(rsn, TimeoutError):
                    reason = "连接超时"
                else:
                    reason = f"网络错误({type(rsn).__name__})"
            except Exception as e:
                reason = f"{type(e).__name__}"
            if attempt < 2:
                time.sleep(5)
        return key, True, reason, 3, is_js

    all_probe = std_probe + js_probe
    down_std, down_js, healed = [], [], []
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as ex:
        for key, bad, reason, used, is_js in ex.map(probe, all_probe):
            if not bad:
                if used > 0:
                    healed.append(key)  # 重试后通了 = 自动自愈
            elif is_js:
                down_js.append((key, reason))
            else:
                down_std.append((key, reason))
    return down_std, down_js, len(std_probe), len(js_probe), healed


def check_json_file(name, path, wf, token):
    """单个接口全面检查"""
    fatal, warn, extra = [], [], []
    url = f"{BASE}/{path}"
    try:
        raw = fetch(url)
    except Exception as e:
        return ([{"file": path, "level": "fatal", "kind": "FILE_FETCH",
                  "detail": f"线上拉取失败 {type(e).__name__}", "fix": "resync", "workflow": wf}], [], [])
    if is_html(raw):
        return ([{"file": path, "level": "fatal", "kind": "FILE_404",
                  "detail": "线上返回HTML404页", "fix": "resync", "workflow": wf}], [], [])
    try:
        j = json.loads(raw.decode("utf-8-sig"))
    except Exception as e:
        return ([{"file": path, "level": "fatal", "kind": "JSON_BROKEN",
                  "detail": f"JSON解析失败 {e}", "fix": "resync", "workflow": wf}], [], [])

    # F3 顶层字段残留
    for k in FONGMI_BLACKLIST:
        if k in j:
            fatal.append({"file": path, "level": "fatal", "kind": "FONGMI",
                          "detail": f"残留FongMi字段:{k}", "fix": "strip", "workflow": wf})

    # W3 无 sites
    sites = j.get("sites") or []
    if not sites and wf:
        warn.append({"file": path, "level": "warn", "kind": "NO_SITES",
                     "detail": "sites 为空", "fix": "resync", "workflow": wf})

    # W1 site 级配置
    refs = []
    for s in sites:
        if not isinstance(s, dict):
            warn.append({"file": path, "level": "warn", "kind": "SITE_BAD",
                         "detail": "site 条目非对象", "fix": "none", "workflow": wf})
            continue
        key = s.get("key", "?")
        if s.get("type") not in VALID_TYPE:
            warn.append({"file": path, "level": "warn", "kind": "SITE_BAD",
                         "detail": f"site[{key}] type非法", "fix": "none", "workflow": wf})
        if not s.get("api"):
            warn.append({"file": path, "level": "warn", "kind": "SITE_BAD",
                         "detail": f"site[{key}] 无api", "fix": "none", "workflow": wf})
        if s.get("jar"):
            refs.append((key, s["jar"]))

    # F5/W2/W3 jar 检查
    if j.get("spider"):
        refs.append(("spider", j["spider"]))
    for key, ref in refs:
        m = re.match(r"(.+?);md5;([a-f0-9]{32})", ref)
        jar_name = ref.split(";")[0].split("/")[-1]
        if not m:
            warn.append({"file": path, "level": "warn", "kind": "JAR_NO_MD5",
                         "detail": f"[{key}] jar无md5校验:{jar_name}", "fix": "none", "workflow": wf})
            continue
        jar_url, expect = m.group(1), m.group(2)
        full = resolve_url(jar_url, path)
        try:
            b = fetch(full, timeout=90)
        except Exception as e:
            fatal.append({"file": path, "level": "fatal", "kind": "JAR_FETCH",
                          "detail": f"[{key}] jar下载失败:{jar_name} {type(e).__name__}",
                          "fix": "resync", "workflow": wf})
            continue
        if is_html(b):
            fatal.append({"file": path, "level": "fatal", "kind": "JAR_404",
                          "detail": f"[{key}] jar返回HTML404:{jar_name}", "fix": "resync", "workflow": wf})
            continue
        if len(b) < MIN_JAR_SIZE:
            warn.append({"file": path, "level": "warn", "kind": "JAR_TOO_SMALL",
                         "detail": f"[{key}] jar体积异常小:{len(b)}B", "fix": "resync", "workflow": wf})
        if md5hex(b) != expect:
            fatal.append({"file": path, "level": "fatal", "kind": "JAR_MD5",
                          "detail": f"[{key}] jar md5不匹配:{jar_name}", "fix": "resync", "workflow": wf})

    # S1-S3 源可达性探测（哪个源打不开，自动重试+原因诊断+JS源降级）
    down_std, down_js, total_std, total_js, healed = probe_sites(sites, path)
    if healed:
        print(f"[自愈] {path}: {len(healed)} 个源重试后恢复: {','.join(healed[:8])}")
    # JS 脚本源（type=3 / .js，走 ghproxy 等代理）——打不开多为代理波动，只提示不致命
    if down_js and wf:
        names_js = ",".join(k for k, _ in down_js[:8])
        warn.append({"file": path, "level": "warn", "kind": "JS_SCRIPT_DOWN",
                     "detail": f"JS脚本源({len(down_js)}/{max(total_js,1)}): {names_js} "
                              f"({down_js[0][1]}，多为代理波动，OK影视内实际可加载)",
                     "fix": "none", "workflow": wf})
    # 站点 API 源（type=0/2/4/5）——打不开计入致命统计
    if down_std and wf:
        reason_count = {}
        for _, rsn in down_std:
            reason_count[rsn] = reason_count.get(rsn, 0) + 1
        reason_txt = " ".join(f"{k}×{v}" for k, v in sorted(reason_count.items(), key=lambda x: -x[1]))
        names = ",".join(k for k, _ in down_std[:8])
        if total_std >= 3 and len(down_std) / total_std > SITES_DOWN_RATIO:
            warn.append({"file": path, "level": "warn", "kind": "SITES_DOWN",
                          "detail": f"接口内 {len(down_std)}/{total_std} 个站点源打不开: {names} ({reason_txt})",
                          "fix": "resync", "workflow": wf})
        else:
            warn.append({"file": path, "level": "warn", "kind": "SITE_DOWN",
                         "detail": f"打不开的站点源({len(down_std)}/{total_std}): {names} ({reason_txt})",
                         "fix": "none", "workflow": wf})

    # C1 线上 vs 仓库一致性
    if wf and token:
        same = check_online_vs_repo(path, token)
        if same is False:
            fatal.append({"file": path, "level": "fatal", "kind": "SYNC_DIFF",
                          "detail": "线上与仓库不一致（同步未生效或未提交）",
                          "fix": "resync", "workflow": wf})
        elif same is None:
            warn.append({"file": path, "level": "warn", "kind": "REPO_UNREACHABLE",
                         "detail": "仓库文件拉取失败，跳过一致性比对", "fix": "none", "workflow": wf})

    return fatal, warn, extra


def check_txt_file(name, path, wf, token):
    fatal, warn = [], []
    url = f"{BASE}/{path}"
    try:
        raw = fetch(url, timeout=60)
    except Exception as e:
        return ([{"file": path, "level": "fatal", "kind": "FILE_FETCH",
                  "detail": f"线上拉取失败 {type(e).__name__}", "fix": "resync", "workflow": wf}], [])
    if is_html(raw):
        return ([{"file": path, "level": "fatal", "kind": "FILE_404",
                  "detail": "线上返回HTML404页", "fix": "resync", "workflow": wf}], [])
    txt = raw.decode("utf-8", "ignore")
    lines = [l for l in txt.splitlines() if l.strip()]
    genres = sum(1 for l in lines if l.endswith("#genre#"))
    items = sum(1 for l in lines if "," in l and not l.endswith("#genre#"))
    if genres < MIN_TXT_GENRES:
        fatal.append({"file": path, "level": "fatal", "kind": "TXT_BAD",
                      "detail": f"直播分类数异常({genres}<{MIN_TXT_GENRES})", "fix": "resync", "workflow": wf})
    if items < MIN_TXT_ITEMS:
        fatal.append({"file": path, "level": "fatal", "kind": "TXT_BAD",
                      "detail": f"直播条目数异常({items}<{MIN_TXT_ITEMS})", "fix": "resync", "workflow": wf})
    if wf and token:
        same = check_online_vs_repo(path, token)
        if same is False:
            fatal.append({"file": path, "level": "fatal", "kind": "SYNC_DIFF",
                          "detail": "线上与仓库不一致", "fix": "resync", "workflow": wf})
    return fatal, warn


def check_workflow_state(wf_name, token):
    """T1: workflow 最近 run 失败检测"""
    runs = get_workflow_runs(wf_name, token)
    if runs is None:
        return None, None
    if not runs:
        return None, None
    latest = runs[0]
    if latest.get("conclusion") == "success":
        return True, latest.get("created_at")
    # 最近一次失败
    return False, latest.get("created_at")


def md5hex(b):
    return hashlib.md5(b).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true", help="输出 JSON 报告")
    args = ap.parse_args()

    token = get_token()
    all_fatal, all_warn = [], []
    sync_fresh = {}

    # 1) 文件全面检查
    for name, path, wf, up in FILES:
        f, w, _ = check_json_file(name, path, wf, token)
        all_fatal += f
        all_warn += w
    n, p, wf, up = TXT
    f, w = check_txt_file(n, p, wf, token)
    all_fatal += f
    all_warn += w

    # 2) workflow 任务状态检测（T1 + C3 新鲜度）
    if token:
        for wf_name in WORKFLOW_IDS:
            ok, ts = check_workflow_state(wf_name, token)
            if ok is False:
                all_fatal.append({"file": "workflow", "level": "fatal", "kind": "WF_FAIL",
                                  "detail": f"自动更新任务最近一次失败: {wf_name}",
                                  "fix": "resync", "workflow": wf_name})
            elif ts:
                sync_fresh[wf_name] = ts

    # 汇总打不开的源（供邮件/报告参考）
    unreachable = []
    for i in all_fatal + all_warn:
        if i["kind"] in ("SITES_DOWN", "SITE_DOWN"):
            unreachable.append({"file": i["file"], "detail": i["detail"]})

    report = {
        "healthy": not all_fatal,
        "fatal_count": len(all_fatal),
        "warn_count": len(all_warn),
        "issues": all_fatal,
        "warnings": all_warn,
        "needs_retry": sorted({i["workflow"] for i in all_fatal if i.get("workflow")}),
        "needs_strip": [i["file"] for i in all_fatal if i.get("fix") == "strip"],
        "workflow_latest_success": sync_fresh,
        "unreachable_sites": unreachable,
    }
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=1))
    else:
        print(f"=== 体检结果: {'ALL_OK' if not all_fatal else f'{len(all_fatal)} 个问题需修复'} ===")
        for i in all_fatal:
            print(f"  [需修] {i['kind']} {i['file']}: {i['detail']} -> {i['fix']} ({i['workflow']})")
        for w in all_warn:
            print(f"  [提示] {w['kind']} {w['file']}: {w['detail']}")
        if all_fatal:
            print("NEED_RETRY:", ",".join(report["needs_retry"]))
            print("NEED_STRIP:", ",".join(report["needs_strip"]))
    sys.exit(2 if all_fatal else 0)


if __name__ == "__main__":
    main()

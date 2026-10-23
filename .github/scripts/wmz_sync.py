# -*- coding: utf-8 -*-
"""
wmz_sync.py — 肥猫独有源自动同步脚本（在 GitHub Actions 里定时运行）
逻辑：
1. 拉取肥猫 wmz 接口 https://8815.kstore.vip/tvbox/wmz
2. 拉取咱们线上 10 套接口（tvbox-bh1.pages.dev 下）汇总已有源清单
3. 找出 wmz 中咱们没有的源（按整个源对比），原原本本完整拷贝字段
4. 生成 cl/wmz.json，有变化时 workflow 负责 commit + push
"""
import json, os, re, sys, urllib.request, ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

WMZ_URL = os.environ.get("WMZ_UPSTREAM") or "https://8815.kstore.vip/tvbox/wmz"
OUR_INTERFACES = [
    "https://tvbox-bh1.pages.dev/xs/api.json",
    "https://tvbox-bh1.pages.dev/fty/api.json",
    "https://tvbox-bh1.pages.dev/wex/api.json",
    "https://tvbox-bh1.pages.dev/feimao/api.json",
    "https://tvbox-bh1.pages.dev/cl/api.json",
    "https://tvbox-bh1.pages.dev/ouyang/api.json",
    "https://tvbox-bh1.pages.dev/lubin/api.json",
    "https://tvbox-bh1.pages.dev/dl/api.json",
    "https://tvbox-bh1.pages.dev/tvurl/api.json",
    "https://zhouyu86-bh1.pages.dev/b.json",
]
OUT = os.environ.get("WMZ_OUT") or os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "cl", "wmz.json")


def fetch(url, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
        return r.read().decode("utf-8-sig", errors="replace")  # utf-8-sig 处理 BOM


def norm(s):
    """规范化源名用于比对：去 emoji/空格/符号，小写"""
    return re.sub(r"[\W_]+", "", s.lower())


def strip_js_comments(text):
    """剥离 // 和 /* */ 注释（保留字符串内部内容）"""
    out = []
    i, n = 0, len(text)
    in_str, str_ch = False, ''
    while i < n:
        c = text[i]
        if in_str:
            out.append(c)
            if c == '\\' and i + 1 < n:
                out.append(text[i + 1])
                i += 2
                continue
            if c == str_ch:
                in_str = False
            i += 1
            continue
        if c in '"\'':
            in_str, str_ch = True, c
            out.append(c)
            i += 1
            continue
        if c == '/' and i + 1 < n and text[i + 1] == '/':
            while i < n and text[i] != '\n':
                i += 1
            continue
        if c == '/' and i + 1 < n and text[i + 1] == '*':
            i += 2
            while i + 1 < n and not (text[i] == '*' and text[i + 1] == '/'):
                i += 1
            i += 2
            continue
        out.append(c)
        i += 1
    return ''.join(out)


def parse_sites(text):
    """解析接口 JSON（支持 JS 注释），返回 [{key, name, raw}]；失败返回 None"""
    try:
        data = json.loads(strip_js_comments(text))
    except Exception:
        return None
    sites = data.get("sites") or []
    out = []
    for s in sites:
        k = s.get("key", "")
        n = s.get("name", "")
        out.append({"key": k, "name": n, "norm": norm(k) + "|" + norm(n), "raw": s})
    return out


def find_struct_end(text, start, open_ch, close_ch):
    """从 start 位置开始找匹配的 close_ch（正确处理字符串内部，跳过 \\ 转义）"""
    i = start
    cnt = 0
    in_str = False
    while i < len(text):
        c = text[i]
        if in_str:
            if c == '\\':
                i += 2
                continue
            if c == '"':
                in_str = False
            i += 1
            continue
        if c == '"':
            in_str = True
            i += 1
            continue
        if c == open_ch:
            cnt += 1
        elif c == close_ch:
            cnt -= 1
            if cnt == 0:
                return i
        i += 1
    return -1


def build_raw_subset(raw_text, unique_keys):
    """
    从上游原始文本中按"字节级原样"提取子集：
    - 只替换 sites 数组内容为选中的源块（原始文本，紧凑格式保留）
    - 其余（spider/wallpaper/logo/warningText/parses/rules/lives...）全部原样保留
    - 绝不用 json.dumps 重新格式化（会改变格式导致 OK影视解析失败）
    """
    # 用正则精确定位 "sites": [ （避免误命中字符串值里的 "sites"）
    m = re.search(r'"sites"\s*:\s*\[', raw_text)
    if not m:
        raise RuntimeError("上游没有 sites 数组！")
    sb = m.end() - 1                             # [ 的位置
    arr_end = find_struct_end(raw_text, sb, '[', ']')  # ] 的位置
    se = arr_end                                 # tail 从 ] 开始（保留闭合括号）

    # 在 [ .. ] 内切出每个顶层对象块（花括号平衡扫描，跳过字符串）
    blocks, keys = [], []
    i = sb + 1
    while i < se - 1:
        while i < se - 1 and raw_text[i] in ' \t\r\n,':
            i += 1
        if i >= se - 1:
            break
        if raw_text[i] != '{':
            i += 1
            continue
        j = find_struct_end(raw_text, i, '{', '}')
        blk = raw_text[i:j + 1]
        try:
            obj = json.loads(blk)
            keys.append(obj.get("key", ""))
        except Exception:
            keys.append("")
        blocks.append(blk)
        i = j + 1

    # 按 key 选独有源块（保持上游原顺序）
    sel = [blk for blk, k in zip(blocks, keys) if k in unique_keys]

    head = raw_text[:sb + 1]   # "sites":[ 之前（含 [ 本身）
    tail = raw_text[se:]       # ] 之后（lives/parses/rules 等原样）
    mid = ",".join(sel)        # 原始紧凑逗号分隔
    return head + mid + tail


def main():
    print("=== wmz 独有源自动同步 ===")

    # 1. 拉 wmz
    try:
        wmz_text = fetch(WMZ_URL)
        wmz = json.loads(wmz_text)
        print(f"wmz 拉取成功: {len(wmz.get('sites') or [])} 源")
    except Exception as e:
        print("wmz 拉取失败:", e)
        sys.exit(1)

    # 2. 汇总咱们已有源
    ours = set()
    for url in OUR_INTERFACES:
        try:
            sites = parse_sites(fetch(url))
            if sites is None:
                print(f"[跳过] {url.split('/')[2]}: 无法解析")
                continue
            for s in sites:
                if s["key"]:
                    ours.add(norm(s["key"]))
                if s["name"]:
                    ours.add(norm(s["name"]))
            print(f"[OK] {url.split('/')[3] if len(url.split('/'))>3 else url}: {len(sites)} 源")
        except Exception as e:
            print(f"[失败] {url}: {e}")

    print(f"咱们已有归一化源名: {len(ours)} 个")

    # 3. 过滤独有源（原原本本）
    unique = []
    for s in wmz.get("sites") or []:
        k, n = s.get("key", ""), s.get("name", "")
        key_hit = norm(k) in ours if k else False
        name_hit = norm(n) in ours if n else False
        if not key_hit and not name_hit:
            unique.append(s)  # 完整字段原样保留

    print(f"独有源: {len(unique)} 个")
    for s in unique:
        print(f"  - {s.get('key')} | {s.get('name')}")

    # 4. 生成新接口：文本级原样提取（保持上游紧凑格式，禁止 json.dumps 重排）
    #    同时把顶层 spider 改为咱们仓库的完整网址 jar（OK影视添加时从 Pages 下载，不会崩）
    unique_keys = set()
    for s in unique:
        unique_keys.add(s.get("key", ""))
    new_text = build_raw_subset(wmz_text, unique_keys)
    new_text = re.sub(
        r'"spider"\s*:\s*"[^"]*"',
        '"spider":"./lmw.jar;md5;62cd1dd7cf867a100d8613907d69b665"',
        new_text,
        count=1,
    )
    new_text = new_text.rstrip() + "\n"

    # 5. 对比旧文件
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    changed = True
    if os.path.exists(OUT):
        with open(OUT, "r", encoding="utf-8") as f:
            old = f.read()
        changed = old != new_text

    with open(OUT, "w", encoding="utf-8") as f:
        f.write(new_text)
    print(f"写入 {OUT}: {len(new_text)} 字节, {'有变化' if changed else '无变化'}")


if __name__ == "__main__":
    main()

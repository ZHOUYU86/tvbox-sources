# -*- coding: utf-8 -*-
"""
lmw_sync.py — 肥猫聚合源(LMW)新接口自动同步脚本
在 GitHub Actions 定时运行：
1. 拉上游 lmw.json（tushen6/Tomorrow 多仓聚合，16个接口）
2. 排除咱们 12 套已有的接口（网络/饭太硬/肥猫/王二小/东篱/南风）
3. 存活检测剩余接口（HTTP 测试，中文域名转 punycode）
4. 生成 cl/lmw_new.json（multi 聚合格式，只含活着且咱们没有的接口，name+url 原样）
5. 有变化则由 workflow commit + push → Cloudflare Pages 自动部署
"""
import json, os, re, sys, urllib.request, ssl
from urllib.parse import urlsplit, urlunsplit, quote

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

LMW_URL = "https://github.catvod.com/https://raw.githubusercontent.com/tushen6/Tomorrow/master/lmw.json"
OUT = os.environ.get("LMW_OUT") or os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "cl", "lmw_new.json")

# 咱们 12 套接口已有的识别特征（URL 关键词，稳定不变）
OURS = [
    "8815.kstore",      # 网络(wmz)
    "饭太硬", "fantaiying", "xn--sss604efuw",  # 饭太硬
    "肥猫", "z7x900a",  # 肥猫
    "9280.kstore", "aiwex",  # 王二小
    "16151.kstore", "chitue",  # 东篱
    "yoursmile66", "XC.json",  # 南风
]


def fetch(url, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
        return r.read()


def fix_url(url):
    """中文域名→punycode，中文路径→百分号编码"""
    try:
        parts = urlsplit(url)
        host = (parts.hostname or "").encode("idna").decode("ascii")
        port = f":{parts.port}" if parts.port else ""
        path = quote(parts.path or "", safe="/:@")
        return urlunsplit((parts.scheme, host + port, path, parts.query, parts.fragment))
    except Exception:
        return url


def alive(url, timeout=25):
    """HTTP 探测接口是否活着（返回是否可访问）"""
    try:
        req = urllib.request.Request(fix_url(url), headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
            data = r.read()
        # 排除返回 HTML 导航页的情况（接口应返回 JSON）
        head = data[:200].decode("utf-8", errors="replace").lstrip()
        if head.startswith("<!doctype") or head.startswith("<html"):
            return False
        return True
    except Exception:
        return False


def main():
    print("=== 肥猫聚合源(LMW)新接口同步 ===")
    try:
        raw = fetch(LMW_URL).decode("utf-8", errors="replace")
        up = json.loads(raw)
        print(f"上游 lmw.json 拉取成功: {len(up.get('urls') or [])} 个接口")
    except Exception as e:
        print("上游拉取失败:", e)
        sys.exit(1)

    new_ones = []
    for it in (up.get("urls") or []):
        url = it.get("url", "")
        hit = next((k for k in OURS if k.lower() in url.lower()), None)
        if hit:
            print(f"  [已有] {it.get('name')} | {url} ({hit})")
        else:
            print(f"  [候选] {it.get('name')} | {url}")
            new_ones.append(it)

    # 存活检测
    final = []
    for it in new_ones:
        if alive(it.get("url", "")):
            print(f"    -> [活] {it.get('name')}")
            final.append(it)
        else:
            print(f"    -> [挂] {it.get('name')} (不做)")

    print(f"新接口（活着+咱们没有）: {len(final)} 个")

    # 生成 multi 聚合接口（name+url 原样保留）
    new_api = {"urls": [{"url": it.get("url"), "name": it.get("name")} for it in final]}
    new_text = json.dumps(new_api, ensure_ascii=False, indent=4) + "\n"

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    changed = True
    if os.path.exists(OUT):
        with open(OUT, "r", encoding="utf-8") as f:
            changed = f.read() != new_text
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(new_text)
    print(f"写入 {OUT}: {len(new_text)}B, {'有变化' if changed else '无变化'}")


if __name__ == "__main__":
    main()

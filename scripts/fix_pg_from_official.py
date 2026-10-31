#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""本地一键修复 PG 源：从上游官方总仓 cnb.cool/fish2035/pg 拉取最新配置+jar+全量lib/js，
覆盖本地 pg/ 目录，并写入实测 md5。用法: python3 scripts/fix_pg_from_official.py
（镜像站 252035.xyz 的 jar 是旧版，网盘接口打不开，必须用官方总仓）"""
import hashlib, io, os, re, sys, urllib.request

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) doubao-fix-pg"}
BASE = "https://cnb.cool/fish2035/pg/-/git/raw/main"
PG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "pg")


def dl(url, timeout=120):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def dl_text(url, timeout=120):
    return dl(url, timeout).decode("utf-8-sig", errors="replace")


def main():
    os.makedirs(PG_DIR, exist_ok=True)
    # 1. 官方配置 jsm.json -> pg.json
    txt = dl_text(BASE + "/jsm.json")
    # 2. 官方最新 jar
    jar = dl(BASE + "/pg.jar", 180)
    with open(os.path.join(PG_DIR, "pg.jar"), "wb") as f:
        f.write(jar)
    md5 = hashlib.md5(jar).hexdigest()
    # 3. 官方 pg.jar.md5 校验
    try:
        official = dl_text(BASE + "/pg.jar.md5", 30).strip().lower()
        print(f"官方 pg.jar.md5: {official}")
        print(f"实测 pg.jar md5: {md5}")
        print("一致" if official == md5 else f"警告: 官方{official} 实测{md5}，以实测为准")
    except Exception as e:
        print(f"(无官方md5文件或读取失败: {e})")
    # 4. 全量同步 lib/js
    libs = sorted(set(re.findall(r'\./lib/([A-Za-z0-9_\-\.]+)', txt)))
    jss = sorted(set(re.findall(r'\./js/([A-Za-z0-9_\-\.]+)', txt)))
    ok = fail = 0
    for f in libs:
        dst = os.path.join(PG_DIR, "lib", f)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        try:
            b = dl(BASE + "/lib/" + f, 60)
            with open(dst, "wb") as fo:
                fo.write(b)
            ok += 1
        except Exception as e:
            print(f"lib 失败 {f}: {e}")
            fail += 1
    for f in jss:
        dst = os.path.join(PG_DIR, "js", f)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        try:
            b = dl(BASE + "/js/" + f, 60)
            with open(dst, "wb") as fo:
                fo.write(b)
            ok += 1
        except Exception as e:
            print(f"js 失败 {f}: {e}")
            fail += 1
    print(f"lib/js 同步: ok={ok} fail={fail}")
    # 5. spider 改相对路径 + 写实测 md5
    txt = re.sub(r'"spider"\s*:\s*"[^"]*"', f'"./pg.jar;md5;{md5}"', txt, count=1)
    with open(os.path.join(PG_DIR, "pg.json"), "w", encoding="utf-8") as f:
        f.write(txt)
    print(f"pg.json spider -> ./pg.jar;md5;{md5}")
    print("本地 PG 源修复完成")


if __name__ == "__main__":
    main()

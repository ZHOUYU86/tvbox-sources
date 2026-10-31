#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 PG 官方 jsm.json（裸字符串 spider 格式）转换为 TVBox 标准接口格式。
官方格式: { "\"./pg.jar;md5;XXX\"", "sites":[...] }
标准格式: { "\"spider\":\"./pg.jar;md5;XXX\"", "sites":[...] }
只改第一行裸字符串 -> 标准 spider 键值对，其余内容原样保留。"""
import io, json, os, re, sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
pg = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "pg", "pg.json")
raw = open(pg, encoding="utf-8").read()

# 匹配第一个裸字符串元素行：行首是引号（不是键），形如 "./pg.jar;md5;..."
m = re.search(r'(?m)^\s*"(\./pg\.jar;md5;[^"]*)"\s*,?\s*$', raw)
if not m:
    print("未找到裸字符串 spider 行（可能已是标准格式或格式异常）")
    print("前3行:")
    for ln in raw.splitlines()[:3]:
        print(repr(ln))
    sys.exit(0)

old_line = m.group(0)
new_line = old_line.replace('"./pg.jar;md5;', '"spider":"./pg.jar;md5;', 1)
new_raw = raw.replace(old_line, new_line, 1)
open(pg, "w", encoding="utf-8").write(new_raw)
print("转换完成:")
print("旧:", old_line.strip())
print("新:", new_line.strip())

# 校验 JSON 合法
try:
    json.loads(new_raw)
    print("JSON 校验: 合法")
except Exception as e:
    print("JSON 校验失败:", e)

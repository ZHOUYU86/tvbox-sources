#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""剥除 FongMi/fish2018 系配置的顶层扩展字段（兼容老版 OK影视，防止解析闪退）。
用法: python3 strip_fongmi_extra.py <json1> [json2 ...]
文本级提取 KEEP 字段原始片段拼接，绝不用 json.dump 重排；先剥 // 注释行。"""
import json, re, sys

KEEP = {"spider", "sites", "lives", "wallpaper"}


def top_fields(text):
    i = text.index("{") + 1
    out = []
    while True:
        while i < len(text) and text[i] in " \r\n\t":
            i += 1
        if i >= len(text) or text[i] == "}":
            break
        ks = i
        assert text[i] == '"', f"bad key at {i}: {text[i:i+40]!r}"
        j = i + 1
        while text[j] != '"':
            if text[j] == "\\":
                j += 1
            j += 1
        key = text[i + 1:j]
        j += 1
        while j < len(text) and text[j] in " \r\n\t":
            j += 1
        assert text[j] == ":", f"bad colon at {j}"
        j += 1
        while j < len(text) and text[j] in " \r\n\t":
            j += 1
        vs = j
        depth = 0
        ins = False
        while j < len(text):
            c = text[j]
            if ins:
                if c == "\\":
                    j += 2
                    continue
                if c == '"':
                    ins = False
            else:
                if c == '"':
                    ins = True
                elif c in "[{":
                    depth += 1
                elif c in "]}":
                    depth -= 1
                elif c == "," and depth == 0:
                    break
            j += 1
        ve = j
        out.append((key, text[ks:ve]))
        i = ve
        while i < len(text) and text[i] in " \r\n\t":
            i += 1
        if i < len(text) and text[i] == ",":
            i += 1
    return out


def strip(path):
    s = open(path, encoding="utf-8").read()
    s = re.sub(r'^\s*//.*$', '', s, flags=re.M)  # 剥注释
    keep = [(k, v) for k, v in top_fields(s) if k in KEEP]
    assert len(keep) == len(KEEP), f"{path}: KEEP 字段缺失 {[k for k, _ in keep]}"
    new = "{\r\n" + ",\r\n".join(v for _, v in keep) + "\r\n}"
    json.loads(new)  # 严格校验
    open(path, "w", encoding="utf-8").write(new)
    print("stripped", path, "->", [k for k, _ in keep])


if __name__ == "__main__":
    for p in sys.argv[1:]:
        strip(p)

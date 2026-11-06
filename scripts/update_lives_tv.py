# -*- coding: utf-8 -*-
"""每日自动更新 lives_tv.txt
来源: Guovin/iptv-api (自动测速优选, 按延迟排序, 死链已过滤)
"""
import urllib.request, ssl

URL = "https://raw.githubusercontent.com/Guovin/iptv-api/gd/output/result.txt"

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

print("下载:", URL)
req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0"})
data = urllib.request.urlopen(req, timeout=60, context=ctx).read().decode("utf-8")

with open("lives_tv.txt", "w", encoding="utf-8") as f:
    f.write(data)

print("完成:", len(data), "字符,", data.count(chr(10)), "行")

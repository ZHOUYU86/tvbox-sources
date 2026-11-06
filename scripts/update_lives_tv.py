# -*- coding: utf-8 -*-
"""每日自动更新 lives_tv.txt
来源: Guovin/iptv-api 自动测速优选
处理: 同频道多线路合并到一行(TVBox格式: 频道名,url1,url2,url3)
"""
import urllib.request, ssl

URL = "https://raw.githubusercontent.com/Guovin/iptv-api/gd/output/result.txt"

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

print("下载:", URL)
req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0"})
data = urllib.request.urlopen(req, timeout=60, context=ctx).read().decode("utf-8")

lines_out = []
ch_urls = {}
order = []

for line in data.split("\n"):
    line = line.strip()
    if not line:
        continue
    if line.endswith(",#genre#"):
        if order:
            for name in order:
                lines_out.append(name + "," + ",".join(ch_urls[name]))
            order = []
            ch_urls = {}
        lines_out.append(line)
        continue
    if "," not in line:
        continue
    name, url = line.split(",", 1)
    name = name.strip()
    url = url.strip()
    if not url.startswith("http"):
        continue
    if name not in ch_urls:
        ch_urls[name] = []
        order.append(name)
    ch_urls[name].append(url)

for name in order:
    lines_out.append(name + "," + ",".join(ch_urls[name]))

result = "\n".join(lines_out) + "\n"
with open("lives_tv.txt", "w", encoding="utf-8") as f:
    f.write(result)

print("完成:", len(result), "字符,", result.count(chr(10)), "行")

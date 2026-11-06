# -*- coding: utf-8 -*-
"""每日自动更新 lives_tv.txt
来源: peterhchina国内CDN(秒开) + iptv-org港澳台
格式: TVBox直播txt
"""
import urllib.request, ssl, re

SOURCES = [
    ("央视卫视", [
        "https://peterhchina.github.io/iptv/CCTV-V4.m3u",
        "https://peterhchina.github.io/iptv/CNTV-V4.m3u",
    ]),
    ("香港澳门台湾", [
        "https://iptv-org.github.io/iptv/countries/hk.m3u",
        "https://iptv-org.github.io/iptv/countries/mo.m3u",
        "https://iptv-org.github.io/iptv/countries/tw.m3u",
    ]),
]

# 要过滤掉的频道名(广告/无关)
SKIP = ["支持作者", "广告", "测试", "Test"]

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

groups = {}
order = []

for group_name, urls in SOURCES:
    if group_name not in groups:
        groups[group_name] = {}
        order.append(group_name)
    for url in urls:
        print("下载:", url)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            data = urllib.request.urlopen(req, timeout=30, context=ctx).read().decode("utf-8")
        except Exception as e:
            print("  失败:", e)
            continue
        cur_name = None
        for line in data.split("\n"):
            line = line.strip()
            if line.startswith("#EXTINF"):
                m2 = re.search(r',([^,]+)$', line)
                if m2:
                    cur_name = m2.group(1).strip()
            elif line.startswith("http") and cur_name:
                if any(k in cur_name for k in SKIP):
                    continue
                if cur_name not in groups[group_name]:
                    groups[group_name][cur_name] = []
                if line not in groups[group_name][cur_name]:
                    groups[group_name][cur_name].append(line)

out = []
for g in order:
    out.append(g + ",#genre#")
    for name, urls in groups[g].items():
        out.append(name + "," + ",".join(urls))
    out.append("")

result = "\n".join(out)
with open("lives_tv.txt", "w", encoding="utf-8") as f:
    f.write(result)

total = sum(len(v) for v in groups.values())
print("完成: %d个分组, %d个频道" % (len(groups), total))

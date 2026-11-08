#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TVBox/OK影视接口自动爬虫
功能：自动爬网上的TVBox接口，检测速度和可用性，去重，生成多接口聚合源all.json
"""

import json
import requests
import time
import base64
from datetime import datetime

# 配置
OUTPUT_FILE = "all.json"  # 输出文件
MAX_ONLINE_SOURCES = 30  # 最多加多少个网上的接口
SPEED_THRESHOLD = 10  # 速度超过10秒的就不要了

# 网上的聚合源地址（爬虫自动爬这些地址里的所有接口）
ONLINE_SOURCES = [
    "https://gh-proxy.com/https://raw.githubusercontent.com/tushen6/Tomorrow/master/lmw.json",
]

# 你自己仓库里的接口地址（用CF Pages地址）
MY_SOURCES = [
    {"name": "📺xs接口", "url": "https://zhouyu86-bh1.pages.dev/xs/api.json"},
    {"name": "📺fty接口", "url": "https://zhouyu86-bh1.pages.dev/fty/api.json"},
    {"name": "📺wex接口", "url": "https://zhouyu86-bh1.pages.dev/wex/api.json"},
    {"name": "📺cl接口", "url": "https://zhouyu86-bh1.pages.dev/cl/aa.json"},
    {"name": "📺ouyang接口", "url": "https://zhouyu86-bh1.pages.dev/ouyang/api.json"},
    {"name": "📺dl接口", "url": "https://zhouyu86-bh1.pages.dev/dl/api.json"},
    {"name": "📺tvurl接口", "url": "https://zhouyu86-bh1.pages.dev/tvurl/api.json"},
    {"name": "📺aowu接口", "url": "https://zhouyu86-bh1.pages.dev/pg/pg.json"},
    {"name": "📺b接口", "url": "https://zhouyu86-bh1.pages.dev/b.json"},
    {"name": "📺ok接口", "url": "https://zhouyu86-bh1.pages.dev/ok/m.json"},
]

# 你自己的接口地址集合（用于去重）
MY_URLS = set([s["url"] for s in MY_SOURCES])

def test_source(url):
    """测试接口速度和可用性，返回(速度, 是否可用)"""
    try:
        start = time.time()
        response = requests.get(url, timeout=10)
        end = time.time()
        speed = round(end - start, 2)
        
        if response.status_code != 200:
            return speed, False
        
        content = response.text
        
        # 看看是不是Base64编码的
        if content.startswith("YmFzZTY0**"):
            try:
                b64_data = content.replace("YmFzZTY0**", "")
                decoded = base64.b64decode(b64_data).decode("utf-8")
                data = json.loads(decoded)
                if "sites" in data and len(data["sites"]) > 0:
                    return speed, True
            except:
                pass
        
        # 看看是不是JSON格式
        try:
            data = response.json()
        except:
            return speed, False
        
        # 看看有没有sites字段，sites是不是为空
        if "sites" in data and len(data["sites"]) > 0:
            return speed, True
        
        # 如果是聚合源格式，也可以
        if "urls" in data and len(data["urls"]) > 0:
            return speed, True
        
        return speed, False
    except:
        return None, False

def crawl_online_sources():
    """爬网上的聚合源里的所有接口，并检测速度和可用性，去重"""
    online_urls = []
    seen_urls = set()  # 已经加过的地址，用于去重
    
    for source_url in ONLINE_SOURCES:
        try:
            print(f"正在爬取：{source_url}")
            response = requests.get(source_url, timeout=10)
            data = response.json()
            if "urls" in data:
                for item in data["urls"]:
                    url = item["url"]
                    name = item.get("name", "未知接口")
                    
                    # 去重：如果是你自己的接口，或者已经加过了，就跳过
                    if url in MY_URLS:
                        print(f"  跳过（你自己的接口）：{name}")
                        continue
                    if url in seen_urls:
                        print(f"  跳过（重复）：{name}")
                        continue
                    
                    print(f"  正在检测：{name}")
                    speed, usable = test_source(url)
                    if usable and speed and speed < SPEED_THRESHOLD:
                        online_urls.append({
                            "name": f"📺{name}",
                            "url": url
                        })
                        seen_urls.add(url)
                        print(f"    ✓ 速度：{speed}秒，可用！添加！")
                    else:
                        print(f"    ✗ 不可用或速度太慢，跳过！")
        except Exception as e:
            print(f"  ✗ 爬取失败：{e}")
    return online_urls[:MAX_ONLINE_SOURCES]

def main():
    print("=" * 60)
    print("TVBox/OK影视接口自动爬虫")
    print(f"开始时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # 爬网上的接口
    print("\n正在爬网上的接口并检测速度和可用性...")
    online_urls = crawl_online_sources()
    print(f"\n共爬到 {len(online_urls)} 个可用的网上接口")
    
    # 合并所有接口
    all_urls = []
    
    # 先加自己的接口
    for source in MY_SOURCES:
        all_urls.append(source)
        print(f"✓ 添加自己的接口：{source['name']}")
    
    # 再加网上的接口
    for source in online_urls:
        all_urls.append(source)
    
    print(f"\n共 {len(all_urls)} 个接口")
    
    # 生成all.json
    output_data = {
        "urls": all_urls
    }
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n已生成：{OUTPUT_FILE}")
    print(f"结束时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

if __name__ == "__main__":
    main()

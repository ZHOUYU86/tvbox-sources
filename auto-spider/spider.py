#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TVBox/OK影视接口自动爬虫
功能：自动爬网上的TVBox接口，生成多接口聚合源all.json
"""

import json
import requests
from datetime import datetime

# 配置
OUTPUT_FILE = "all.json"  # 输出文件

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

def crawl_online_sources():
    """爬网上的聚合源里的所有接口"""
    online_urls = []
    for source_url in ONLINE_SOURCES:
        try:
            print(f"正在爬取：{source_url}")
            response = requests.get(source_url, timeout=10)
            data = response.json()
            if "urls" in data:
                for item in data["urls"]:
                    online_urls.append({
                        "name": item.get("name", "未知接口"),
                        "url": item["url"]
                    })
                    print(f"  ✓ 找到接口：{item.get('name', '未知接口')}")
        except Exception as e:
            print(f"  ✗ 爬取失败：{e}")
    return online_urls

def main():
    print("=" * 60)
    print("TVBox/OK影视接口自动爬虫")
    print(f"开始时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # 爬网上的接口
    print("\n正在爬网上的接口...")
    online_urls = crawl_online_sources()
    print(f"\n共爬到 {len(online_urls)} 个网上接口")
    
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

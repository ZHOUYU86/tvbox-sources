#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TVBox/OK影视接口自动爬虫
功能：生成多接口聚合源all.json
"""

import json
from datetime import datetime

# 配置
OUTPUT_FILE = "all.json"  # 输出文件

# 你自己仓库里的接口地址
SOURCE_SITES = [
    {"name": "xs", "url": "https://zhouyu86-bh1.pages.dev/xs/api.json"},
    {"name": "fty", "url": "https://zhouyu86-bh1.pages.dev/fty/api.json"},
    {"name": "wex", "url": "https://zhouyu86-bh1.pages.dev/wex/api.json"},
    {"name": "nf", "url": "https://zhouyu86-bh1.pages.dev/nf/api.json"},
    {"name": "feimao", "url": "https://zhouyu86-bh1.pages.dev/feimao/api.json"},
    {"name": "cl", "url": "https://zhouyu86-bh1.pages.dev/cl/api.json"},
    {"name": "ouyang", "url": "https://zhouyu86-bh1.pages.dev/ouyang/api.json"},
    {"name": "lubin", "url": "https://zhouyu86-bh1.pages.dev/lubin/api.json"},
    {"name": "dl", "url": "https://zhouyu86-bh1.pages.dev/dl/api.json"},
    {"name": "tvurl", "url": "https://zhouyu86-bh1.pages.dev/tvurl/api.json"},
    {"name": "aowu", "url": "https://zhouyu86-bh1.pages.dev/aowu/api.json"},
    {"name": "b", "url": "https://zhouyu86-bh1.pages.dev/b/api.json"},
    {"name": "ok", "url": "https://zhouyu86-bh1.pages.dev/ok/api.json"},
    {"name": "tvbox18", "url": "https://zhouyu86-bh1.pages.dev/tvbox18/api.json"},
    {"name": "wmz", "url": "https://zhouyu86-bh1.pages.dev/wmz/api.json"},
    {"name": "zhenxin", "url": "https://zhouyu86-bh1.pages.dev/zhenxin/api.json"},
]

def main():
    print("=" * 60)
    print("TVBox/OK影视接口自动爬虫")
    print(f"开始时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # 生成站点列表
    sites = []
    for source in SOURCE_SITES:
        site = {
            "key": source["name"],
            "name": source["name"],
            "type": 3,
            "api": source["url"],
            "searchable": 1,
            "quickSearch": 1
        }
        sites.append(site)
        print(f"✓ 添加接口：{source['name']}")
    
    print(f"\n共 {len(sites)} 个接口")
    
    # 生成all.json
    output_data = {
        "spider": "",
        "sites": sites,
        "parses": [],
        "flags": [],
        "download": "",
        "UA": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n已生成：{OUTPUT_FILE}")
    print(f"结束时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

if __name__ == "__main__":
    main()

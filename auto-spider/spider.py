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

# 你自己仓库里的接口地址（用CF Pages地址）
SOURCE_URLS = [
    {"name": "📺xs接口", "url": "https://zhouyu86-bh1.pages.dev/xs/api.json"},
    {"name": "📺fty接口", "url": "https://zhouyu86-bh1.pages.dev/fty/api.json"},
    {"name": "📺wex接口", "url": "https://zhouyu86-bh1.pages.dev/wex/api.json"},
    {"name": "📺nf接口", "url": "https://zhouyu86-bh1.pages.dev/nf/api.json"},
    {"name": "📺feimao接口", "url": "https://zhouyu86-bh1.pages.dev/feimao/api.json"},
    {"name": "📺cl接口", "url": "https://zhouyu86-bh1.pages.dev/cl/api.json"},
    {"name": "📺ouyang接口", "url": "https://zhouyu86-bh1.pages.dev/ouyang/api.json"},
    {"name": "📺lubin接口", "url": "https://zhouyu86-bh1.pages.dev/lubin/api.json"},
    {"name": "📺dl接口", "url": "https://zhouyu86-bh1.pages.dev/dl/api.json"},
    {"name": "📺tvurl接口", "url": "https://zhouyu86-bh1.pages.dev/tvurl/api.json"},
    {"name": "📺aowu接口", "url": "https://zhouyu86-bh1.pages.dev/aowu/api.json"},
    {"name": "📺b接口", "url": "https://zhouyu86-bh1.pages.dev/b/api.json"},
    {"name": "📺ok接口", "url": "https://zhouyu86-bh1.pages.dev/ok/api.json"},
    {"name": "📺tvbox18接口", "url": "https://zhouyu86-bh1.pages.dev/tvbox18/api.json"},
    {"name": "📺wmz接口", "url": "https://zhouyu86-bh1.pages.dev/wmz/api.json"},
    {"name": "📺zhenxin接口", "url": "https://zhouyu86-bh1.pages.dev/zhenxin/api.json"},
]

def main():
    print("=" * 60)
    print("TVBox/OK影视接口自动爬虫")
    print(f"开始时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # 生成urls列表
    urls = []
    for source in SOURCE_URLS:
        urls.append({
            "url": source["url"],
            "name": source["name"]
        })
        print(f"✓ 添加接口：{source['name']}")
    
    print(f"\n共 {len(urls)} 个接口")
    
    # 生成all.json
    output_data = {
        "urls": urls
    }
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n已生成：{OUTPUT_FILE}")
    print(f"结束时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

if __name__ == "__main__":
    main()

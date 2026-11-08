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

# 你自己仓库里的接口地址（用GitHub raw地址，从GitHub独立拉取）
SOURCE_URLS = [
    {"name": "xs", "url": "https://raw.githubusercontent.com/ZHOUYU86/tvbox-sources/main/xs/api.json"},
    {"name": "fty", "url": "https://raw.githubusercontent.com/ZHOUYU86/tvbox-sources/main/fty/api.json"},
    {"name": "wex", "url": "https://raw.githubusercontent.com/ZHOUYU86/tvbox-sources/main/wex/api.json"},
    {"name": "nf", "url": "https://raw.githubusercontent.com/ZHOUYU86/tvbox-sources/main/nf/api.json"},
    {"name": "feimao", "url": "https://raw.githubusercontent.com/ZHOUYU86/tvbox-sources/main/feimao/api.json"},
    {"name": "cl", "url": "https://raw.githubusercontent.com/ZHOUYU86/tvbox-sources/main/cl/api.json"},
    {"name": "ouyang", "url": "https://raw.githubusercontent.com/ZHOUYU86/tvbox-sources/main/ouyang/api.json"},
    {"name": "lubin", "url": "https://raw.githubusercontent.com/ZHOUYU86/tvbox-sources/main/lubin/api.json"},
    {"name": "dl", "url": "https://raw.githubusercontent.com/ZHOUYU86/tvbox-sources/main/dl/api.json"},
    {"name": "tvurl", "url": "https://raw.githubusercontent.com/ZHOUYU86/tvbox-sources/main/tvurl/api.json"},
    {"name": "aowu", "url": "https://raw.githubusercontent.com/ZHOUYU86/tvbox-sources/main/aowu/api.json"},
    {"name": "b", "url": "https://raw.githubusercontent.com/ZHOUYU86/tvbox-sources/main/b/api.json"},
    {"name": "ok", "url": "https://raw.githubusercontent.com/ZHOUYU86/tvbox-sources/main/ok/api.json"},
    {"name": "tvbox18", "url": "https://raw.githubusercontent.com/ZHOUYU86/tvbox-sources/main/tvbox18/api.json"},
    {"name": "wmz", "url": "https://raw.githubusercontent.com/ZHOUYU86/tvbox-sources/main/wmz/api.json"},
    {"name": "zhenxin", "url": "https://raw.githubusercontent.com/ZHOUYU86/tvbox-sources/main/zhenxin/api.json"},
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

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TVBox/OK影视接口聚合源
功能：生成多接口聚合源all.json
"""

import json
from datetime import datetime

# 配置
OUTPUT_FILE = "all.json"  # 输出文件

def main():
    print("=" * 60)
    print("TVBox/OK影视接口聚合源")
    print(f"开始时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # 你自己GitHub仓库里的所有接口（15个）
    all_urls = [
        {"url": "https://zhouyu86-bh1.pages.dev/xs/api.json", "name": "📺xs接口"},
        {"url": "https://zhouyu86-bh1.pages.dev/fty/api.json", "name": "📺fty接口"},
        {"url": "https://zhouyu86-bh1.pages.dev/wex/api.json", "name": "📺wex接口"},
        {"url": "https://zhouyu86-bh1.pages.dev/cl/aa.json", "name": "📺cl接口"},
        {"url": "https://zhouyu86-bh1.pages.dev/ouyang/api.json", "name": "📺ouyang接口"},
        {"url": "https://zhouyu86-bh1.pages.dev/dl/api.json", "name": "📺dl接口"},
        {"url": "https://zhouyu86-bh1.pages.dev/tvurl/api.json", "name": "📺tvurl接口"},
        {"url": "https://zhouyu86-bh1.pages.dev/pg/pg.json", "name": "📺aowu接口"},
        {"url": "https://zhouyu86-bh1.pages.dev/b.json", "name": "📺b接口"},
        {"url": "https://zhouyu86-bh1.pages.dev/ok/m.json", "name": "📺ok接口"},
        {"url": "https://zhouyu86-bh1.pages.dev/nf/XC.json", "name": "📺nf接口"},
        {"url": "https://zhouyu86-bh1.pages.dev/feimao/multi.json", "name": "📺feimao接口"},
        {"url": "https://zhouyu86-bh1.pages.dev/lubin/api.json", "name": "📺lubin接口"},
        {"url": "https://zhouyu86-bh1.pages.dev/wmz/wmz.json", "name": "📺wmz接口"},
        {"url": "https://zhouyu86-bh1.pages.dev/zhenxin/tvboxdx.json", "name": "📺zhenxin接口"},
    ]
    
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

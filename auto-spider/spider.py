#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TVBox/OK影视接口自动爬虫
功能：自动爬取网上最新的TVBox接口，检测可用性，合并成all.json
"""

import requests
import json
import re
import time
import os
from urllib.parse import urlparse
from datetime import datetime

# 配置
TIMEOUT = 10  # 超时时间（秒）
MAX_RETRIES = 2  # 最大重试次数
OUTPUT_FILE = "all.json"  # 输出文件

# 已知的TVBox接口来源（从网上收集的）
SOURCE_URLS = [
    # GitHub上的热门TVBox接口仓库
    "https://raw.githubusercontent.com/TvBox/TvBox/master/json/TVBox.json",
    "https://raw.githubusercontent.com/gaotianliuyun/gao/master/json/1.json",
    "https://raw.githubusercontent.com/YuanNengSY/TVBox/main/json/OK.json",
    "https://raw.githubusercontent.com/tvbox360/TVBox/main/json/TVBox.json",
    "https://raw.githubusercontent.com/kinggofboss/TVBox/main/json/TVBox.json",
    "https://raw.githubusercontent.com/down888/tvbox/main/json/tvbox.json",
    "https://raw.githubusercontent.com/qingfengmingyue/TVBox/main/json/TVBox.json",
    "https://raw.githubusercontent.com/weleoys/TVBox/main/json/TVBox.json",
    "https://raw.githubusercontent.com/izzguy/TVBox/main/json/TVBox.json",
    "https://raw.githubusercontent.com/limbopro/mac.sh/main/TVBox/TVBox.json",
    # 其他来源
    "https://js.1080zyku.com/iphone/js/0407.json",
    "https://js.1080zyku.com/iphone/js/0408.json",
    "https://js.1080zyku.com/iphone/js/0409.json",
]

def is_valid_url(url):
    """检查URL是否有效"""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False

def fetch_url(url, timeout=TIMEOUT):
    """下载URL内容，带重试"""
    for i in range(MAX_RETRIES):
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
            response = requests.get(url, headers=headers, timeout=timeout)
            if response.status_code == 200:
                return response.text
        except Exception as e:
            print(f"  下载失败（第{i+1}次）：{e}")
            time.sleep(1)
    return None

def check_api_availability(api_url):
    """检测API接口是否可用"""
    try:
        # 尝试获取首页
        result = fetch_url(api_url, timeout=5)
        if result:
            # 检查是否是JSON格式
            try:
                data = json.loads(result)
                return True
            except:
                # 不是JSON，但能打开
                return True
        return False
    except:
        return False

def parse_tvbox_json(json_text):
    """解析TVBox JSON配置"""
    try:
        data = json.loads(json_text)
        return data
    except:
        return None

def extract_sites(data):
    """从TVBox配置中提取站点列表"""
    sites = []
    if isinstance(data, dict):
        # 标准TVBox格式
        if 'sites' in data:
            sites = data['sites']
        # 其他格式
        elif 'site' in data:
            sites = data['site']
    return sites

def merge_sites(all_sites, new_sites):
    """合并站点列表，去重"""
    existing_keys = set()
    for site in all_sites:
        if 'key' in site:
            existing_keys.add(site['key'])
    
    for site in new_sites:
        if 'key' in site and site['key'] not in existing_keys:
            all_sites.append(site)
            existing_keys.add(site['key'])
    
    return all_sites

def main():
    print("=" * 60)
    print("TVBox/OK影视接口自动爬虫")
    print(f"开始时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    all_sites = []
    valid_sources = 0
    total_sources = len(SOURCE_URLS)
    
    for i, source_url in enumerate(SOURCE_URLS):
        print(f"\n[{i+1}/{total_sources}] 正在爬取：{source_url[:60]}...")
        
        # 下载接口
        json_text = fetch_url(source_url)
        if not json_text:
            print("  ✗ 下载失败")
            continue
        
        # 解析JSON
        data = parse_tvbox_json(json_text)
        if not data:
            print("  ✗ JSON解析失败")
            continue
        
        # 提取站点
        sites = extract_sites(data)
        if not sites:
            print("  ✗ 没有找到站点")
            continue
        
        print(f"  ✓ 找到 {len(sites)} 个站点")
        
        # 合并到总列表
        all_sites = merge_sites(all_sites, sites)
        valid_sources += 1
    
    print("\n" + "=" * 60)
    print(f"爬取完成！")
    print(f"有效来源：{valid_sources}/{total_sources}")
    print(f"总站点数：{len(all_sites)}")
    
    # 生成all.json
    output_data = {
        "spider": "",
        "sites": all_sites,
        "parses": [],
        "flags": [],
        "download": "",
        "UA": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    
    print(f"已生成：{OUTPUT_FILE}")
    print(f"结束时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

if __name__ == "__main__":
    main()

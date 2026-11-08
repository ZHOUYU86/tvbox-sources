#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TVBox/OK影视接口自动爬虫
功能：从GitHub仓库爬取所有接口，检测可用性，合并成all.json
"""

import requests
import json
import time
from datetime import datetime

# 配置
TIMEOUT = 5  # 超时时间（秒）
MAX_RETRIES = 2  # 最大重试次数
OUTPUT_FILE = "all.json"  # 输出文件

# 你自己仓库里的接口地址
SOURCE_URLS = [
    "https://raw.githubusercontent.com/ZHOUYU86/tvbox-sources/main/xs/api.json",
    "https://raw.githubusercontent.com/ZHOUYU86/tvbox-sources/main/fty/api.json",
    "https://raw.githubusercontent.com/ZHOUYU86/tvbox-sources/main/wex/api.json",
    "https://raw.githubusercontent.com/ZHOUYU86/tvbox-sources/main/nf/api.json",
    "https://raw.githubusercontent.com/ZHOUYU86/tvbox-sources/main/feimao/api.json",
    "https://raw.githubusercontent.com/ZHOUYU86/tvbox-sources/main/cl/api.json",
    "https://raw.githubusercontent.com/ZHOUYU86/tvbox-sources/main/ouyang/api.json",
    "https://raw.githubusercontent.com/ZHOUYU86/tvbox-sources/main/lubin/api.json",
    "https://raw.githubusercontent.com/ZHOUYU86/tvbox-sources/main/dl/api.json",
    "https://raw.githubusercontent.com/ZHOUYU86/tvbox-sources/main/tvurl/api.json",
    "https://raw.githubusercontent.com/ZHOUYU86/tvbox-sources/main/aowu/api.json",
    "https://raw.githubusercontent.com/ZHOUYU86/tvbox-sources/main/b/api.json",
    "https://raw.githubusercontent.com/ZHOUYU86/tvbox-sources/main/ok/api.json",
    "https://raw.githubusercontent.com/ZHOUYU86/tvbox-sources/main/tvbox18/api.json",
    "https://raw.githubusercontent.com/ZHOUYU86/tvbox-sources/main/wmz/api.json",
    "https://raw.githubusercontent.com/ZHOUYU86/tvbox-sources/main/zhenxin/api.json",
]

def fetch_url(url, timeout=TIMEOUT):
    """下载URL内容，带重试"""
    for i in range(MAX_RETRIES):
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
            start_time = time.time()
            response = requests.get(url, headers=headers, timeout=timeout)
            elapsed_time = time.time() - start_time
            if response.status_code == 200:
                return response.text, elapsed_time
        except Exception as e:
            print(f"  下载失败（第{i+1}次）：{e}")
            time.sleep(1)
    return None, 0

def check_site_availability(site):
    """检测站点是否可用"""
    try:
        # 获取站点的API地址
        api = site.get('api', '')
        if not api:
            return False
        
        # 检测API地址是否可用
        result, elapsed_time = fetch_url(api, timeout=3)
        if result:
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
    if isinstance(data, list):
        # 数组格式
        sites = data
    elif isinstance(data, dict):
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
        source_name = source_url.split('/')[-2]
        print(f"\n[{i+1}/{total_sources}] 正在爬取：{source_name}...")
        
        # 下载接口
        json_text, elapsed_time = fetch_url(source_url)
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
        
        print(f"  ✓ 找到 {len(sites)} 个站点（耗时 {elapsed_time:.2f}s）")
        
        # 合并到总列表
        all_sites = merge_sites(all_sites, sites)
        valid_sources += 1
    
    print("\n" + "=" * 60)
    print(f"爬取完成！")
    print(f"有效来源：{valid_sources}/{total_sources}")
    print(f"总站点数：{len(all_sites)}")
    
    # 检测每个站点的可用性
    print("\n正在检测站点可用性...")
    valid_sites = []
    for i, site in enumerate(all_sites):
        site_name = site.get('name', site.get('key', '未知'))
        print(f"[{i+1}/{len(all_sites)}] 检测：{site_name}...", end=" ")
        
        if check_site_availability(site):
            print("✓ 可用")
            valid_sites.append(site)
        else:
            print("✗ 不可用")
    
    print(f"\n可用站点：{len(valid_sites)}/{len(all_sites)}")
    
    # 生成all.json
    output_data = {
        "spider": "",
        "sites": valid_sites,
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

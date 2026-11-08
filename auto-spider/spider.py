#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TVBox/OK影视接口自动爬虫
功能：从GitHub仓库爬取所有接口，生成导航页面
"""

import requests
import json
import time
from datetime import datetime

# 配置
TIMEOUT = 10  # 超时时间（秒）
MAX_RETRIES = 2  # 最大重试次数
OUTPUT_FILE = "index.html"  # 输出文件

# 你自己仓库里的接口地址
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

# CF Pages域名
CF_PAGES_DOMAIN = "https://zhouyu86-bh1.pages.dev"

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

def main():
    print("=" * 60)
    print("TVBox/OK影视接口自动爬虫")
    print(f"开始时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    valid_sources = []
    total_sources = len(SOURCE_URLS)
    
    for i, source in enumerate(SOURCE_URLS):
        source_name = source['name']
        source_url = source['url']
        print(f"\n[{i+1}/{total_sources}] 正在检测：{source_name}...")
        
        # 下载接口
        json_text = fetch_url(source_url)
        if not json_text:
            print("  ✗ 下载失败")
            continue
        
        # 解析JSON
        try:
            data = json.loads(json_text)
            if isinstance(data, list):
                site_count = len(data)
            elif isinstance(data, dict) and 'sites' in data:
                site_count = len(data['sites'])
            else:
                site_count = 0
        except:
            site_count = 0
        
        # CF Pages地址
        cf_url = f"{CF_PAGES_DOMAIN}/{source_name}/api.json"
        
        valid_sources.append({
            "name": source_name,
            "url": cf_url,
            "site_count": site_count
        })
        
        print(f"  ✓ 有效（{site_count}个站点）")
    
    print("\n" + "=" * 60)
    print(f"爬取完成！")
    print(f"有效来源：{len(valid_sources)}/{total_sources}")
    
    # 生成HTML导航页面
    html_parts = []
    html_parts.append('<!DOCTYPE html>')
    html_parts.append('<html lang="zh-CN">')
    html_parts.append('<head>')
    html_parts.append('<meta charset="UTF-8">')
    html_parts.append('<meta name="viewport" content="width=device-width, initial-scale=1.0">')
    html_parts.append('<title>TVBox接口导航</title>')
    html_parts.append('<style>')
    html_parts.append('body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; background-color: #f5f5f5; }')
    html_parts.append('h1 { text-align: center; color: #333; }')
    html_parts.append('.source-list { background: white; border-radius: 8px; padding: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }')
    html_parts.append('.source-item { padding: 15px; border-bottom: 1px solid #eee; display: flex; justify-content: space-between; align-items: center; }')
    html_parts.append('.source-item:last-child { border-bottom: none; }')
    html_parts.append('.source-name { font-size: 18px; font-weight: bold; color: #333; }')
    html_parts.append('.source-info { color: #666; font-size: 14px; }')
    html_parts.append('.source-url { color: #007bff; font-size: 12px; word-break: break-all; }')
    html_parts.append('.copy-btn { background: #007bff; color: white; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer; font-size: 14px; }')
    html_parts.append('.copy-btn:hover { background: #0056b3; }')
    html_parts.append('</style>')
    html_parts.append('</head>')
    html_parts.append('<body>')
    html_parts.append('<h1>TVBox/OK影视接口导航</h1>')
    html_parts.append('<p style="text-align: center; color: #666;">点击"复制"按钮，然后粘贴到OK影视里即可使用</p>')
    html_parts.append('<div class="source-list">')
    
    for source in valid_sources:
        html_parts.append('<div class="source-item">')
        html_parts.append('  <div>')
        html_parts.append(f'    <div class="source-name">{source["name"]}</div>')
        html_parts.append(f'    <div class="source-info">{source["site_count"]}个站点</div>')
        html_parts.append(f'    <div class="source-url">{source["url"]}</div>')
        html_parts.append('  </div>')
        html_parts.append(f'  <button class="copy-btn" onclick="copyUrl(\'{source["url"]}\')">复制</button>')
        html_parts.append('</div>')
    
    html_parts.append('</div>')
    html_parts.append('<script>')
    html_parts.append('function copyUrl(url) { navigator.clipboard.writeText(url).then(function() { alert("已复制：" + url); }, function() { prompt("请手动复制：", url); }); }')
    html_parts.append('</script>')
    html_parts.append('</body>')
    html_parts.append('</html>')
    
    html_content = '\n'.join(html_parts)
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"已生成：{OUTPUT_FILE}")
    print(f"结束时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

if __name__ == "__main__":
    main()

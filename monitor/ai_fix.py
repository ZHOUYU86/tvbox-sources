# -*- coding: utf-8 -*-
"""
AI自动修复挂掉的影视源
用免费的智谱GLM-4-Flash接口
"""
import json
import requests
import os

# 读巡检结果
with open("monitor/result.json", "r", encoding="utf-8") as f:
    result = json.load(f)

failed = result["failed"]
if not failed:
    print("没有挂掉的源，不需要修复")
    exit(0)

# 智谱免费AI接口
ZHIPU_API = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
ZHIPU_KEY = os.environ.get("ZHIPU_API_KEY", "")

if not ZHIPU_KEY:
    print("未配置ZHIPU_API_KEY，跳过自动修复")
    exit(0)

print(f"发现{len(failed)}个挂掉的源，开始让AI自动修复...")

for site in failed:
    name = site["name"]
    api = site["api"]
    print(f"\n正在让AI分析：{name} ...")
    
    # 让AI分析这个api为什么挂了，给一个替代方案
    prompt = f"""
我有一个TVBox影视源配置，现在挂了：
源名称：{name}
接口地址：{api}
错误信息：{site.get('error', '请求失败')}

请帮我：
1. 分析可能挂掉的原因
2. 如果是接口换域名了，给我一个现在能用的同类型采集源地址
3. 只返回JSON格式：{{"fixed_api": "新的接口地址", "reason": "修复说明"}}
不要返回其他内容。
"""
    
    try:
        r = requests.post(ZHIPU_API, headers={
            "Authorization": f"Bearer {ZHIPU_KEY}",
            "Content-Type": "application/json"
        }, json={
            "model": "glm-4-flash",
            "messages": [{"role": "user", "content": prompt}]
        }, timeout=30)
        
        ai_res = r.json()
        ai_text = ai_res["choices"][0]["message"]["content"]
        print(f"AI返回：{ai_text}")
        
        # 提取JSON
        start = ai_text.find("{")
        end = ai_text.rfind("}") + 1
        if start > 0 and end > start:
            fix = json.loads(ai_text[start:end])
            new_api = fix.get("fixed_api", "")
            if new_api and new_api.startswith("http"):
                # 改b.json里对应的api
                with open("b.json", "r", encoding="utf-8") as f:
                    conf = json.load(f)
                for s in conf["sites"]:
                    if s.get("name") == name or s.get("key") == site.get("key"):
                        print(f"✅ 自动修复：{name} -> {new_api}")
                        s["api"] = new_api
                        break
                with open("b.json", "w", encoding="utf-8") as f:
                    json.dump(conf, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"AI修复{name}失败：{e}")

print("\nAI自动修复完成！")

# -*- coding: utf-8 -*-
"""
AI自动修复挂掉的影视源 - 全量版
用免费的智谱GLM-4-Flash接口，自动找新地址，先测试再修改
"""
import json
import requests
import os
import glob

UA = {"User-Agent": "Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 Chrome/120.0.0.0 Mobile Safari/537.36"}

# 读巡检结果
with open("monitor/result.json", "r", encoding="utf-8") as f:
    result = json.load(f)

failed = result["failed"]
if not failed:
    print("✅ 没有挂掉的源，不需要修复")
    exit(0)

# 智谱免费AI接口
ZHIPU_API = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
ZHIPU_KEY = os.environ.get("ZHIPU_API_KEY", "")

if not ZHIPU_KEY:
    print("⚠️ 未配置ZHIPU_API_KEY，跳过自动修复")
    exit(0)

print(f"发现{len(failed)}个挂掉的源，开始让AI自动修复...")

def test_new_api(api):
    """先测试新地址能不能用，能用才改"""
    try:
        test_url = api + "?ac=list&pg=1"
        r = requests.get(test_url, headers=UA, timeout=10)
        return r.status_code == 200 and len(r.text) > 100
    except:
        return False

for site in failed:
    name = site["name"]
    old_api = site["api"]
    from_file = site.get("from_file", "b.json")
    print(f"\n正在让AI分析：{name} (来自{from_file}) ...")
    
    prompt = f"""
我有一个TVBox苹果CMS影视源配置，现在挂了：
源名称：{name}
旧接口地址：{old_api}
错误信息：{site.get('error', '请求失败')}

请帮我找一个现在能用的同类型苹果CMS采集源地址，只返回JSON格式：
{{"fixed_api": "新的可用接口地址", "reason": "为什么这个新地址能用"}}
不要返回其他任何内容。
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
        
        start = ai_text.find("{")
        end = ai_text.rfind("}") + 1
        if start < 0 or end <= start:
            print("❌ AI返回格式错误，跳过")
            continue
            
        fix = json.loads(ai_text[start:end])
        new_api = fix.get("fixed_api", "")
        
        if not new_api.startswith("http"):
            print("❌ AI返回的地址无效，跳过")
            continue
            
        # 先测试新地址能不能用
        print(f"测试新地址：{new_api} ...")
        if not test_new_api(new_api):
            print("❌ 新地址测试失败，跳过修改，不会改坏原有配置")
            continue
            
        # 新地址能用，才修改对应的json文件
        print(f"✅ 新地址测试通过，开始修改...")
        with open(from_file, "r", encoding="utf-8") as f:
            conf = json.load(f)
        
        modified = False
        for s in conf["sites"]:
            if s.get("name") == name or s.get("api") == old_api:
                print(f"✅ 自动修复：{name} {old_api} -> {new_api}")
                s["api"] = new_api
                modified = True
                break
        
        if modified:
            with open(from_file, "w", encoding="utf-8") as f:
                json.dump(conf, f, ensure_ascii=False, indent=2)
            print(f"✅ 已写入{from_file}")
        else:
            print(f"⚠️ 在{from_file}里没找到这个源，跳过")
            
    except Exception as e:
        print(f"❌ AI修复{name}失败：{e}")

print("\n✅ AI自动修复完成！")

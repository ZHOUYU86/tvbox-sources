# -*- coding: utf-8 -*-
"""
影视源自动巡检脚本
"""
import json
import requests
import os

# 读b.json
with open("b.json", "r", encoding="utf-8") as f:
    conf = json.load(f)

failed = []
success = []

UA = {"User-Agent": "Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 Chrome/120.0.0.0 Mobile Safari/537.36"}

for site in conf["sites"]:
    name = site.get("name", site.get("key", "未知"))
    stype = site.get("type", 0)
    api = site.get("api", "")
    
    if not api:
        continue
    
    print(f"正在测试：{name} ...")
    try:
        # type=1的采集源直接测分类接口
        if stype == 1:
            test_url = api + "?ac=list&pg=1"
            r = requests.get(test_url, headers=UA, timeout=10)
            if r.status_code == 200 and len(r.text) > 100:
                success.append(name)
                print(f"  ✅ 正常")
            else:
                failed.append({"name": name, "api": api, "type": stype})
                print(f"  ❌ 异常，状态码{r.status_code}")
        else:
            # type=3的PY/JAR源跳过，等线上部署后再测
            print(f"  ⏭️  PY/JAR源，跳过本地测试")
    except Exception as e:
        failed.append({"name": name, "api": api, "type": stype, "error": str(e)})
        print(f"  ❌ 失败：{e}")

# 输出结果
with open("monitor/result.json", "w", encoding="utf-8") as f:
    json.dump({"success": success, "failed": failed}, f, ensure_ascii=False, indent=2)

print(f"\n测试完成：成功{len(success)}个，失败{len(failed)}个")
if failed:
    print("失败列表：")
    for f in failed:
        print(f"  - {f['name']}")

# 给GitHub Actions传结果
with open(os.environ["GITHUB_OUTPUT"], "a") as f:
    f.write(f"failed_sources={json.dumps(failed, ensure_ascii=False)}\n")

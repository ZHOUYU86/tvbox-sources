# -*- coding: utf-8 -*-
"""
全量影视源自动巡检脚本 v2 - 并行测试+失败重试+生成报告
改进：降低误判、加延时防封IP、自动生成报告
"""
import json
import requests
import os
import glob
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

UA = {"User-Agent": "Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 Chrome/120.0.0.0 Mobile Safari/537.36"}
all_sites = []

# 递归遍历仓库里所有json文件，排除monitor目录下的结果文件
json_files = [f for f in glob.glob("**/*.json", recursive=True) if not f.startswith("monitor/")]
print(f"找到{len(json_files)}个配置文件：{json_files}")

for jf in json_files:
    try:
        with open(jf, "r", encoding="utf-8") as f:
            conf = json.load(f)
        sites = conf.get("sites", [])
        print(f"📄 {jf} 里有{len(sites)}个站点")
        for site in sites:
            site["_from_file"] = jf
            all_sites.append(site)
    except Exception as e:
        print(f"⚠️ 读{jf}失败：{e}")

print(f"\n总共要监控{len(all_sites)}个站点，并行测试开始...\n")

def test_once(site):
    """单次测试一个源，返回测试结果"""
    name = site.get("name", site.get("key", "未知"))
    stype = site.get("type", 0)
    api = site.get("api", "")
    from_file = site.get("_from_file", "")

    if not api or not api.startswith("http"):
        return None

    try:
        if stype == 1:
            test_url = api + "?ac=list&pg=1"
            r = requests.get(test_url, headers=UA, timeout=10)
            if r.status_code != 200 or len(r.text) < 100:
                return {"name": name, "api": api, "type": stype, "from_file": from_file, "error": f"列表接口返回{r.status_code}", "ok": False}

            data = r.json()
            video_list = data.get("list", [])
            if not video_list:
                return {"name": name, "api": api, "type": stype, "from_file": from_file, "error": "列表为空", "ok": False}

            first_vod = video_list[0]
            vid = first_vod.get("vod_id")
            detail_url = api + f"?ac=detail&ids={vid}"
            r2 = requests.get(detail_url, headers=UA, timeout=10)
            if r2.status_code != 200:
                return {"name": name, "api": api, "type": stype, "from_file": from_file, "error": f"详情接口返回{r2.status_code}", "ok": False}

            detail = r2.json().get("list", [])
            if not detail:
                return {"name": name, "api": api, "type": stype, "from_file": from_file, "error": "详情为空", "ok": False}

            return {"name": name, "ok": True}
        else:
            return None
    except Exception as e:
        return {"name": name, "api": api, "type": stype, "from_file": from_file, "error": str(e)[:80], "ok": False}

def test_site_with_retry(site):
    """带重试的测试：失败后等3秒再测一次，两次都失败才算坏"""
    result = test_once(site)
    if result is None:
        return None
    if result["ok"]:
        return result
    # 第一次失败，等3秒重试
    time.sleep(3)
    retry = test_once(site)
    if retry is None:
        return result
    if retry["ok"]:
        print(f"  🔄 {result['name']} 第一次失败但重试成功，判定为正常")
        return retry
    # 两次都失败，合并错误信息
    result["error"] = f"连续2次失败: {result['error']}"
    return result

# 并行测试，并发降到5，加延时防封IP
success = []
failed = []
with ThreadPoolExecutor(max_workers=5) as executor:
    futures = {executor.submit(test_site_with_retry, site): site for site in all_sites}
    for future in as_completed(futures):
        res = future.result()
        if res is None:
            continue
        if res["ok"]:
            success.append(res["name"])
            print(f"✅ {res['name']} 正常")
        else:
            failed.append(res)
            print(f"❌ {res['name']} 失败：{res.get('error', '未知')}")

# 生成报告
os.makedirs("monitor", exist_ok=True)
with open("monitor/result.json", "w", encoding="utf-8") as f:
    json.dump({"success": success, "failed": failed}, f, ensure_ascii=False, indent=2)

# 生成markdown报告
now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
total = len(success) + len(failed)
report = f"""# 影视源健康检测报告

**检测时间：** {now}  
**检测总数：** {total} 个源  
**正常：** ✅ {len(success)} 个  
**异常：** ❌ {len(failed)} 个  

---

## ❌ 异常源列表（{len(failed)}个）

| 源名称 | 来源文件 | 错误原因 |
|--------|----------|----------|
"""
for f in failed:
    report += f"| {f['name']} | {f['from_file']} | {f.get('error', '未知')} |\n"

report += f"""
---

## ✅ 正常源列表（{len(success)}个）

{', '.join(success) if success else '无'}
"""

with open("monitor/report.md", "w", encoding="utf-8") as f:
    f.write(report)

print(f"\n✅ 测试完成：成功{len(success)}个，失败{len(failed)}个")
print(f"📄 报告已生成：monitor/report.md")

with open(os.environ["GITHUB_OUTPUT"], "a") as f:
    f.write(f"failed_sources={json.dumps(failed, ensure_ascii=False)}\n")
    f.write(f"total_sources={total}\n")
    f.write(f"failed_count={len(failed)}\n")

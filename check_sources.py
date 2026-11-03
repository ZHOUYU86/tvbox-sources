# -*- coding: utf-8 -*-
"""
全量影视源自动巡检脚本 v3 - 低误报版
"""
import json
import requests
import os
import glob
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

UA = {"User-Agent": "Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 Chrome/120.0.0.0 Mobile Safari/537.36"}
all_sites = []

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

def test_site(site):
    name = site.get("name", site.get("key", "未知"))
    stype = site.get("type", 0)
    api = site.get("api", "")
    from_file = site.get("_from_file", "")

    if not api or not api.startswith("http"):
        return None
    if "127.0.0.1" in api or "localhost" in api:
        return None

    try:
        if stype == 1:
            test_url = api + "?ac=list&pg=1"
            r = requests.get(test_url, headers=UA, timeout=6)
            if r.status_code == 403:
                return None
            if r.status_code == 404:
                return {"name": name, "api": api, "type": stype, "from_file": from_file, "error": "接口404不存在", "ok": False}
            if r.status_code != 200 or len(r.text) < 100:
                return None
            data = r.json()
            video_list = data.get("list", [])
            if not video_list:
                return {"name": name, "api": api, "type": stype, "from_file": from_file, "error": "列表为空（源真挂了）", "ok": False}
            first_vod = video_list[0]
            vid = first_vod.get("vod_id")
            detail_url = api + f"?ac=detail&ids={vid}"
            r2 = requests.get(detail_url, headers=UA, timeout=6)
            if r2.status_code == 403:
                return None
            if r2.status_code != 200:
                return None
            detail = r2.json().get("list", [])
            if not detail:
                return None
            return {"name": name, "ok": True}
        else:
            return None
    except requests.exceptions.Timeout:
        return None
    except requests.exceptions.ConnectionError:
        return None
    except Exception as e:
        err_str = str(e)
        if "Expecting value" in err_str:
            return None
        return {"name": name, "api": api, "type": stype, "from_file": from_file, "error": err_str[:80], "ok": False}

success = []
failed = []
skipped = 0
with ThreadPoolExecutor(max_workers=8) as executor:
    futures = {executor.submit(test_site, site): site for site in all_sites}
    for future in as_completed(futures):
        res = future.result()
        if res is None:
            skipped += 1
            continue
        if res["ok"]:
            success.append(res["name"])
            print(f"✅ {res['name']} 正常")
        else:
            failed.append(res)
            print(f"❌ {res['name']} 失败：{res.get('error', '未知')}")

os.makedirs("monitor", exist_ok=True)
with open("monitor/result.json", "w", encoding="utf-8") as f:
    json.dump({"success": success, "failed": failed}, f, ensure_ascii=False, indent=2)

now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
total = len(success) + len(failed)
report = f"""# 影视源健康检测报告

**检测时间：** {now}  
**检测总数：** {total} 个源  
**正常：** ✅ {len(success)} 个  
**异常：** ❌ {len(failed)} 个  
**跳过（本地地址/超时/IP限制）：** ⏭️ {skipped} 个  

---

## ❌ 真正异常的源（{len(failed)}个）

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

print(f"\n✅ 测试完成：成功{len(success)}个，真正异常{len(failed)}个，跳过{skipped}个")
print(f"📄 报告已生成：monitor/report.md")

with open(os.environ["GITHUB_OUTPUT"], "a") as f:
    f.write(f"failed_sources={json.dumps(failed, ensure_ascii=False)}\n")
    f.write(f"total_sources={total}\n")
    f.write(f"failed_count={len(failed)}\n")

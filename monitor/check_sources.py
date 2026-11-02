# -*- coding: utf-8 -*-
"""
全量影视源自动巡检脚本 - 并行测试+真测播放
"""
import json
import requests
import os
import glob
from concurrent.futures import ThreadPoolExecutor, as_completed

UA = {"User-Agent": "Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 Chrome/120.0.0.0 Mobile Safari/537.36"}

all_sites = []

# 递归遍历仓库里所有json文件
json_files = glob.glob("**/*.json", recursive=True)
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
    
    try:
        if stype == 1:
            # 测列表接口
            test_url = api + "?ac=list&pg=1"
            r = requests.get(test_url, headers=UA, timeout=10)
            if r.status_code != 200 or len(r.text) < 100:
                return {"name": name, "api": api, "type": stype, "from_file": from_file, "error": "列表接口无响应", "ok": False}
            
            data = r.json()
            video_list = data.get("list", [])
            if not video_list:
                return {"name": name, "api": api, "type": stype, "from_file": from_file, "error": "列表为空", "ok": False}
            
            # 拉详情
            first_vod = video_list[0]
            vid = first_vod.get("vod_id")
            detail_url = api + f"?ac=detail&ids={vid}"
            r2 = requests.get(detail_url, headers=UA, timeout=10)
            if r2.status_code != 200:
                return {"name": name, "api": api, "type": stype, "from_file": from_file, "error": "详情接口无响应", "ok": False}
            
            detail = r2.json().get("list", [])
            if not detail:
                return {"name": name, "api": api, "type": stype, "from_file": from_file, "error": "详情为空", "ok": False}
            
            play_url = detail[0].get("vod_play_url", "")
            if not play_url:
                return {"name": name, "ok": True}
            
            # 测播放地址
            first_play = play_url.split("#")[0]
            play_addr = first_play.split("$")[-1]
            if play_addr.startswith("http"):
                r3 = requests.get(play_addr, headers=UA, timeout=10, stream=True)
                if r3.status_code == 200:
                    return {"name": name, "ok": True}
                else:
                    return {"name": name, "api": api, "type": stype, "from_file": from_file, "error": f"播放地址返回{r3.status_code}", "ok": False}
            else:
                return {"name": name, "ok": True}
        else:
            return None
    except Exception as e:
        return {"name": name, "api": api, "type": stype, "from_file": from_file, "error": str(e), "ok": False}

# 并行测试，同时跑10个
success = []
failed = []
with ThreadPoolExecutor(max_workers=10) as executor:
    futures = {executor.submit(test_site, site): site for site in all_sites}
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

os.makedirs("monitor", exist_ok=True)
with open("monitor/result.json", "w", encoding="utf-8") as f:
    json.dump({"success": success, "failed": failed}, f, ensure_ascii=False, indent=2)

print(f"\n✅ 测试完成：成功{len(success)}个，失败{len(failed)}个")
if failed:
    print("失败列表：")
    for f in failed:
        print(f"  - {f['name']} (来自{f['from_file']})：{f.get('error', '未知')}")

with open(os.environ["GITHUB_OUTPUT"], "a") as f:
    f.write(f"failed_sources={json.dumps(failed, ensure_ascii=False)}\n")

# 瓜子影视接入 b.json 主接口 + 备份记录

日期：2026-10-16
状态：已完成并线上验证

## 一、背景结论（接 2026-10-15 逆向攻坚档案）

- 瓜子影视自研 jar 不可行（响应加密+加固壳 native 解密，Windows/x86 模拟器全堵死）。
- 但**瓜子影视在 OK影视 里能正常用**——因为它走的是现成的 wex 接口，无需自研。

## 二、瓜子影视真实链路（本次查清）

1. OK影视 配置 config_0/config_1 = `https://zhouyu86-bh1.pages.dev/wex/api.json`
2. wex/api.json（32666B，96 个 type=3 源）spider = `./spider.jar;md5;fc8f993c9297d38139363cd0e3db9853`
3. **瓜子影视 = site `WexAiGuaZi`**，name `💥瓜子┃秒播💥`，api `csp_WexAiGuaZiGuard`
4. wex/spider.jar（1000156B，md5 fc8f993c…）含 `classes.dex`（39KB，含 WexAiGuaZiGuard 类）+ wexguard_v7/v8.so 加固
5. 瓜子影视 token/授权存在 OK影视 本地 shared_prefs `NewWexFnw_preferences.xml`：
   - wex_guazi_device_key = 1D5A975CF0908434A5FB5BFF9ABD4B30BB67AE9E
   - wex_guazi_token_id = 50210152
   - wex_guazi_token = b8322e6a…（长串）
   - thunderCfg（迅雷 deviceId/peerId）

## 三、备份（双重保险）

- wex/api.json + wex/spider.jar **本来就在 GitHub 仓库 `wex/` 目录**（pages.dev 部署源）
- 本次再备份副本到仓库根目录：`wex_api.json`（sha 853ceae6）、`wex_spider.jar`（sha bd517bf7）
- 本地副本：D:\tvbox\_tools\wex_api.json、D:\tvbox\_tools\wex_spider.jar

## 四、接入 b.json 主接口（本次完成）

- b.json 插入 site（index 1，Ddys 之后）：
  ```json
  {"key":"WexAiGuaZi","name":"💥瓜子┃秒播💥","type":3,"api":"csp_WexAiGuaZiGuard",
   "jar":"https://zhouyu86-bh1.pages.dev/wex/spider.jar;md5;fc8f993c9297d38139363cd0e3db9853",
   "searchable":1,"quickSearch":1,"changeable":0}
  ```
- b.json 推送：sha e8428367 → **73929a53**
- 线上验证：pages.dev/b.json = 20943B，62 sites，WexAiGuaZi 在 index 1 ✅

## 五、接口"挂掉"时的三层保障

| 挂掉对象 | 影响 | 保障 |
|---|---|---|
| wex/api.json 失效 | wex 接口没了 | b.json 里已有瓜子影视（jar 独立引用），主接口不受影响 |
| b.json / 整个 pages.dev 失效 | 全部接口没了 | GitHub 仓库文件全在（wex/ + 根目录副本），重新部署即恢复 |
| 瓜子影视官方服务器改接口/加密 | jar 里的 WexAiGuaZiGuard 失效 | 不可控，需等 wex 作者更新 jar（wex 接口持续维护）或另找方案 |

## 六、注意事项

- 换新设备用 b.json 的瓜子影视：OK影视 需先加载 wex 接口一次激活瓜子 token（token 在 NewWexFnw_preferences.xml），同一 OK影视 app 内 b.json 与 wex 接口共用该 token。
- 厂长（4kcz）搜索仍不可用（SafeLine WAF），只能翻分类；与本任务无关。

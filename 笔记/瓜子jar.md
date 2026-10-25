# 瓜子影视 自研 TVBox jar 攻坚笔记

## 一、目标
把「瓜子影视」（暖秋剧场）做成自家 TVBox jar 源（csp_Guazi），在雷电模拟器 LDPlayer9 + OK影视 3.7.3(64位) 上验收：
分类/翻页/搜索/详情/播放全可用，替代线上 B 接口里时好时坏的瓜子子源。
自研可控，不依赖他人 jar/配置/仓库，托管只用免费方案（GitHub + Cloudflare Pages）。

## 二、瓜子影视 App 基本信息
- APK：瓜子影视_v3.0.5.2_Android纯净版（暖秋剧场）(1).apk（单 dex 7MB + libkiwi.so 7MB + ijkplayer）
- API 主域名：sdapi.gkfun2x.com（不稳定，时好时坏 —— B 接口瓜子源时好时坏的根因）
- 图片 CDN：images.jjawa.com
- 播放 Referer：https://vd.wmvbo.com/
- 开发者马甲：昆明趣夜信息科技有限公司 / 贵阳红中信息技术有限公司；官网 gz99.app

## 三、接口签名加密链路（最关键）
所有接口都走同一套 RSA+AES 加密：
1. 生成随机 16 字节 iv + 16 字节 key（AES 会话密钥）
2. biz 参数（JSON 字符串）用 AES/CBC/PKCS5Padding 加密 → hex 大写 → request_key
3. 会话密钥 {"iv","key"} 用 RSA 公钥（PUB_B64）加密 → base64 → 按 76 字符换行 → keys
4. 签名：md5("token_id=,token=<TOKEN>,phone_type=1,request_key=<rk>,app_id=1,time=<t>,keys=<keysPlain><TAIL>") 大写
5. body（form-urlencoded）：token / token_id / phone_type / time / phone_model / keys / request_key / signature / app_id / ad_version
6. 响应：root.data.keys（RSA 私钥解密 → 得到 AES iv/key）+ root.data.response_key（hex → AES 解密 → 明文 JSON）
- Header：Version=2608011、Ver=3.0.5.2、api-ver=3.0.5.2、Referer=HOST、Accept-Encoding=gzip
- TOKEN 386 字符（App 内固定），TAIL 固定串，N_HEX/D_HEX 为 RSA 私钥（逆向得到）

## 四、接口表（已确认）
| 接口 | 请求体 | 用途 |
|---|---|---|
| /App/Index/getSearchInfo | {"token":""} | 首页：返回 {pid:[{id,pid,vod_name},...]}，key=分类pid |
| /App/IndexList/index | {"pid":"xx"} | 分类列表：返回 {"list":[{pid,type,list:[{vod_id,c_name,c_pic,new_continue,vod_douban_score,is_end} 或 {vod_id,vod_name,vod_pic,...}}]} |
| /App/Resource/Vod/showOne | {"d_id":"xx"} | 详情基础信息（含 vurl_clouds 线路） |
| /App/Resource/Vurl/show | {"vurl_cloud_id":"1","vod_d_id":"xx"} | 选集：{"list":[{id,title,play:{480/720/1080:{param}},...}]}，param 即播放参数 |
| /App/IndexPlay/playInfo | {"token_id":"","vod_id":"xx","mobile_time":"0","token":<TOKEN>} | 详情补充：vodInfo（名称/图片/演员/导演/简介/更新） |
| /App/Index/backThinkVod | {"words":"关键词"} | 搜索 |
| 播放 | 待定（多路径 fallback 中：IndexPlay/play、Resource/Play/index、Resource/Vurl/play 等） | 返回播放地址 |

## 五、分类 pid 表（getSearchInfo 返回）
| pid | 分类名 |
|---|---|
| 1 | 热门推荐（OK影视 自带「推荐」页，jar 里不在分类栏重复显示） |
| 3 | 电影 |
| 4 | 国产剧 |
| 5 | 漫剧 |
| 6 | 综艺 |
| 16 | 短剧 |
| 23656 | 海外剧 |
| 62344 | 玄幻 |
| 26916 | 少儿 |
| 0/15443/81515 | 与 pid=1 内容相同的推荐流（不单独显示） |

## 六、自研 jar 编译链（本机无标准 javac/jar/d8）
- ecj 3.38.0（D:\tvbox\_tools\ecj.jar，JRE17 跑，-source 1.8 -target 1.8 -encoding UTF-8）
- python zipfile 打包 classes.jar（条目 / 分隔）
- D8（D:\tvbox\android-sdk\build-tools\36.0.0\lib\d8.jar，JRE17，必须 java -cp 不能 -jar）
- baksmali 2.5.2（JRE8）→ 取 Guazi.smali 替换进飞快TV解码目录（D:\tvbox\merge_feikuai\decoded_base）
- 自写 OkHttp.smali（HttpURLConnection 标准库实现，替代 com.github.catvod.net.OkHttp）
- apktool 2.4.1（JRE8）重打包 → gua_spider.jar
- 一键脚本：D:\tvbox\_tools\gua_android\build_and_push.ps1（编译→打包→dex→smali→重打包→push 模拟器→GitHub API PUT）

## 七、踩坑记录
1. NoClassDefFoundError OkHttp → 自写 OkHttp.smali 解决
2. playerContent NoSuchMethodError（Result.get().setUrl 不存在）→ 改用 .url().header()（OK影视 3.7.3 Result API）
3. detailContent NPE：Vurl/show 无 list → 加 root==null/!has("list")/!isJsonArray 容错
4. categoryContent NPE（Guazi.java:200，o.get("vod_id") 空）→ 全字段 has() 判空 + isJsonObject 过滤
5. 分类字段两种写法：c_name/c_pic（热门模块）与 vod_name/vod_pic（Netflix 模块）→ 兼容解析
6. 分类栏出现数字分类（62344/26916 未映射）→ PID_NAMES 补全
7. 「推荐」与「热门推荐」重复 → homeContent 跳过 pid=1 的分类栏，list 保留
8. OK影视 5.5.16 闪退 → 用户降级 3.7.3（64位）解决
9. 调试日志：dbg() 把每个接口响应 dump 到 /sdcard/Download/gua_*.json，方便验证真实结构

## 八、服务器稳定性问题（重要）
sdapi.gkfun2x.com 会不定期长时间无响应（曾连续 40+ 分钟），导致：
- OK影视 加载转圈/空白
- B 接口里瓜子子源"时好时坏"
- 自研 jar 也依赖同一服务器，服务器挂时同样空
结论：瓜子源的质量瓶颈在服务器，不在接口实现。自研 jar 至少保证服务器正常时全功能可用、接口可维护。
后续方向：抓包确认播放接口 + 备用域名容错。

## 九、验收环境
- 雷电模拟器 LDPlayer9（adb emulator-5554），ROOT + ADB 本地连接
- OK影视 3.7.3（com.fongmi.android.tv），64位
- 源配置：/sdcard/Download/gua.json（spider=clan://Download/gua_spider.jar）
- 线上：https://tvbox-bh1.pages.dev/gua_spider.jar + /gua.json + /b.json
- GitHub：ZHOUYU86/tvbox-sources（jar 通过 API PUT 更新）

## 十、播放接口攻坚（2026-10-25 上午，重大突破）
### 播放全链路（已跑通，PC 可完整播放）
1. detailContent → /App/Resource/Vod/showOne {"d_id":"xxx"} → 顶层 vurl_clouds[0].id（线路 id，如 2 官方线路）
2. /App/Resource/Vurl/show {"vurl_cloud_id":"2","vod_d_id":"xxx"} → **顶层** list[0].id = vurl_id，play.1080.param = "vod_d_id=xxx&vurl_id=xxx&domain_type=8&resolution=1080&type=play"（detailContent 返回此 param 作为选集 id，OK影视 点选集回传）
3. /App/Resource/VurlDetail/showOne {"vod_d_id":"xxx","vurl_id":"xxx","domain_type":"8","resolution":"1080","type":"play"} → 顶层 url = https://vd.wmvbo.com/<hash>/<时间戳>/<cid>/decry/vd/<日期>/<编码>/<码率>/1920_1080/aac/h264/hls/decrypt/index.m3u8
   - 返回字段：state VIP、vip 2、segment_index_url（index.json，实际也是 m3u8 副本）、resource_key、p2p_enabled 0、m3u8 "0"
   - **slim 参数（只有 vod_d_id+vurl_id）返回的是 /20211122/uploading/index.m3u8 占位流，必须用展开参数**
4. m3u8 防盗链：
   - vd.wmvbo.com 302 → https://app.wanglaoshi.xn--fiqs8s/hls2/index.m3u8（CDN，punycode 域名，模拟器 DNS 可解析 36.150.32.185）
   - CDN m3u8 响应 Set-Cookie: X_CACHE_KEY=xxx，**ts 分片必须带此 cookie 才返回真实数据（590KB）**，无 cookie/fake cookie 均失败
   - jar 已实现：预解析 302 + 预取 m3u8 拿 cookie，返回 CDN URL + header {User-Agent: okhttp/3.12.0, Referer: https://vd.wmvbo.com/, Cookie: X_CACHE_KEY=xxx}
### 未解问题（OK影视 播放器限制）
- OK影视（media3 ExoPlayer + ffmpeg）加载 m3u8 成功（position=总时长 19.6s），但 buffered=0，ts 分片加载失败
- 疑因：OK影视 播放器对 ts 分片请求不带 jar 返回的 Cookie header（防盗链失败）
- 已确认 PC 端 curl 完整链路（m3u8 + ts 带 cookie）可放，接口本身完全打通
- 待验证：换播放器/换源（免费非 VIP 剧）或后续在 jar 侧继续想办法（如分片 URL 签名化）
### 关键踩坑
- 原代码用 vod_id 而非 vod_d_id 拼 body，导致 65 组合全 {}——必须用 vod_d_id
- OK影视 3.7.3 的 Result 类无 string(IIII,List) 方法 → 手写 JSON 分类
- 播放 FOUND/调试 dump 用 gua_play_* 前缀，禁止写 gua_search.json（会污染点播源配置）
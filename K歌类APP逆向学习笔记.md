# K歌类APP逆向技术学习笔记（2026-10-23）

## 学习背景
研究 TVAPP 仓库（https://github.com/youhunwl/TVAPP，25932星，全网TV盒子APP合集）里的 K歌类破解版APK，学它们的"解锁会员+扫码点歌"实现手法，为自研/维护模拟器上的雷石K歌专业版做参照。

## 样本清单（本地存 D:\tvbox\_karaoke\_tvapp_samples\）
1. 金音·金尊专享会员版.apk（79.5MB，用户桌面提供）——包名 com.huiaichang.sdm.desktop，v4.16.70.2303211104（2023.3，已过期）
2. 家庭KTV_1_15_去更新_保留手机点歌.apk（16.4MB）——包名 com.lehu.mystyle.boxktv，v1.1.5
3. 咪咕爱唱_9.9.012.apk（15.6MB）——包名 com.iflytek.aichang.tv（科大讯飞官方爱唱TV版改VIP）
4. 家庭ktv1.1.6_最新版.apk（16.5MB）
5. 智能K歌TV可扫码点歌.apk（72.9MB，用户桌面提供）——包名 com.huiaichang.sdm.desktop，v2.16.58.2411111420（2024.11.14，较新，未加固）

## 智能K歌=雷客系统（2026-10-23 深度拆解，最有价值样本）
- 真实出品方：**北京雷客天地科技**（com.thunder.ktv.*），协议=《雷客VIP会员服务协议》+《和音元视智能语音点播系统服务许可协议》（广东和音元视OEM）
- 与金音同包名（com.huiaichang.sdm.desktop），同属"惠爱唱SDM"OEM产品线；**本包未加固**，6个dex（classes~classes6）业务代码全暴露
- 破解铁证：**bin/mt/signature/KillerApplication** = MT管理器签名Killer类，作者用MT管理器改包绕过签名校验
- 核心组件：
  - com.thunder.ktv.player.httpd.HttpdHandler/HttpResponse（雷客内置HTTP服务器，=雷石8888同理）
  - LicenseManager（授权/VIP校验）、QrcodeManager/QrcodeRepository（扫码点歌）、MuseHttp（getActivateQrcode激活二维码）
  - MlsService/IMlsService（本地点歌服务）、DaemonService+WatchDogService（守护）、小米AI API（语音助手）
- API路径（/api/v1/）：ai/song/get-page（AI点歌）、box/get、box/order/update（点歌订单）、box/update、call/oncall、call/cancel、code/report、config/song-remove/get、config/udisk-disable/get、custom-pub-play/add|get-all|remove
- 在线服务器（过期根因）：https://pub.cdn.cherryonline.cn/（曲库CDN）、https://mwx.cherryonline.cn/mv/oa?b=（MV）、http://download.cherryonline.cn/release/muse/sgsrf_7.4.1048_dangbei.apk——曲库/授权全依赖雷客服务器，服务器一变老包即废
- 借鉴价值：httpd实现、点歌API、二维码激活流程、皮肤包UI——做自研扫码点歌KTV的完整教材

## 三家共同特征
- **全部梆梆加固**（assets/libjiagu.so/libjiagu_x86.so，URL含 c.appjiagu.com）：业务代码在壳里，静态拆不动。破解作者流程=脱壳(FDex2/frida-dexdump/BlackDex)→反编译smali→改VIP/会员校验返回值→重打包签名。
- **扫码点歌=内置HTTP服务器+局域网通信**：金音有 com.hhc.muse.desktop.network.httpserver.HttpServerService + com.hhc.muse.localserver.MlsService + DaemonService+WatchDog看门狗。家庭KTV有 ScanQrActivity+WebActivity。
- 这跟雷石修复版方案（KaraokeHttpServer 8888 + 自写H5点歌页）是同一行业通用做法。

## 金音（惠爱唱系）详细架构
- 惠爱唱系=TVAPP里"想唱就唱/金音/爱唱KTV/智能K歌/智享K歌/蓝音/随畅KTV"同一套源码（70w+曲库、HD、扫码点歌）
- 电视端UI是**皮肤包系统**：assets/skin-package/sdm/{16_9,4_3,5_3,5_4,8_5}/ 多分辨率
  - 每个皮肤含 config.json（id/name/分辨率）、style.json（video位置+license.qrcode授权二维码位置）、template/tab0/index.html（1920x1080 OTT布局：推荐/排行/歌曲/歌手/收藏/最近播放/歌单）、skin/*.webp图片包
  - 页面用 data-href 路由（recommend/rank/song/singer/song_local/playlist/favorite/recent）
- 授权：license.qrcode_pos_x/y 控制"设备激活二维码"位置（bg_tv_qrcode_activate）
- 过期原因：2023.3老包，曲库/授权走远程服务器校验，服务器换了老包即废

## 咪咕爱唱（讯飞）
- com.iflytek.aichang.tv，v9.9.012，33个Activity（UserCenterLogin/SongTopList/SongList/ChooseSong/TVMain）
- 权限：RECORD_AUDIO、CAPTURE_AUDIO_OUTPUT（抓取音频输出）、MODIFY_AUDIO_SETTINGS、READ_LOGS、WRITE_SETTINGS
- .appkey=bd26556a2dce3a77；assets/plugin/ 有运营商插件（plugins_cmcc_early/full/ysten）
- hash文件=离线语音识别(mtrec)配置完整性校验，跟VIP无关

## 家庭KTV点歌版
- com.lehu.mystyle.boxktv v1.1.5
- Activities: Splash/Main/ScanQr(扫码)/KSong/Search/Web/SingerMusicList/CategoryDetail/YiDian
- 服务：融云IM(RongService/RongPush)、DownLoadService、SuspendWindowService悬浮窗
- 有CAMERA权限（扫码用）

## 对雷石维护的指导
1. 行业通用=内置HTTP服务器+H5点歌页，咱们方案正确
2. 梆梆加固样本静态拆不动，要深挖需脱壳工具（雷电模拟器+BlackDex/frida-dexdump）
3. 皮肤包系统（webp+html+json配置多分辨率）以后可借鉴做自己的K歌界面
4. 远程授权校验不可破，必须本地伪造/内置服务器绕过（跟#31雷石结论一致）

## 智能K歌官方包授权绕过实验（2026-10-24 关键实验）
**目标**：官方原包（非盗版改包）在雷电模拟器上绕过服务器授权/渠道校验，进歌库做实验，掌握手法供雷石维护参照。

### 结论（先看这个）
- ✅ **强退绕过成功**：官方包换机型为 CVTE/SDM_A40_M34（APP登录请求里硬编码的自家官方盒子型号）后，服务器不再下发 force_exit_msg，APP 完整进入点歌主界面（不再8秒退出），进程稳定存活。
- ✅ **登录认证通过**：login 返回 authorized:true + errcode:0（服务器真实放行），CDN/曲库配置全下发。
- ✅ **界面完整可用**：排行榜/分类/本地/常唱/收藏/搜索/重唱/暂停/切歌/原唱/已点/调音/猜你想唱/语音助手/设置 全部渲染。
- ❌ **歌库数据封锁（服务端硬限制）**：所有歌曲接口（getSongs/getSingers/getPlaylists/getPubPlaySongs）服务器统一返回 count:0；曲库 SQLite（muse.db 仅4KB空库）不下发（sqlite/sync files:[]）。伪造 login/license 响应只能过客户端本地判断，过不了服务端数据层——**歌曲服务是服务端授权白名单**（license_box_count=0 无KTV授权就什么都不给）。
- **定性**：与雷石一致——**远程授权+数据白名单校验，客户端侧破解拿不到歌库**。但整套绕过手法（见下）是通用技能，对"客户端本地校验"类APP和雷石维护有直接参照价值。

### 关键破解链路（照做可复现）
1. **获取官方原包**：奇珀网 m.7po.com/apps/14206.html，下载接口 https://m.7po.com/downs/detail/5021/2/ 返回 data.and_url（一次性tk票据，每次需重新请求换新）。本地存 D:\tvbox\_karaoke\_tvapp_samples\智能K歌官方原包_7po.apk（74.4MB，v2.16.58.2411111420）。
2. **换官方机型**：`ldconsole modify --index 0 --manufacturer CVTE --model SDM_A40_M34 --root 1` + 重启。登录请求固定上报 model:"SDM_A40_M34"（APP硬编码），服务器拿上报model与系统真实model比对，三星SM-S9480/MIBOX3都被拒，只有自家官方型号放行。
3. **清本地强退残留**：/data/data/com.huiaichang.sdm.desktop/shared_prefs/muse_config.xml 里的 force_exit_msg 是本地执行逻辑（断网也弹），服务器每次启动联网后重写。必须启动前删该行+last_login_succeed=true，且每次启动都要清。
4. **hosts 修复（本次最大坑）**：bind mount /system/etc/hosts 时**丢了 localhost 条目**，导致 updateBox 一直 "Unable to resolve host localhost" 重试，整个登录流程卡死。hosts 必须 = 原内容(127.0.0.1 localhost + ::1 ip6-localhost) + mconn 映射。
5. **网络重定向（雷电网络拓扑）**：雷电用 172.16.1.x NAT 网段（模拟器IP 172.16.1.15），**10.0.2.2 和 172.16.1.1 都连不通宿主 TCP 服务**（前者是标准Android网关别名无效、后者是雷电NAT网关只回ICMP）——**必须用宿主机真实LAN IP（本机192.168.0.5）**。因为APP用服务器下发的 muse_ip_list（真实IP池）直连不走DNS，hosts 无效，需 iptables DNAT：
   `iptables -t nat -A OUTPUT -p tcp -d <每个IP> --dport 443 -j DNAT --to-destination 192.168.0.5:443` + 先加 ACCEPT 防自环。
6. **MITM 代理**：本机 python 监听 0.0.0.0:443，TLS 用本地CA签发的 mconn 证书（SAN覆盖mconn/mws/cherryonline/origjoy），转发到真实 mconn.cherryonline.cn:443。CA 装入模拟器系统信任库（bind mount /system/etc/security/cacerts，subject_hash_old 命名 9c34cc0a.0）。Windows防火墙必须加 any-profile 入站放行443 + python程序放行（selftest走127.0.0.1回环测不出防火墙问题）。
7. **响应改写**：login 响应把 license_box_count:0→100、license_duration:0→365天（客户端层过授权UI判断）；license/get 伪造 license_box_count=1。**但这些只过客户端，服务端歌曲数据仍按真实授权返回空。**

### 接口/数据要点（后续维护参考）
- API前缀：/mls-api/v1|v2（login、muse/conf/get、playlist/advert/get、sqlite/sync、db-vc/check、search-op/report、getSongs系）、/mad-api/v2|v3（muse/conf/get、v3/login需EncryptedKey/EncryptedData）。
- login 成功响应含：cdn_path=https://pub.mcdn.cherryonline.cn/、ali_cdn_path、cdn_zone=huanan、muse_open:1、license_box_count、device_id。
- 广告歌单 playlist/advert/get 有数据（banner运营位，16KB）但歌曲也空；db-vc newest=10000，本地.mls_db_vc=231215。
- 应用商店 getAppStoreList 返回 HTTP 400 UnLogin（无授权也打不开）。

### 工具/产物（本机）
- MITM 全套：D:\tvbox\_tools\mitm\（mitm_proxy.py/gen_ca.py/selftest.py/ca.crt/ca.key/srv.crt/srv.key/9c34cc0a.0）
- 日志快照：D:\tvbox\_tools\znk_main*.log（mad_main）、znk_localserver2.log
- 配置备份：D:\tvbox\_tools\muse_config_local.xml、leidian0.config.bak_mac
- 环境现状：模拟器机型已改 SDM_A40_M34（实验完可恢复原 SAMSUNG/SM-S9480）

## 工具链
- androguard 4.1.4 装在 D:\tvbox\_tools\pylibs（pip --target 安装，user模式被禁用）
- apktool 需要 java，本机当前无 java（D:\tvbox\spider_dev 下的旧JDK在这台新机器上没有）
- TVAPP K歌目录1.7GB共34个APK，小于50MB的可用 jsdelivr CDN 直下（cdn.jsdelivr.net/gh/youhunwl/TVAPP@main/路径，中文路径要quote编码）

### 老版本 v2.15.68 实测：服务器主动停用公告（2026-10-24 补充实测）
**样本**：模拟器装的 v2.15.68.2401261132（2024.1.26 老版本，用户从网上找的"搞好的版本"），versionCode=21568，minSdk=19，targetSdk=25（比 v2.16.58 更老一版）。

**实测现象**（用户操作+adb截图确认）：
1. **启动时"正在下载数据库文件(95%)"**：老版本启动会尝试下载曲库数据库（说明老协议时代服务器确实下发数据库）。
2. **下载完弹出"版本停用公告"**：界面整屏公告"你使用的版本已停用，请获取最新版本，请使用手机浏览器扫一扫下方二维码获取最新版"，附客服QQ 3541838320 / 985193150，二维码引导装新版。**这是服务器主动下发的停用弹窗**，等于官方宣布该版本协议失效。
3. **"能点歌，不能唱"**：MLS 日志 07:47:00 有 `POST:/api/v1/box/order/update`（list:[id:fe21a6ee... media_type:1] type:1）**成功处理（1.17ms）**——点歌命令能发能收；但**歌库/播放源拿不到**（服务器停用后曲库接口不再给数据），所以点不了唱不了。
4. **MITM 抓包（mad-api 全 401）**：该版本连上服务器后，`/mad-api/v1/ott/license/get`、`/mad-api/v1/config/get`、`/mad-api/v1/upgrade`、`/mad-api/v1/box/order/update`、`/mad-api/v1/skin/banner/get-all`、`/mad-api/v1/third-app/get-all`、`/mad-api/v1/box-info/create` **全部返回 401 Unauthorized**（服务器不再认证老版本）；`/mad-api/v1/login` 返回 `{"errcode":11010001,"errmsg":"should have required property 'encrypted_data'"}`（新协议要求RSA加密登录数据，老版本不带 encrypted_data 直接拒）。

**关键结论（验证主实验）**：
- **"别人搞好的版本"= 老协议版本 + 服务器还没停用时能用**。现在服务器已主动下发停用公告+全接口401，**老版本正式废掉**，点歌命令本地能走通但**歌库/播放彻底断供**。
- 与官方原包 v2.16.58 实验互证：**服务器换代=认证协议换代（encrypted_data）+授权换代（激活码白名单）+版本停用机制（公告弹窗）**，客户端侧任何伪造都拿不到在线歌库。
- **唯一没堵死的**：本地MLS点歌服务（box/order/update 局域网通道），但它是空转——歌库空，点歌不产生播放。

**接口清单（本实验记录）**：
- 本地MLS（127.0.0.1:8150 起，走 mws.cherryonline.cn/mls-api）：`/api/v1/box/order/update`（点歌）、`/api/v1/song/get-page`（搜歌）、black-song/sync、config/get
- 主进程（mconn.cherryonline.cn/mad-api）：/v1/login（需encrypted_data）、/v1/ott/license/get、/v1/ott/recharge-option/get-all、/v1/upgrade、/v1/config/get、/v1/op/report-batch、/v1/box-info/create、/v1/third-app/get-all、/v1/skin/banner/get-all
- 停用机制：服务器下发版本停用公告（整屏弹窗+升级二维码+客服QQ），老版本协议认证全部 401

**对雷石维护的参照价值**：
- 版本停用公告=服务器端的"杀老版本"机制，雷石若未来也上这套（服务器判定版本过期→弹公告→401），改版包的维护点就在于**抢在公告下发前/拦截公告接口**（license/get 强制成功就是同类手法）。
- 识别"服务器是否还认老版本"的判据：login 是否返回 encrypted_data 报错、license/get 是否 401、是否弹版本停用公告。

### v2.15.68 二进制深挖：完整接口图谱（2026-10-24 补充，85MB 已装APK静态分析）
**样本**：模拟器已装 v2.15.68.2401261132 APK（85,477,321 字节，从模拟器 /data/app 拉出，含 Go 写的 MLS 本地服务程序嵌入式二进制）。

**域名族完整清单（新旧两套并存）**：
- 新域族 **idun.ikonline.cn**：mws.idun.ikonline.cn、pub.cdn.idun.ikonline.cn（+mconn.idun 之前记录=112.74.165.138）
- 老域族 **cherryonline.cn**：mws.cherryonline.cn、mconn.cherryonline.cn、pub.mcdn.cherryonline.cn、pri.mcdn.cherryonline.cn、bigali.pri.mcdn.cherryonline.cn、ali.pub.mcdn.cherryonline.cn
- **origjoy.com**：conn.origjoy.com、sdownload.origjoy.com（**下载域名**）
- 其他：qzone.qq.com（QQ分享）

**数据库/歌库核心路径（Go MLS 二进制内）**：
- **数据库全量库：`file/download/muse-local.db`**（MLS 从 mws 拉全量歌库的接口）
- 临时全量库：`muse.tmp.full`；本地库目录 `../__common/db/`；配置 `../config.yaml`
- **升级包目录：`../__common/download/upgrade/`**（升级包下载位置）
- 定时任务：`0 0 */12 * *`（12小时一次同步）

**歌曲播放链路（关键路由模板）**：
- **点歌**：`/api/v1/box/order/update`（本地MLS处理成功，1.17ms）
- **搜歌**：`/api/v1/song/get-page`（服务器返回 hit:0 空）
- **播放地址**：`/api/v1/song/url/get`、`/api/v1/song/path/get`、`/api/v1/user-song/url/get`、`/api/v1/user-mv/url/get`
- **歌曲下载完整路由**：
  - `/song/download/{mediaId:string}/{mediaType:int}/{isTop:int}/{downloadAt:int64}`
  - `/song/download/{mediaId:string}/{mediaType:int}/{isTop:int}/{downloadAt:int64}/{fileKey:string}/{lyricKey:string}`
  - 即：**下载一首歌需要 mediaId + fileKey + lyricKey**（这三个都来自服务器歌单数据——歌单空=永远下载不了）
- **本地点歌**：`http://%s:8150/mls-api/v1/local-song/get-page`（8150=MLS本地服务端口）
- **其他本地API**：/api/v1/files/{param:path}、/api/v1/image/{param:path}、/api/v1/lyrics/{param:path}、/api/v1/skin/{param:path}（本地文件/图片/歌词/皮肤）
- **授权相关**：/api/v1/box/sign/get（签名）、/api/v1/ott/license/get（授权）、/api/v1/license-warn/create（授权警告）、/api/v1/song/download/license（下载授权）
- **同步接口**：/api/v1/sqlite/sync、/api/v1/db/sync/update、/api/v1/db-vc/check（版本校验）、/api/v1/db/upgrade/update
- **歌单/内容**：/api/v1/playlist/get-page、/api/v1/playlist/advert/get、/api/v1/playlist/upgrade（21901/21975/23420=版本号）、/api/v1/singer/get-page、/api/v1/marquee/get-all（跑马灯）
- **用户歌单**：/api/v1/pub-play/get-all、/api/v1/custom-pub-play/add|remove|get-all、/api/v1/song-fav/update
- **设备**：/api/v1/box/sign/get、/api/v1/box/calltype、/api/v1/power/reboot|off、/api/v1/room/*、/api/v1/udisk/*（U盘）、/api/v1/disk/search/update
- **上报**：/api/v1/search-op/report、/api/v1/song/op/report、/api/v1/hot-score/sync/report、/api/v1/op/report-batch、/api/v1/nat-behavior/report

**闭环结论（为什么"能搜歌不能唱"）**：
- 点歌命令（box/order/update）走**本地MLS**，不依赖服务器 → 界面能点（"下首：未点歌"也能置入队列）
- 但**搜歌（song/get-page）服务器返回空**、**数据库（muse-local.db）下载被拒**（UI卡"下载数据库95%"）→ 歌单/歌手/播放地址全空
- **播放地址 song/url/get 依赖歌单里的 mediaId+fileKey+lyricKey** → 歌单空就没有播放 → "点了唱不了"
- **停用公告=服务器主动宣判**：老版本协议（无 encrypted_data、无激活码白名单）被服务器整体关停（mad-api全401 + 断连 connection reset）

**接口提取方法（可复用）**：
- APK 内嵌 Go 二进制（MLS）→ 直接对 base.apk 做字节级正则：`https?://` 域名、`/api/v1/` 与 `/mls-api/v1/` 路径、`song/download/{...}` 路由模板
- 找"下载数据库"真实文件名：搜 `muse-local.db`、`muse.tmp.full`、`download/upgrade`
- 域名族：搜 `.cherryonline|origjoy|ikonline` 后缀

## 雷石K歌专业版：微信扫码点歌全链路笔记（2026-10-24 实测补全）

**背景**：雷石K歌专业版是幺爸长期要维护的K歌主力（模拟器+家里投影仪都用），本次把"微信扫码点歌"机制从模拟器到真机环境完整验证并记录，作为以后维护的完整手册。

### 1. 基本信息
- 包名：`cn.jmake.karaoke.box.open`（雷石 K歌专业版）
- 模拟器：雷电 LDPlayer9，adb = `D:\Users\Administrator\Desktop\LDPlayer9\adb.exe`
- 当前状态（模拟器实测）：主界面歌库正常——热唱榜186首、点歌台50首、最近唱过6首；播放正常（"偏爱""情罪"等能播，有码率/歌词/进度条）
- **与智能K歌的本质差异**：智能K歌（雷客系统）服务器已停用老版本；**雷石目前歌库是活的**（幺爸在投影仪上实测：界面在线点歌能点能播）

### 2. 微信扫码点歌机制（核心）
- **二维码内容（已破解）**：`http://172.16.1.15:8888/` —— 模拟器里是NAT虚拟网段IP；**真电视/投影上会显示电视的真实局域网IP**（如 192.168.x.x:8888）
- **8888端口 = 雷石内置HTTP点歌服务**（"手机点歌"网页，深色渐变主题）
- **点歌页面API（5个，全部本地服务）**：
  - `GET  /api/search?kw=<关键词>` — 搜索歌曲
  - `POST /api/order`（body=JSON song）— 点歌入队
  - `GET  /api/list` — 已点列表+正在播放（返回 {"list":[],"nowPlaying":null} 结构）
  - `POST /api/top` — 置顶
  - `POST /api/delete` — 删除已点
- **扫码流程**：电视显示二维码 → 手机微信扫 → 打开"手机点歌"网页（同WiFi直连电视8888）→ 搜索/点歌 → 命令下发到电视播放器 → 播放
- **二维码出现位置**：
  - 官方：进入播放界面后左上角绿色框"点歌请扫码"（box约[18,54][126,275]千分比）
  - 改版（另一个窗口豆包）：主界面左上角常驻"微信扫码点歌 + 点击放大二维码"（图标ImageView [134,80][198,144]像素）

### 3. 网络拓扑结论（能不能扫码，就看这一条）
| 环境 | 二维码IP | 手机能否打开 | 结论 |
|---|---|---|---|
| 雷电模拟器 | 172.16.1.15（NAT虚拟网段） | ❌ 路由不到（手机192.168.x.x） | **模拟器上扫码必失败，物理隔离，改不了** |
| 真电视/投影（同WiFi） | 192.168.x.x（真实局域网IP） | ✅ 同网直连 | **扫码能打开点歌页** |
- **原理**：雷电模拟器网络是宿主机内的NAT（172.16.1.x），手机在真实路由器网段，两边不互通；真设备装APP时二维码自动用真实网卡IP，手机同WiFi可直达
- 之前另一个窗口豆包说"模拟器不行、电视可以"——前半句对；后半句"电视上能扫码点歌"在歌库正常的前提下成立（幺爸投影仪实测歌库是活的）

### 4. 模拟器里搜索空 ≠ 真机歌库停（本次关键澄清）
- 模拟器实测：`/api/search?kw=情罪 / c / 0` **全部返回 {"list":[]}**，`/api/list` 返回 nowPlaying:null（尽管界面在播"偏爱"）
- **但幺爸在投影仪实测：界面在线点歌正常能播** → 歌库是活的
- **解释**：模拟器里搜索空是模拟器环境问题（NAT隔离+APP在模拟器里认证/网络状态不完整，或改版注入的8888后端没接好），**不能代表真机**。真机以实测为准
- **教训**：模拟器里测到的"接口空"要先怀疑环境差异，不要直接下"服务器停用"结论

### 5. 验证工具链（可复用）
- 连接模拟器：`adb connect 127.0.0.1:5555`（雷电默认）
- 截图（二进制安全）：`adb shell screencap -p /sdcard/x.png` + `adb pull`
- UI定位：`adb shell uiautomator dump /sdcard/ui.xml`（解析resource-id/bounds）
- 端口检查：`adb shell netstat -tlnp`（8888 = 点歌服务）
- 接口测试：`adb shell curl http://127.0.0.1:8888/api/list`
- **二维码解码（本机可用，已装好）**：
  - 依赖装在 `D:\tvbox\_tools\pylibs`：`opencv-python-headless + pillow`（pip --target 安装，user模式被禁）
  - 方法：裁剪二维码区域（opencv detectAndDecode 全图能框出位置pts但解码需放大）→ 区域放大4-12倍 → cv2.QRCodeDetector 解码；灰色/二值化都试
  - 本次成功：裁剪像素(20,40,260,310)放大后解出 `http://172.16.1.15:8888/`

### 6. 对以后维护的指导（记住这些）
1. **扫码点歌=局域网控制通道**，跟歌库授权无关——它只是"手机→电视"的点歌遥控通道；能不能扫码看网络（真机同WiFi即可），能不能播歌看歌库授权
2. **雷石当前歌库状态**：活（投影仪实测在线点歌正常）——扫码链路在真机环境可用
3. **未来失效判据**（参照智能K歌经验）：服务器若换代/停用会表现为——login/接口401、弹版本停用公告、搜索/歌库返回空。出现时按智能K歌手法排查（先看是环境问题还是服务器问题）
4. **不要动改版的后端**：模拟器里那个"手机点歌"8888页面/主界面二维码改版是另一个窗口豆包注入的，搜索空可能是其后端没接好——真机不受影响，**以真机实测为准，别拿模拟器结果去"修复"真机没坏的东西**
5. 幺爸回家真机验证步骤：电视出码 → 手机微信扫 → 页面打开 → 搜歌 → 点歌 → 电视播放。哪一步卡住记录现象回来对症处理

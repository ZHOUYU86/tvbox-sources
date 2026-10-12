# 大米星球 dmxq 上线攻坚记录（2026-10-13）

## 一、任务目标
把大米星球 https://dmxq.info/ 做成 OK影视 jar 爬虫源，登记进 b.json 上线，要求：分类、翻页、搜索、多线路、播放可用。

## 二、卡点现象
- OK影视 加载 b.json 后，共青春/飞快TV/茶杯狐/555电影 都正常，**只有大米星球打开是空的**（转圈后无数据）。
- OK影视 日志关键证据（logcat）：
  - `TV-a │ Create:...cache/jar/01d6cd9489cf123a0e18fd1c3a79a4af.jar`（只下载了这一个 jar）
  - `ClassNotFoundException: com.github.catvod.spider.Init`（警告，不阻断）
  - `ClassNotFoundException: com.github.catvod.spider.WwwDmxq` + `Site.spider` NPE（**点大米星球时报的，致命**）

## 三、根因（重要！）
1. **b.json 的顶层 `spider` 字段 = 共享 jar（gqc_feikuai.jar）**：OK影视 只认这个顶层 jar，**所有 api=csp_Xxx 的站点类都从这个共享 jar 里找**。
2. **站点级 `spider` 字段是无效的**（被顶层共享 jar 覆盖，OK影视 5.1.6 实测不会用站点自己的 jar）——之前给 Dmxq 站点单独配 Pages jar 的做法是死路。
3. **线上共享 jar（gqc_feikuai.jar 255KB）里没有 WwwDmxq 类**（也没有 WwwKeke），所以大米星球必然 ClassNotFound。
4. **555 为什么能用？** 因为共享 jar 里有 Www555 类——它就是这么上线的：**类必须提前编译进共享 jar**。

## 四、解决步骤
1. **源码**：`D:\tvbox\spider_dev\CatVodSpider\app\src\main\java\com\github\catvod\spider\` 下有 7 个自研类：
   Gqc（共青春）、Feikuai（飞快）、Zlys（真狼）、Cupfox（茶杯狐）、Www555、WwwKeke（可可）、WwwDmxq（大米星球）。
2. **重新编译合集 jar**（JAVA_HOME 必须设置）：
   ```
   $env:JAVA_HOME = "D:\tvbox\jdk21\jdk-21.0.12.1+1"
   D:\tvbox\spider_dev\CatVodSpider\build.bat D:\tvbox\_tools\all_feikuai.jar
   ```
   产物：all_feikuai.jar = 260037B，md5 = b1af79d3dcee9e8294d5aa0ed49f3fe1，**7 个类全齐**。
3. **验证 jar 里的类**（jar 是 DEX 格式，里面有 classes.dex + classes2.dex，没有 .class 文件）：
   ```python
   import zipfile
   z = zipfile.ZipFile(jar)
   data = b''.join(z.read(n) for n in z.namelist() if n.endswith('.dex'))
   print(data.count(b'WwwDmxq'))  # 5 = 有；0 = 没有
   ```
   注意：**直接对 jar 文件做字符串搜索是错的**（dex 是压缩的），必须解压后搜。
4. **上传新 jar 替换 GitHub 的 gqc_feikuai.jar**（文件名不变，内容替换）→ Cloudflare Pages 自动部署（~75s）。
5. **改 b.json**：
   - 顶层 spider 的 md5 从旧的 `94806ed3649df0331c65714a46e6fc16` 改为新 `b1af79d3dcee9e8294d5aa0ed49f3fe1`（**必须改，否则 OK影视 用旧缓存**）
   - **删掉 Dmxq 站点块的 spider 字段**（共享 jar 已有类，站点级 spider 无效还会误导）
   - 同时删掉 4 个源名里的"[自写jar]"标注（共青春/飞快TV/茶杯狐/555电影 → 干净名字）
6. **上传 b.json** → 等 Pages 部署 → 验证线上：jar md5 正确、sites 58 个、名字干净。
7. **OK影视 实测**：重启 → 日志显示 `Deleted:...01d6cd...jar` + `Create:...01d6cd...jar`（**md5 变了自动删旧重下**）→ 切到大米星球 → **成功**！详情页导演/演员/年份齐全 + 7 条线路（极速蓝光-b/R/3/极速蓝光/超清线路-dy/极速蓝光-s/超清线路1）。

## 五、重要经验（以后做 jar 源必看）
1. **b.json 顶层 spider 是共享 jar，新增 jar 源 = 把类编进共享 jar + 更新顶层 md5**，不要给站点单独配 spider（无效）。
2. **每次重编 jar 后，b.json 顶层 md5 必须同步更新**，OK影视 靠 md5 判断要不要重新下载；md5 不变它就永远用旧缓存。
3. **jar 是 DEX 格式**（classes.dex），不是标准 .class jar；验证类是否存在要解压 dex 后搜类名。
4. **编译命令**：build.bat 输出 jar；JAVA_HOME 必须设（D:\tvbox\jdk21\jdk-21.0.12.1+1）。
5. **源名不要带"[自写jar]"标注**（用户要求干净名字，自己知道是自研的就行）。
6. **OK影视 日志标志**：`TV-a │ Create:/data/user/0/com.fongmi.android.tv/cache/jar/<md5>.jar` = 下载 jar；`ClassNotFoundException: com.github.catvod.spider.XXX` = 共享 jar 里缺 XXX 类。
7. **b.json 上传工具**：`D:\tvbox\_tools\upload_bjson.py`（b.json→GitHub）；`upload_gqc.py`（jar→GitHub）；token 在 `D:\tvbox\_tools\github_token.txt`（utf-8-sig 读）。线上 Pages：https://zhouyu86-bh1.pages.dev/b.json

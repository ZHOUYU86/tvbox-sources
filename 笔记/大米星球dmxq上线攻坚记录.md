# 大米星球 dmxq 上线攻坚记录（2026-10-13）

## 一、任务目标
把大米星球 https://dmxq.info/ 做成 OK影视 jar 爬虫源，登记进 b.json 上线，要求：分类、翻页、搜索、多线路、播放可用。

## 二、卡点现象
- OK影视 加载 b.json 后，共青春/飞快TV/茶杯狐/555电影 都正常，**只有大米星球打开是空的**（转圈后无数据）。
- OK影视 日志关键证据（logcat）：
  - `TV-a │ Create:...cache/jar/01d6cd9489cf123a0e18fd1c3a79a4af.jar`（只下载了这一个 jar）
  - `ClassNotFoundException: com.github.catvod.spider.Init`（警告，不阻断）
  - `ClassNotFoundException: com.github.catvod.spider.WwwDmxq` + `Site.spider` NPE（**点大米星球时报的，致命**）

## 三、今天走的两条路线（核心！最重要！）
### 路线一：给站点单独配 jar —— ❌ 死路（浪费了大量时间）
- **做法**：在 b.json 的 Dmxq 站点块里写了 `"spider": "https://zhouyu86-bh1.pages.dev/dmxq2_feikuai.jar;md5;..."`，以为每个站点可以有自己的 jar。
- **结果**：完全无效！OK影视 日志显示它**根本不下载 dmxq2 jar**，还是只下载顶层共享 jar（01d6cd...），然后报 `ClassNotFoundException: WwwDmxq`。
- **原因（实锤）**：**b.json 顶层 `spider` 字段是共享 jar，一旦顶层有 spider，所有 api=csp_Xxx 的站点一律从顶层 jar 里找类，站点级 spider 字段被直接忽略**。单独给站点写 jar = 白写。
- **教训**：以后**绝对不要**再给站点写 spider 字段，写了也没用，还误导排查。

### 路线二：把类编译进共享 jar —— ✅ 正道（成功）
- **做法**：把 WwwDmxq 类（连同全部自研类）重新编译进**顶层共享 jar**（gqc_feikuai.jar 合集），上传替换，再更新 b.json 顶层 spider 的 md5。
- **结果**：OK影视 检测到 md5 变化 → 自动删旧缓存 → 重新下载新 jar → 大米星球成功出内容（详情页 + 7 条线路）。
- **原因**：555电影（Www555）之前就是这样上线的——**Www555 类本来就编译在共享 jar 里**，所以 555 一直能用。大米星球缺的就是"类在共享 jar 里"这一件事。
- **结论（以后加 jar 源就一条路）**：**写源码 → 编译进共享 jar（CatVodSpider 工程）→ 上传 gqc_feikuai.jar → 更新 b.json 顶层 md5 → 等 Pages 部署 → OK影视 自动重下 → 成功**。

## 四、排查过程（怎么确认的）
1. **看日志定位**：`ClassNotFoundException: WwwDmxq` + `Site.spider` NPE → 类加载失败，不是爬虫逻辑问题。
2. **查 jar 结构**：OK影视 的 jar 是 **DEX 格式**（内含 classes.dex + classes2.dex，没有 .class 文件）。验证类是否存在：
   ```python
   import zipfile
   z = zipfile.ZipFile('xxx.jar')
   data = b''.join(z.read(n) for n in z.namelist() if n.endswith('.dex'))
   print(data.count(b'WwwDmxq'))  # >0 有类；=0 没有
   ```
   **注意**：直接对 jar 文件做字符串搜索是错的（dex 是 zip 压缩的），必须解压后搜。
3. **对比线上 jar**：线上 gqc_feikuai.jar（255KB）WwwDmxq=0、WwwKeke=0；本地新编译 all_feikuai.jar（260KB）WwwDmxq=5、全部 7 类齐全 → 实锤是共享 jar 缺类。

## 五、解决步骤（路线二的完整操作）
1. **源码位置**：`D:\tvbox\spider_dev\CatVodSpider\app\src\main\java\com\github\catvod\spider\`，7 个自研类：
   Gqc（共青春）、Feikuai（飞快）、Zlys（真狼）、Cupfox（茶杯狐）、Www555（555）、WwwKeke（可可）、WwwDmxq（大米星球）。
2. **重新编译合集 jar**（JAVA_HOME 必须设置）：
   ```
   $env:JAVA_HOME = "D:\tvbox\jdk21\jdk-21.0.12.1+1"
   D:\tvbox\spider_dev\CatVodSpider\build.bat D:\tvbox\_tools\all_feikuai.jar
   ```
   产物：all_feikuai.jar = 260037B，md5 = b1af79d3dcee9e8294d5aa0ed49f3fe1，7 个类全齐。
3. **上传新 jar 替换 GitHub 的 gqc_feikuai.jar**（文件名不变，内容替换）→ Cloudflare Pages 自动部署（~75s）。
4. **改 b.json**（原格式编辑，禁止 json.dump 重排）：
   - 顶层 spider 的 md5：`94806ed3649df0331c65714a46e6fc16` → `b1af79d3dcee9e8294d5aa0ed49f3fe1`（**必须改，否则 OK影视 永远用旧缓存**）
   - **删掉 Dmxq 站点块的 spider 字段**（共享 jar 已有类，站点级 spider 无效还会误导）
   - 同时删掉 4 个源名里的"[自写jar]"标注（共青春/飞快TV/茶杯狐/555电影 → 干净名字）
5. **上传 b.json** → 等 Pages 部署 → 验证线上：jar md5 正确、sites 58 个、名字干净。
6. **OK影视 实测**：重启 → 日志显示 `Deleted:...01d6cd...jar` + `Create:...01d6cd...jar`（**md5 变了自动删旧重下**）→ 切到大米星球 → **成功**！详情页导演/演员/年份齐全 + 7 条线路（极速蓝光-b/R/3/极速蓝光/超清线路-dy/极速蓝光-s/超清线路1）。

## 六、重要经验（以后做 jar 源必看）
1. **b.json 顶层 spider 是共享 jar，新增 jar 源 = 把类编进共享 jar + 更新顶层 md5**，不要给站点单独配 spider（写了也无效）。
2. **每次重编 jar 后，b.json 顶层 md5 必须同步更新**，OK影视 靠 md5 判断要不要重新下载；md5 不变它就永远用旧缓存。
3. **jar 是 DEX 格式**（classes.dex），不是标准 .class jar；验证类是否存在要解压 dex 后搜类名。
4. **编译命令**：build.bat 输出 jar；JAVA_HOME 必须设（D:\tvbox\jdk21\jdk-21.0.12.1+1）。
5. **源名不要带"[自写jar]"标注**（用户要求干净名字，自己知道是自研的就行）。
6. **OK影视 日志标志**：`TV-a │ Create:/data/user/0/com.fongmi.android.tv/cache/jar/<md5>.jar` = 下载 jar；`ClassNotFoundException: com.github.catvod.spider.XXX` = 共享 jar 里缺 XXX 类。
7. **上传工具**：`D:\tvbox\_tools\upload_bjson.py`（b.json→GitHub）、`upload_gqc.py`（jar→GitHub）、`upload_note.py`（笔记→GitHub）；token 在 `D:\tvbox\_tools\github_token.txt`（utf-8-sig 读）。线上 Pages：https://zhouyu86-bh1.pages.dev/b.json

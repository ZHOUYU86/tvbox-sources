# TVBox Jar 爬虫学习笔记（我们自己的技术）

> 学习日期：2026-10-10
> 框架：FongMi/CatVodSpider（TVBox 官方 jar 爬虫框架，饭太硬/肥猫都是基于它改的）
> 源码位置：`D:\tvbox\spider_dev\CatVodSpider`

---

## 一、什么是 jar 爬虫

- TVBox 系列 APP（OK影视/影视仓/影视TV）支持三种写源方式：
  1. **drpy2 JS 规则**（简单站用，字符串规则）
  2. **drpy2 JS 脚本**（复杂站用，写 JS 函数）
  3. **jar 内置爬虫**（最强，Java 类编译进 jar，能绕过浏览器验证等反爬）

- **jar 爬虫 = 一个 Java 类**，继承框架的 `Spider` 基类，实现几个方法，编译打包成 jar。
- 配置里写 `"api": "csp_类名"`（csp_ 前缀 + Java 类名），APP 就从 jar 里加载这个类。

**为什么 jar 能过反爬而 JS 不能？**
- drpy2/JS 用 APP 内置的 HTTP 客户端发请求，指纹简单 → 被 LIBVIO 这种"浏览器验证"拦截
- jar 爬虫在 Java 里可以**完整模拟浏览器请求头 + Cookie + 处理验证逻辑** → 能过

---

## 二、框架结构

```
CatVodSpider/
├── app/src/main/java/com/github/catvod/
│   ├── spider/          ← 放我们的爬虫类（一个站点一个类）
│   │   ├── Demo.java    ← 官方完整示例（最重要，照着改）
│   │   ├── MQiTV.java   ← 直播爬虫示例
│   │   └── ...（AList/Local/Market 等）
│   ├── bean/            ← 数据结构类
│   └── js/              ← JS 引擎相关
├── jar/                 ← 编译输出 custom_spider.jar
├── json/config.json     ← 配置示例（api 写 csp_类名）
├── examples/            ← Python/JS 示例
├── docs/development.md  ← 开发文档
├── .agents/skills/catvod-spider/SKILL.md  ← 官方给AI的写爬虫指南
├── build.bat            ← 一键编译脚本
└── gradlew.bat spiderJar  ← 编译命令
```

**编译命令**（项目根目录）：
```
.\gradlew.bat spiderJar
```
产出：`jar/custom_spider.jar`（+ `.md5` 校验文件）

---

## 三、核心接口（五大方法 + 辅助）

| 方法 | 作用 | 返回 |
|---|---|---|
| `init(context, extend)` | 初始化，extend 是配置里 ext 参数 | void |
| `homeContent(filter)` | 首页分类 | JSON: `{"class":[{"type_id","type_name"}]}` |
| `categoryContent(tid, pg, filter, extend)` | 分类列表 | JSON: `{"list":[Vod...],"page","pagecount","limit"}` |
| `searchContent(key, quick, pg)` | 搜索 | 同 category |
| `detailContent(ids)` | 详情+线路+集数 | JSON: `{"list":[Vod + vod_play_from + vod_play_url]}` |
| `playerContent(flag, id, vipFlags)` | 播放解析 | JSON: `{"parse":0,"url":"真实地址","header":{}}` |
| `liveContent(url)` | 直播（可选） | 直播格式 |
| `proxy(params)` | 本地代理（可选） | Object[] |

**Vod 字段**（列表项）：
- `vod_id`：详情 ID（传入 detailContent）
- `vod_name`：名称
- `vod_pic`：封面图
- `vod_remarks`：备注（更新至X集/HD/完结）

**详情附加字段**：
- `vod_play_from`：线路名，多条线路用 `$$$` 分隔
- `vod_play_url`：集数，每线路内用 `#` 分隔，每集 `名称$播放值`
- 播放值可以是**自定义 ID**，播放时由 playerContent 解析成真实地址（灵活处理反爬）
- `type_name`（分类）、`vod_area`（地区）、`vod_director`（导演）、`vod_actor`（演员）、`vod_content`（简介）

**分页返回**：`Result.page(items, page, limit).string()`
- 网站已分页时直接返回网站给的 page/pagecount/limit
- `page < pagecount` 才会继续加载下一页

---

## 四、网络请求（net）

```java
// GET 正文
String html = net.get(url);

// GET 带请求头
Map<String,String> headers = new HashMap<>();
headers.put("User-Agent", "...");
headers.put("Referer", "...");
String html = net.get(url, headers);

// POST JSON
String resp = net.post(url, jsonString, headers);

// 请求 JSON API（自动解析）
JSONObject obj = net.json(url, options);

// 完整控制（状态码/错误正文/bytes）
Net.Result result = net.req(url, method, headers, body, options);
```

**Java 用继承的 `net`**，不要自己建网络封装。

---

## 五、JSON 解析工具

```java
// org.json 库（Android 自带）
JSONObject obj = new JSONObject(html);
JSONArray arr = obj.getJSONArray("key");
String name = obj.optString("name");

// com.github.catvod.utils.Json（框架工具）
// bean 的 objectFrom / arrayFrom 可以快速解析
```

**解析 HTML**：框架依赖 jsoup（`implementation libs.jsoup`）
```java
Document doc = Jsoup.parse(html);
Elements items = doc.select(".stui-vodlist__box a");
for (Element e : items) {
    String title = e.attr("title");
    String href = e.attr("href");
    String pic = e.attr("data-original");
}
```

---

## 六、写爬虫的套路（5 步）

1. **看站点**：浏览器打开，找分类 URL、列表 URL、详情 URL、播放页 URL 规律
2. **建类**：复制 Demo.java → 改名 `Libvio.java` → 删掉不需要的功能
3. **写 init**：保存站点域名等常量
4. **写五大方法**：
   - homeContent → 返回分类（硬编码或请求）
   - categoryContent → 请求列表页 → jsoup 解析 → Result.page
   - searchContent → 请求搜索 → 解析 → Result.page
   - detailContent → 请求详情页 → 解析 vod_play_from/vod_play_url
   - playerContent → 根据自定义 ID 请求播放页 → 解析真实地址
5. **编译测试**：`gradlew.bat spiderJar` → 推送到模拟器 → OK影视 测试

---

## 七、配置格式（json）

```json
{
  "spider": "./jar/custom_spider.jar",
  "sites": [
    {
      "key": "libvio",
      "name": "立播",
      "type": 3,
      "api": "csp_Libvio",
      "searchable": 1,
      "quickSearch": 1,
      "changeable": 1,
      "ext": "配置参数"
    }
  ]
}
```

- `type: 3` = jar 爬虫
- `api: csp_Libvio` = 加载 jar 里的 Libvio 类
- `ext` = 传给 init 的 extend 参数（可以是字符串或 JSON 对象）

---

## 八、LIBVIO 站点结构（已摸清）

- 主站：`https://libvio.pw`
- 分类：`/type/{id}.html`（1=电影 2=剧集 3=综艺 4=番剧），翻页 `/type/{id}-{page}.html`
- 列表：`/show/{cid}-----------{page}.html`（11 个横线）
- 详情：`/detail/{id}.html`
- 播放页：`/w/{id}-{线路}-{集数}.html`
- 搜索：`/search/-------------.html?wd=关键词`
- 列表项：`.stui-vodlist__box` 里的 `<a>` 标签（title/data-original/href）
- 播放地址：播放页 HTML 里 `player_aaaa={json}</script>` 的 `obj.url`（MP4 直链）
- **反爬**：非浏览器请求返回 403 `browser verification required` → 需要 jar 爬虫模拟浏览器

**饭太硬的方案**（fty/api.json）：
```json
{"key":"立播","name":"🌟立播┃秒播","type":3,"api":"csp_LibvioGuard","timeout":10,"searchable":1,"quickSearch":1,"changeable":1}
```
全局 `"spider":"./jar/spider.jar"` — csp_LibvioGuard 编译在 fty 的 jar 里（已加固加密，反编译不了，但证明思路可行）

---

## 九、重要经验

1. **"无数据,防无限请求"** = drpy2 请求失败时的占位返回（图片是 dr_py 的 404.jpg）→ 不是网站返回的，是规则端失败
2. **网站能打开 ≠ 没反爬**：LIBVIO 只拦"非浏览器请求"，浏览器打开正常，代码请求 403
3. **jar 加固**：饭太硬/肥猫的 jar 用 classes.dex + .so 加固，反编译不出来 → 我们自己的 jar 可以不加固，方便维护
4. **框架自带 catvod-spider 技能**（`.agents/skills/catvod-spider/SKILL.md`）→ 写爬虫时照着它做

---

## 十、下一步

- [ ] 安装 JDK 17（清华镜像下载中）
- [ ] 编写 `Libvio.java`（继承 Spider，实现五大方法）
- [ ] `gradlew.bat spiderJar` 编译
- [ ] 推送 jar 到模拟器 OK影视 测试
- [ ] 成功后推广到其他站点（大米星球等）

---

## 十一、真狼影视（zlys9.top）逆向实战记录（2026-10-11，已弃用但技术全保留）

### 站点特征（Next.js RSC + 加密 API）
- 握手：`GET /api/crypto/handshake` → `{"data":{"token","key(base64 AES-256)"}}`，token 每次变、约 1h 有效
- 加密请求带 `X-Enc-Token` 头；响应 `enc:"1"` 时 data 为 base64：**iv=前12字节、tag=12-28、ct=28起**；Android 用 `cipher.doFinal(ct||tag)`，Python 用 `AESGCM(key).decrypt(ct, tag, iv)`
- **解密后必须再剥内层 `{"errno":0,"data":{...}}` 的 data**（只剥外层会导致搜索空/无线路/播放失败）
- 详情 `/api/detail?cat={数字}&id={vid}&site={源}`；解析 `/api/resolve?url={编码}` → m3u8 直链；搜索 `/api/search?q=&page=&size=36`
- 播放源 20 个：qiyi/youku/qq/mgtv/imgo/bilibili/bilibili1/douyin/leshi/le/levp/sohu/pptv/cntv/xigua/wasu/huashu/m1905/hanju/renren
- **分类首页无服务端分页**（?page= 无效），但 `/category/{cat}/filter?[type=|area=]&page=N` 每页 36 条可翻页；RSC 条目 `{"href":"/detail/{path}/{id}","title","cover","cat":数字}`
- cat 数字：movie=1、tv=2、variety=3、anime=4、children=4；筛选参数 type/area 的 74 个组合全部有效且可翻页

### 源分布实测（关键教训）
- 《醒来》**仅爱奇艺(qiyi)** 有源；《早春晴朗》**仅优酷(youku)** 有源 → 详情必须**先单查爱奇艺、再单查优酷，有货立即返回**；不能等并发全部查完（FongMi 等待窗口短，会先显示"暂无线路"再慢出）

### 坑（必记，通用价值）
1. **运营商 DNS 污染**（时好时坏，解析成 0.0.0.0/无法解析）→ jar 用**自定义 OkHttp Dns 把域名解析到服务器 IP，URL 保持域名**（SNI 正确，等效 curl --resolve）。**直接用 IP 当 URL 会被边缘节点拒**（TLS SNI=IP 不匹配）
2. **R8 混淆（minifyEnabled=true）产物经 apktool 合并 + 并发执行 = SIGSEGV 闪退**（混淆方法 Zlys.e 在并发线程崩溃）→ 必须 `minifyEnabled=false` 重编译；verifySpiderJar 校验脚本与无混淆不兼容，用 `gradlew generateSpiderJar` 跳过
3. **Java 8 lambda 经 apktool 合并可能出问题 → 用匿名类（new Runnable(){...}）最稳**
4. **OkHttp 对真狼服务器 keep-alive 复用连接会挂起超时** → `connectionPool(new ConnectionPool(0,1,MILLISECONDS))` 每次请求新连接（curl 每次新连接 0.8s 正常）
5. token 缓存：握手一次 1h 有效，解密失败时重新握手重试

### 结论
真狼源分布极分散（新剧常只有单一源）、服务器响应慢、模拟器体验差（先暂无后出线路），已按用户决定放弃该站。**逆向→解密→RSC翻页→多源查线路→IP直连绕DNS→无混淆编译的完整链路已打通**，可整体复用于其他站点。

---

## 十二、茶杯狐（cupfoxyy.com）攻克实录（2026-10-12，成功上线）

### 站点结构（苹果CMS 静态 HTML）
- 主域：`https://www.cupfoxyy.com`；播放源服务器 `https://svip.high22-playback.com/`
- 镜像（已写进爬虫容错，请求失败自动切换）：`www.1pdb.com / www.irrmj.cc / www.zldianti.com / www.bahet.com.cn`
- 分类：`/vod/{1..4}.html`（1电影 2电视剧 3综艺 4动漫）
- 列表条目：`<a href="/detail/{id}.html">` + `<img src>` + `<div class="title">片名</div>`
- 详情：`/detail/{id}.html`（h1标题、"导演:</div>…"、"主演:</div>…"、"简介:</div>…<p>正文</p>"、线路nav `#playlist1~4`）
- 播放页：`/play/{id}-{线路}-{集数}.html`，HTML 内嵌 JSON `{"url":"https:\/\/svip.high22-playback.com\/…\/index.m3u8"}`
- 搜索：`/vodsearch/wd/{关键词}.html`
- **大分类 /vod/N.html 无分页**；**子分类页 /vodshow/id/{N}/page/{M}.html 有真实分页**（每页24条，详见第十三章）→ categoryContent 用 Result.page 返回子分类真实分页

### 爬虫设计要点
- Cupfox.java 继承 Spider，解析全用字符串定位（indexOf/substring）或正则，稳过静态 HTML
- 播放地址：从播放页 HTML 抓 `{"url":"..."}` 的 JSON，取 m3u8 直链，`playerContent` 直接返回 `Result.get().url()`
- 多线路：详情页有 4 个线路 nav，`vod_play_from` 用 `$$$` 拼线路名，每线路集数 `#` 分隔

### 关键坑（今天最值钱的经验，写 jar 源必看）
1. **gradle `spiderJar` 产物是"单 dex"**：`decodeSpiderJar` 用了 `--only-main-classes`，只提取主 classes.dex 的类（爬虫 + js 包），**不含 api 层**（`spider.Init`/`bean.Class`/`crawler.Spider` 等）→ OK影视 报 `ClassNotFoundException: com.github.catvod.spider.Init`，表现就是"空的、圈圈都不转"。
2. **手动往 jar 里塞 dex 会坏**：用 .NET ZipArchive Update 模式加 classes2.dex → dex2oat 报 `Failed to extract classes.dex: Inconsistent information`（zip 结构非标准），还是加载不了。
3. **正解 = apktool 合并法（复刻"已验证成功的 jar"的打包路径）**：
   - 用之前**用户测试通过的旧 jar**（如 custom_spider_feikuai.jar 193KB）`apktool d` 解包 → 得到 `smali`（爬虫层）+ `smali_classes2`（api 层，minSdk 23）
   - 把新编译的爬虫 smali（`build/spiderJar/decoded/smali/com/github/catvod/spider/` 里的 Cupfox.smali 等，**含所有爬虫**)覆盖进解包目录的 `smali/com/github/catvod/spider/`
   - `apktool b 解包目录 -o custom_spider.jar` → 标准产物（双 dex：爬虫层 + api 层，minSdk 23）
   - 产物 209KB，OK影视 直接加载成功
4. **gradle 产物 vs apktool 合并产物的差异**：gradle 产物的 `apktool.yml` 是 `sdkInfo: null`（`--api-level` 参数没写进去）；合并产物是 `minSdkVersion: 23` 同旧 jar → dex2oat 正常。
5. **经验总结**：以后新增站点，**不要直接上线 gradle 的 spiderJar 产物**；把新爬虫 smali 合并进"已验证 jar 的解包目录"重新打包最稳。已整理的 base 解包目录：`D:\tvbox\merge_feikuai_v2\decoded_base`。

### 验证与上线（全流程）
- 类检查：`build-tools\dexdump.exe` 查 `Class descriptor: 'Lcom/github/catvod/spider/Cupfox;'`（爬虫层）、`crawler/Spider`（api 层）
- OK影视 文件夹导入 `cupfox.json`（spider=`clan://Download/custom_spider.jar`）→ 分类/列表/详情/播放全通过
- 上线：新 jar（209154B，md5 `edc3cef004f5d971428af332d98d5a1c`）替换 `_edgeone_deploy/gqc_feikuai.jar`；b.json 加站点 `{"key":"Cupfox","name":"茶杯狐[自写jar]","type":3,"api":"csp_Cupfox",...}` 并更新 spider 的 md5 → git 推送 GitHub → Cloudflare Pages 自动部署
- 线上验证：`https://tvbox-bh1.pages.dev/b.json`

### 收获
茶杯狐 = **第一个"静态 HTML 苹果CMS"自研 jar 源完整打通**：无分页、多线路、内嵌 JSON 播放地址、镜像容错。打包链路（apktool 合并法）已固化，后续新站照此流程批量复制即可。

---

## 十三、茶杯狐翻页修复实录（2026-10-12，v2/v3，成功）

### 翻页真相：子分类页才有真实分页
- 大分类 `/vod/{1..4}.html`（电影/电视剧/综艺/动漫）：**无分页**，`/vod/1-2.html`、`/vod/1-3.html` 返回内容与第 1 页**完全相同**（236 条），页面无"下一页"导航 → 任何解析器都只能单页
- **子分类页 `/vodshow/id/{N}.html`：有真实分页** `/vodshow/id/{N}/page/{M}.html`，每页 24 条，实测 p1/p2/p3 的 `/detail/xxx.html` 链接完全不同
- 分页导航：`<div class="pages-box">` 里 `<a class="page" href=".../page/2.html">2</a>` 数字链接，取最大页码即总页数

### 27 个子分类 id 表
- 电影：6动作片 7喜剧片 8爱情片 9科幻片 10恐怖片 11剧情片 12战争片 31记录片 32动画片
- 电视剧：13国产剧 14港剧 15日剧 16韩剧 29欧美剧 30泰剧 33台湾剧 34海外剧 36预告片
- 综艺：20大陆综艺 21日韩综艺 22港台综艺 23欧美综艺
- 动漫：24国产动漫 25日韩动漫 26欧美动漫 27海外动漫 35港台动漫
- 首页 nav 还有地区/年份筛选（`/vodshow/area/{地区}/id/{N}.html`、`/vodshow/id/{N}/year/{年}.html`）——未采用，仅记录

### 列表解析必须限定容器（新坑）
页面顶部有"推荐区"（也含 `/detail/` 链接 + `class="title"`），全页正则会把推荐区混进列表（实测一页抓到 59 条，而真实列表只有 24 条）。
**正解**：先 `html.indexOf("myui-vodbox-content")` 截取列表容器之后的子串再解析 → 每页正好 24 条、无推荐区干扰。

### 分页总页数解析的坑（本次翻页失败的根因）
pages-box 导航 HTML 是 **`class="page"` 写在 `href` 前面**：
```html
<div><a class="page active" href="/vodshow/id/6/page/1.html">1</a></div>
<div><a class="page" href="/vodshow/id/6/page/2.html">2</a></div>
```
正则若按 `href="..." class="page">N</a>`（class 在后）写 → **一个都匹配不到 → pagecount=1 → OK影视 认为只有 1 页 → 不能翻页**（列表只有 24 条、无"下一页"）。
**正解**：不依赖属性顺序，写成 `/vodshow/id/\d+/page/(\d+)\.html"[^>]*>(\d+)</a>`，取最大 M 为总页数。

### OK影视 jar 加载机制坑（v2 失败根因）
- 配置 json 的 `"spider": "clan://Download/custom_spider.jar"` 指定 jar **文件名**，OK影视 从该路径加载
- 推送新 jar 时**必须覆盖配置引用的那个文件名**（本例 custom_spider.jar），否则 OK影视 还在用旧 jar → 分类没变化
- 改完 jar 后要重启 OK影视（或重新加载配置）才生效

### 最终产物（v3 翻页版）
- 209,782B，md5 `DF3E77C64BCFA295347F782B047AB742`
- 上线步骤同前：替换 `_edgeone_deploy/gqc_feikuai.jar` → b.json 更新 md5 → git push → Cloudflare 自动部署

### 经验
"不能翻页"先分清楚是**网站没分页**还是**解析器没把分页信息带出来**：网站没分页就去找子分类/筛选接口（大类没有就挖子分类）；有分页就重点检查两处——`Result.page` 的 pagecount 是否解析正确（正则别写死属性顺序）、jar 是否真的被替换加载（文件名要匹配配置）。



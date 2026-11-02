# TVBox 全源自动更新保障排障笔记（GitHub + 本地双端）

> 写给以后接手的 AI/新手：按步骤照做就能复现，看懂每个坑为什么会发生。
> 环境：Windows + PowerShell 7 + i7-3770，仓库 = ZHOUYU86/tvbox-sources（GitHub 公开），
> 线上入口 = https://zhouyu86.de5.net/b.json 与 https://zhouyu86-bh1.pages.dev/b.json

---

## 一、整体架构（先看懂，再动手）

```
┌─────────────────────────────────────────────────────────────┐
│ GitHub 仓库 ZHOUYU86/tvbox-sources（云端，自动更新主力）     │
│  ├─ .github/workflows/  共 7 个定时任务（Actions）           │
│  │   ├─ sync-legacy-sources.yml  每天 01:30/13:30（北京）     │
│  │   │   └─ scripts/sync_legacy.py 同步 15 个老源            │
│  │   ├─ pg_aowu_sync.yml   每天 02:00/14:00 同步 pg/aowu     │
│  │   ├─ wmz_sync.yml       每天 03:00/15:00 同步 wmz          │
│  │   ├─ zhenxin_sync.yml   每天 01:00/13:00 同步 zhenxin      │
│  │   ├─ live_tv.yml        每天 02:20 同步直播源             │
│  │   ├─ sync-adult-sources.yml 每天 00:00 同步成人源           │
│  │   └─ health_check.yml   每天 04:00 全量体检+自动修复       │
│  └─ Cloudflare Pages / CL 自动部署 -> 线上 b.json            │
└─────────────────────────────────────────────────────────────┘
          ↑ push 触发部署
┌─────────────────────────────────────────────────────────────┐
│ 本地 D:\tvbox（Windows 计划任务，双保险）                     │
│  ├─ update_all.ps1        主控（单实例锁 + 四级回滚）        │
│  ├─ update_{fty,wex,nf,...}.ps1  10 个子脚本                  │
│  ├─ lib_download.ps1       公共下载库（多代理自动切换）      │
│  └─ 计划任务 TVBox Auto Update  每天 02:00                   │
└─────────────────────────────────────────────────────────────┘
```

**关键认知**：
- GitHub 云端 Actions 是**主力**，本地计划任务是**双保险**。两边互不依赖。
- Actions 服务器在海外，**直连 github.com 不需要代理**；本地在国内，**必须走 gh-proxy 镜像**。
- 本地 D:\tvbox **不是 git 仓库**，真正的 git 仓库副本在 `D:\tvbox\_git_work\tvbox-sources`。

---

## 二、本次修了什么（三大根因）

### 根因 1：gh-proxy.com 单代理，一挂全挂
**现象**：日志里反复出现 `未能解析此远程名称: 'gh-proxy.com'`，波及 xs/fty/cl/ouyang/dl/lubin/nf/tvurl/zhenxin 等 9 个源。
**根因**：所有子脚本都写死 `$zipUrl = "https://gh-proxy.com/https://github.com/..."`，这个免费代理在 10-27~11-01 连续 4 天 DNS 解析失败。
**修复**：新建 `D:\tvbox\lib_download.ps1`，实现多代理自动切换：
```powershell
# 代理优先级（按实测可用性排序）
$script:GHProxies = @(
    "https://gh-proxy.com",
    "https://ghproxy.net",
    "https://gh-proxy.net"
)
# 最后直连 github.com 兜底（国内可能慢但不是不可能）
```
所有 ZIP 类脚本（xs/cl/ouyang/lubin/dl）改用 `Invoke-SafeZip <原始GitHubURL> <输出路径> <最小MB>`。
所有 raw 类脚本（fty/nf/tvurl）改用 `Get-GHUrls` 生成候选列表 + `Invoke-SafeDownload`。

### 根因 2：双触发并发冲突
**现象**：日志里同一秒多次 `START`，xs_repo.zip 报"正由另一进程使用"。
**根因**：
- 计划任务 `TVBox Auto Update` 每天 02:00 跑 update_all.ps1
- 登录触发任务 `TVBox8080自启` 跑 start_tvbox.ps1，内含"当天未成功就再跑一次 update_all"逻辑
- 两个入口同时跑，互相抢 zip 文件、互相覆盖 tmp_backup。
**修复**：update_all.ps1 开头加单实例锁：
```powershell
$lockFile = Join-Path $BASE "update.lock"
if (Test-Path $lockFile) {
    $lockPid = [int](Get-Content $lockFile -Raw).Trim()
    if (Get-Process -Id $lockPid -ErrorAction SilentlyContinue) { exit 0 }  # 已有实例在跑，本次跳过
    else { Remove-Item $lockFile -Force }  # 锁残留但进程已死，接管
}
$PID | Out-File $lockFile
# ... 跑完后 ...
Remove-Item $lockFile -Force
```

### 根因 3：fty 脚本"先删后下"，失败留空目录
**现象**：日志反复 `api.json: missing`，fty 目录下空无一物。
**根因**：update_fty.ps1 原来 L17-22 一上来就 `Remove-Item $jarDir -Recurse` + `Remove-Item $apiPath`，然后才下载；任何一步失败，目录就空了。
**修复**：改成"临时区下载 → 全部成功才原子替换"：
```
fty_staging/  ← 新方案：先全量下载到这里
  ├─ api.json   （多代理下载）
  ├─ jar/*.jar （逐个多代理下载）
  └─ FTY/*.js  （逐个多代理下载）
校验：api.json 必须成功 + jar 至少 1 个成功
  ↓ 全部通过才：
Move-Item fty fty_old_backup
Move-Item fty_staging fty
Remove-Item fty_old_backup
```

---

## 三、本次同步修的 GitHub 侧问题

### zhenxin_sync.yml "先删后下"缺陷
原脚本 L18-23：
```yaml
rm -rf zhenxin    # ← 一上来就删
curl -o /tmp/zhenxin.zip "https://gh-proxy.com/..."  # ← 用代理
unzip ...
mv /tmp/zhenxin_x/*/zhenxin zhenxin
```
两个坑：① 下载失败 zhenxin 就被删空；② Actions 服务器不需要 gh-proxy。

**修复后**（D:\tvbox\_git_work\tvbox-sources\.github\workflows\zhenxin_sync.yml）：
```bash
# 直连 github.com，不绕代理
curl -L --max-time 300 -o /tmp/zhenxin.zip \
  "https://github.com/DodgeZhang/tvbox/archive/refs/heads/main.zip"
# 校验 zip 至少 1MB，否则保留现有 zhenxin/
if [ "$(stat -c%s /tmp/zhenxin.zip)" -lt 1000000 ]; then
  echo "下载失败，保留现有 zhenxin/"
  exit 1
fi
# 校验解压后有 zhenxin/ 目录
if [ ! -d /tmp/zhenxin_x/*/zhenxin ]; then
  echo "上游结构变了，保留现有 zhenxin/"
  exit 1
fi
# 全部通过才替换
rm -rf zhenxin
mv /tmp/zhenxin_x/*/zhenxin zhenxin
```

---

## 四、验证结果（2026-11-02 19:00）

### 本地 10 源健康检查
| 源 | api.json 大小 | jar 数 | 总 jar 大小 | 状态 |
|---|---|---|---|---|
| fty | 17,628 B | 7 | 7.9 MB | ✅ |
| wex | 34,495 B | 1 | 1.0 MB | ✅ |
| nf | 66,665 B | 2 | 6.8 MB | ✅ |
| feimao | 18,419 B | 1 | 1.0 MB | ✅ |
| cl | 31,149 B | 23 | 43 MB | ✅ |
| ouyang | 41,182 B | 12 | 7.7 MB | ✅ |
| lubin | 32,306 B | 1 | 2.0 MB | ✅ |
| dl | 54,884 B | 1 | 1.1 MB | ✅ |
| tvurl | 23,882 B | 8 | 19.9 MB | ✅ |
| xs | 27,373 B | 1 | 1.8 MB | ✅ |

**结论：10/10 全部健康，api.json 与 jar 均在位。**

### GitHub 云端提交记录（证明 Actions 在跑）
- 2026-11-02 09:38  auto update live tv sources 2026-11-02
- 2026-11-02 08:54  sync pg/aowu content 202611020854
- 2026-11-02 07:59  sync legacy sources 202611020759
- 2026-11-02 07:21  sync zhenxin (DodgeZhang/tvbox) 202611020721
- 2026-11-01 全天 6 次自动提交全部成功

### 线上 b.json 体检（49 个源）
- 30 个 JSON 接口源：29 个 OK
- **唯一异常**：`豆瓣资源3`（https://caiji.dbzy5.com/...）DNS 解析失败，上游域名已死
- 对照：`豆瓣资源2`（https://dbzy.tv/...）正常，两者是同站不同域名，资源3 可从 b.json 里删掉或换 dbzy.tv
- 15 个 csp jar 爬虫源：需在 TVBox 客户端实测，服务器端只验证 jar 可下载

---

## 五、以后怎么手动触发一次全量更新

```powershell
# 1. 先杀残留进程（防止并发）
Get-CimInstance Win32_Process -Filter "Name='powershell.exe'" |
  Where-Object { $_.CommandLine -match 'update_all|update_' } |
  ForEach-Object { Stop-Process -Id $_.ProcessId -Force }

# 2. 清理锁文件（如果残留）
Remove-Item 'D:\tvbox\update.lock' -Force -ErrorAction SilentlyContinue

# 3. 跑全量更新
powershell.exe -ExecutionPolicy Bypass -File D:\tvbox\update_all.ps1

# 4. 看日志
Get-Content D:\tvbox\update_log.txt -Tail 30
```

---

## 六、以后怎么看 GitHub Actions 是否在跑

不需要 token，直接看提交历史：
```
https://github.com/ZHOUYU86/tvbox-sources/commits/main
```
每次自动更新会留下 `sync xxx content YYYYMMDDHHMM` 格式的提交。
- 每天至少 6 次自动提交 = 正常
- 超过 24 小时没新提交 = 某工作流挂了，去 Actions 页面看红叉

---

## 七、踩坑记录（现象 → 根因 → 修复）

| 现象 | 根因 | 修复 |
|---|---|---|
| xs_repo.zip "正由另一进程使用" | 计划任务 + 登录任务双触发并发 | update_all.ps1 加单实例锁 update.lock |
| 所有 gh-proxy.com 源同时失败 | gh-proxy.com DNS 连续挂 4 天 | lib_download.ps1 多代理自动切换 |
| fty api.json 突然 missing | update_fty.ps1 先删后下，下载失败留空 | 改成 staging 临时区，全部成功才替换 |
| GitHub Actions zhenxin 更新后目录空 | zhenxin_sync.yml 先 rm -rf 再下载 | 改成直连 + 1MB 校验 + 结构校验 |
| 线上 b.json 豆瓣资源3 打不开 | caiji.dbzy5.com 域名已死 | 待用户确认：从 b.json 删除或换 dbzy.tv |
| 本地 git push 401 Unauthorized | remote 内嵌 token 过期 | 本地更新不需要 push；GitHub 侧 Actions 用自己的 GITHUB_TOKEN，不受影响 |

---

## 八、还没做、需要用户拍板的事

1. **豆瓣资源3（caiji.dbzy5.com）已死**：要从 b.json 删掉，还是把 api 换成 https://dbzy.tv/...（豆瓣资源2 已覆盖）？
2. **本地 git 仓库 `D:\tvbox\_git_work\tvbox-sources` 有 15 项未提交改动**（b.json M、pg_aowu_sync.yml M、fty.json 0B、tools/ 临时文件等），本次我改的是 `D:\tvbox\update_*.ps1`（本地脚本）和 `D:\tvbox\_git_work\tvbox-sources\.github\workflows\zhenxin_sync.yml`（GitHub 工作流）。zhenxin_sync.yml 的改动要 push 上去才生效——**这一步需要用户确认**（push 到 GitHub 是写操作）。
3. **15 个 csp jar 爬虫源**（瓜子/咕噜/低端/共青春/飞快/茶杯狐/555/大米/千千/厂长/可可/饭搭子/兔小贝）需要在 TVBox 客户端（雷电模拟器）逐个实测才能确认可用，服务器端体检不到爬虫逻辑。

---

**笔记写完时间**：2026-11-02 19:05
**适用版本**：PowerShell 7 + GitHub Actions Ubuntu latest
**下次维护时**：先看本笔记第二节"三大根因"是否仍存在，再看 update_log.txt 最近 50 行，最后跑一次手动全量更新验证。

# TVBox 15个主配置完整修复清单
# 制作日期：2026-10-29
# 用途：配置坏了直接打开对应的线上地址检查，然后去对应上游拉最新文件替换

| 序号 | 配置名称（OK影视里显示的名字） | 你平时填的线上访问地址（直接复制用） | 上游同步来源 | 自动同步状态 |
|------|--------------------------------|--------------------------------------|--------------|--------------|
| 1 | 主接口b（瓜子/稀饭/大师兄） | https://zhouyu86-bh1.pages.dev/b.json | 自己定制修改，不自动同步上游 | ✅ 手动维护 |
| 2 | 王二小(wex_api) | https://zhouyu86-bh1.pages.dev/wex_api.json | https://9280.kstore.vip/newwex.json | ✅ 自动同步 |
| 3 | 饭太硬 | https://zhouyu86-bh1.pages.dev/lubin/tvbox/饭太硬.json | https://github.com/fantaiying7/EXT | ✅ 自动同步 |
| 4 | 嗷呜 | https://zhouyu86-bh1.pages.dev/aowu/aowu.json | https://9763.kstore.vip/aowu.json | ✅ 自动同步 |
| 5 | 摸鱼 | https://zhouyu86-bh1.pages.dev/lubin/tvbox/摸鱼.json | https://github.com/lubin776/tvbox-api-backup | ✅ 自动同步 |
| 6 | 肥猫 | https://zhouyu86-bh1.pages.dev/ouyang/tvbox/FM/肥猫/肥猫.json | http://xn--z7x900a.net/tv | ✅ 自动同步 |
| 7 | tvbox18 | https://zhouyu86-bh1.pages.dev/tvbox18.json | https://jihulab.com/tvbox18/tvbox18 | ✅ 已修复BOM |
| 8 | XBPQ | https://zhouyu86-bh1.pages.dev/ouyang/tvbox/gao/XBPQ.json | https://github.com/adminouyang/231006 | ✅ 自动同步 |
| 9 | 真心(zhenxin) | https://zhouyu86-bh1.pages.dev/zhenxin/FongMi.json | https://github.com/DodgeZhang/tvbox | ✅ 自动同步 |
| 10 | fty.json | https://zhouyu86-bh1.pages.dev/fty.json | https://github.com/mrgaoshuiquan/tvbox-config | ✅ 自动同步 |
| 11 | CL主配置 | https://zhouyu86-bh1.pages.dev/cl/cl.json | https://github.com/cluntop/tvbox | ✅ 自动同步 |
| 12 | gua.json | https://zhouyu86-bh1.pages.dev/gua.json | 自己维护的单源配置 | ✅ 手动 |
| 13 | PG接口 | https://zhouyu86-bh1.pages.dev/pg/pg.json | https://www.252035.xyz/p/jsm.json | ✅ 自动同步 |
| 14 | WMZ接口 | https://zhouyu86-bh1.pages.dev/wmz/wmz.json | https://8815.kstore.vip/tvbox/wmz | ✅ 自动同步 |
| 15 | 潇洒(xs) | https://zhouyu86-bh1.pages.dev/xs/xs.json | https://github.com/qist/tvbox | ✅ 自动同步 |

---
## 重要注意事项：
1.  所有文件绝对不能用JSON格式化工具重新排版！会导致OK影视解析失败，直接从上游原文件复制覆盖即可
2.  tvbox18和wex_api之前的UTF-8 BOM头问题已经修复，拉新文件后要检查开头第一个字符是不是`{`，不能有乱码
3.  XBPQ开头的//注释行是TVBox原生支持的，不要删掉
4.  摸鱼、王二小里面很多小源点不开，是第三方采集站自己服务器挂了，属于全TVBox用户都会遇到的正常情况，不是我们配置损坏
5.  托管域名备用：https://zhouyu365666.top + 上面的路径（比如王二小就是 https://zhouyu365666.top/wex_api.json）

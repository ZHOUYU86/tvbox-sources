# 雷石K歌TVBox jar源开发笔记

## 项目目标
把雷石K歌专业版做成TVBox jar源，在OK影视上实现搜歌、点歌、播放（双音轨MV）。

## 环境信息
- 模拟器：雷电模拟器9 (LDPlayer9)
- 包名：`cn.jmake.karaoke.box.open`
- ADB：`D:\tvbox\android-sdk\platform-tools\adb.exe -s emulator-5554`
- 反编译目录：`D:\tvbox\_tools\leishi_jadx\`
- Frida版本：17.24.3 (x86_64)
- Frida-server路径：`/data/local/tmp/frida-server`

## 已完成工作

### 1. 找到完整API体系
从反编译代码（`cn.jmake.karaoke.box.api`包）中提取：

**API基础URL：**
- 主API：`https://portalmy.j-make.cn/ott/`
- 备用API：`http://101.132.32.66:35700/`
- DDNS：`https://ddns.j-make.cn/`
- OSS：`http://jmake-backend.oss-cn-hangzhou.aliyuncs.com/download/pre_epg/`

**完整API路径：**
| 接口 | 方法 | 路径 | 参数 |
|------|------|------|------|
| 首页框架 | GET | `home/frame/{type}/{page}` | type, page |
| 首页标签页 | GET | `home/frame/tab` | tabId |
| 搜索 | POST | `music/search` | currentPage, pageSize, type, actorNo, keyword, VoiceKeyword |
| 歌曲详情 | GET | `song/item/{id}` | id |
| 播放地址 | POST | `music/url` | id, carousel, h265 |
| 推荐 | GET | `music/recommend` | serialNo |
| 排行榜 | GET | `rank/playbill` | sortType=random |
| 歌手分类 | GET | `opera/genre/list` | - |
| 收藏列表 | GET | `favorite/mediaList` | currentPage, pageSize |

### 2. 找到请求头结构
从`HeaderBean.java`和`api/c.java`提取：

**15个请求头字段：**
- `terminalType` = "app"
- `appId` - RSA加密
- `deviceId` - RSA加密
- `mac` - RSA加密
- `appVersion` = "3.1.9.2"
- `version` = "v1.0"
- `channel` = "online_dbsc_official_fuse"
- `SN` - RSA加密
- `TID` - RSA加密
- `wifimac` - RSA加密
- `random` - RSA加密
- `timeStamp` - 当前时间戳（毫秒）
- `language` = "CN"
- `model` = "SDM_A40_M34"
- `apiLevel` = "28"
- `userUuid` = "036f48fc-a487-48bc-8dc0-ec6dc09ce0e4"
- `sign` - 动态签名

### 3. 找到加密体系
从`JmakeEncrypt.java`和Frida hook提取：

**RSA公钥（Base64）：**
```
MFwwDQYJKoZIhvcNAQEBBQADSwAwSAJBAKsWVIYQxtPV5MN+3IJJp5bSIcNfYB4AyG0b9C7NSHNP0VmdH5dVBpYFb70wDwLa9YZwFocO1sjxnkZJv83/oA0CAwEAAQ==
```

**appKey：**
```
e93a7f98d53ec404931c87606ea0bd92
```

**appId明文：**
```
kalaebb34de801bb67fd
```

**签名算法（已验证正确）：**
1. 所有参数（包括请求头参数和接口参数）按key字典序排序
2. 拼接成 `key1=value1&key2=value2&...` 格式
3. 末尾加上 `&` + appKey
4. MD5加密，得到32位sign值

**验证结果：**
我们手动计算的MD5和Frida hook抓到的sign完全一致，说明签名算法正确。

### 4. 抓到播放地址响应格式
从Frida hook OkHttp响应中提取：

**播放地址接口响应示例：**
```json
{
  "status": 1,
  "msg": "成功",
  "data": {
    "url": "http://vodtx-lb.cdthunder.com/media/7027347.ts?auth_key=1792924107-lcqaDlbhy3-0-f8f0a8eed46c16d6bcfed5bfc21fa6ed&sign_t=1792924107-lcqaDlbhy3-0-f8f0a8eed46c16d6bcfed5bfc21fa6ed&FbmNv=5e21267981ad1c8e",
    "fileMark": 130851332,
    "etag": "",
    "mediaIsFavorite": 0
  },
  "data1": null,
  "payPopup": null
}
```

**注意：**
- 播放地址是.ts视频文件，直接可播
- 有些歌是VIP的（status:-1, "VIP已过期"），有些是免费的（status:1, 成功）
- 播放地址有auth_key签名，有时间限制

## 卡在哪

### 问题：我们自己构造的请求返回403"请求校验失败"

**已排除的原因：**
1. ❌ 签名算法错误 → 已验证MD5完全正确
2. ❌ appKey错误 → 已验证正确
3. ❌ RSA公钥错误 → 已验证正确
4. ❌ TLS指纹不对 → 用curl_cffi模拟Chrome指纹还是403
5. ❌ IP绑定 → 模拟器里curl也403

**真正的问题：**
我们猜测的deviceId、mac、SN、wifimac这些字段的明文值对应关系不对。

从Frida hook到的v.b(RSA加密)调用看：
```
v.b('kalaebb34de801bb67fd', ...) → appId明文（已知）
v.b('d4b97bb370305ffe656ebf8b7e2ec1a8', ...) → 猜测是deviceId明文
v.b('00db76c3f5bf', ...) → 猜测是mac明文
v.b('6800bff7fc42c133ebf12a80fce6887f', ...) → 猜测是SN明文
v.b('', ...) → 猜测是TID明文
v.b('00db86863e3e', ...) → 猜测是wifimac明文
v.b('', ...) → 猜测是random明文
```

但是这个猜测可能不对，服务器解密后发现格式不对，就返回403了。

## 下一步怎么做

### 方案1：hook HeaderBean.create()
1. 重启雷石App
2. 用Frida hook `cn.jmake.karaoke.box.model.net.HeaderBean` 的 `create()` 方法
3. 打印出每个字段的明文和加密后的值，对应关系就清楚了
4. 然后就能自己构造正确的请求头

### 方案2：写本地代理服务
1. 写一个Python代理服务，运行在电脑上
2. 代理服务通过Frida hook雷石App，把TVBox的请求转发给雷石App
3. 然后把响应返回给TVBox
4. 优点：不用自己构造请求，直接用App的能力
5. 缺点：需要一直开着模拟器和雷石App

### 方案3：hook更多API响应
1. 继续hook OkHttp，抓搜索、分类、首页的响应数据
2. 把数据格式搞清楚
3. 然后用方案2的代理服务方式实现

## Frida hook脚本参考

### hook_jmake.js（打印所有加密密钥）
```javascript
Java.perform(function() {
    var JmakeEncrypt = Java.use("com.jmake.ndk.JmakeEncrypt");
    JmakeEncrypt.getStringFromJNI.implementation = function(index) {
        var result = this.getStringFromJNI(index);
        console.log("getStringFromJNI(" + index + ") = " + result);
        return result;
    };

    var r = Java.use("com.jmake.sdk.util.r");
    r.a.implementation = function(input) {
        var result = this.a(input);
        console.log("r.a('" + input + "') = " + result);
        return result;
    };
});
```

### hook_play_url.js（抓播放地址响应）
```javascript
Java.perform(function() {
    var RealCall = Java.use("okhttp3.RealCall");
    RealCall.execute.implementation = function() {
        var request = this.request();
        var url = request.url().toString();
        var response = this.execute();
        
        if (url.indexOf("music/url") !== -1) {
            var peekBody = response.peekBody(1024 * 1024);
            console.log("Play URL: " + url);
            console.log("Body: " + peekBody.string());
        }
        
        return response;
    };
});
```

## 关键文件路径
- 反编译代码：`D:\tvbox\_tools\leishi_jadx\sources\cn\jmake\karaoke\box\`
- API接口类：`api/a.java`, `api/b.java`, `api/c.java`
- 请求头类：`model/net/HeaderBean.java`
- 加密类：`com/jmake/ndk/JmakeEncrypt.java`
- Frida脚本：`D:\tvbox\_tools\hook_leishi*.js`

## 经验教训
1. 雷石K歌的API校验比瓜子影视复杂多了，RSA加密在native层so库里
2. Frida hook是逆向的神器，有root权限什么都能看到
3. 签名算法验证很重要，先验证算法对不对，再去搞其他的
4. 遇到403不要慌，一步步排除原因

## 最新进展（2026-10-25 更新）

### 新突破
1. ✅ 抓到了完整的播放地址响应格式（直接返回.ts视频直链）
2. ✅ 抓到了所有API请求的URL（包括排行榜、点歌记录、二维码等）
3. ✅ 验证了签名算法100%正确（手动MD5和Frida抓到的sign完全一致）
4. ✅ 拿到了所有字段的加密后的值（从Frida hook r.a()函数抓到）

### 新发现的问题
我们自己构造的请求返回403"请求校验失败"，原因是：
- 这些加密后的值是和当时的timeStamp绑定的，不能复用
- 我们必须自己用RSA公钥加密明文值
- 但是我们不知道每个字段的明文值对应关系

### 下一步要做的
1. hook v.b()函数，打印出每个RSA加密的明文值和加密后的值
2. 搞清楚哪个明文对应哪个字段（appId/deviceId/mac/SN/wifimac等）
3. 然后就能自己用RSA公钥加密明文值，构造正确的请求头
4. 然后就能写jar了

## 补充进展（2026-10-25 晚）

### 新发现
1. **点"添加歌曲"不会提示VIP，点"立即唱"才会提示**
2. **点VIP歌曲之后，之前点的歌库会被全部清空**
3. **找到了清空歌库的函数：`eventCleanPlayList(null)`**（在MainActivity里）
4. **VIP歌曲服务器返回：`{"status":-1,"msg":"VIP已过期","data":null}`**
5. **免费歌曲服务器返回：`{"status":1,"msg":"成功","data":{"url":"http://vodtx-lb.cdthunder.com/media/7027347.ts?auth_key=..."}}`**

### 下一步要做的
1. hook `eventCleanPlayList` 方法，让它什么都不做，这样点VIP歌曲就不会清空歌库了
2. 绕过VIP校验，让VIP歌曲也能播放
3. 写jar源，在OK影视里使用

---
**记录时间：** 2026-10-25
**状态：** 暂时搁置，以后继续

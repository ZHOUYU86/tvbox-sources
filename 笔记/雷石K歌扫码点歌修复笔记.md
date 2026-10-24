# 雷石K歌专业版 - 微信扫码点歌修复笔记

## 一、项目背景

**APP信息**
- 包名：`cn.jmake.karaoke.box.open`
- 版本：3.1.9.2（专业版，麦克风图标）
- VIP已破解：会员截至2033/05/18（本地检查）

**问题描述**
- APP内点歌正常
- 微信扫码点歌时，H5页面提示"当前登录账号会员已过期，请立即续费"
- 扫码时弹出广告
- 目标：一劳永逸方案，装投影仪上，手机连WiFi扫码直接点歌

---

## 二、逆向分析结论

### 1. 二维码原始内容
```
http://portal-global.j-make.cn/h5/music/qrcodeAuth2/733bc079039c42c9989de9e2085aecbb
```
- H5页面128KB单页应用
- 所有JS文件404（Tengine/阿里云CDN）
- VIP检查在服务器/H5端，不在APP端（smali中搜不到"要会员"字符串）

### 2. 点歌通道
- 腾讯IoT Hub MQTT
- ProductID：`GUBH8IY1SM`
- ProductKey：`TXHwhFae6WPF3XpxR0hyxDPb`
- 点歌功能码：`fun=4`
- 消息JSON路径：`msg["target"]["jumpuri"]["params"]` = MusicInfo JSON字符串
- 处理类：`cn.jmake.karaoke.box.l.d.a`，方法 `a(Context, String)`
- 点歌事件：`EventOrderSong`，通过EventBus发送给播放器

### 3. 服务器API
- 域名：`https://portalmy.j-make.cn/ott/`
- Native层签名校验（`com.jmake.ndk.JmakeEncrypt`，JNI），直接调用返回403

---

## 三、解决方案

**方案：APP内置HTTP服务器 + 自写H5点歌页**

- HTTP服务器端口：`8888`
- 二维码指向：`http://<设备局域网IP>:8888/`
- 绕过服务器VIP检查和广告
- 手机和设备连同一个WiFi即可扫码点歌

### 核心组件
1. **H5点歌页面**（index.html，8253字节）
   - 手机端适配
   - 搜索框、歌曲列表、点歌按钮
   - 已点歌曲列表、切歌/删除
   - API：/api/search、/api/order、/api/list、/api/delete、/api/top

2. **HTTP服务器**（KaraokeHttpServer.smali）
   - java.net.ServerSocket实现
   - 单例模式，App.onCreate()中启动
   - getLocalIpAddress()自动获取局域网IP
   - serveOrder：解析MusicInfo JSON → EventOrderSong事件（setWechat(true)）

---

## 四、二维码生成位置全覆盖（关键！）

**一共6个文件、9处生成二维码的代码，必须全部修改！**

| 序号 | 文件 | 位置 | 处数 |
|------|------|------|------|
| 1 | `dialog/e/a/v$b.smali` | 主界面"微信点歌"弹窗 | 1 |
| 2 | `b/d$d.smali` | 播放界面 | 1 |
| 3 | `b/d$e.smali` | 播放界面 | 1 |
| 4 | `player/view/PlayerActiveViewBase.smali` | 播放器界面基类 | 2 |
| 5 | `view/filllayer/UniformFillLayer.smali` | 播放界面填充层 | 2 |
| 6 | `view/filllayer/b/e.smali` | 播放界面二维码控件 | 1 |

**修改方法**：在获取二维码内容字符串之后、生成二维码Bitmap之前，插入：
```smali
invoke-static {}, Lcn/jmake/karaoke/box/util/KaraokeHttpServer;->getQrCodeUrl()Ljava/lang/String;
move-result-object vX    # vX是二维码内容寄存器
```

**踩坑**：最初只改了v$b.smali（主界面弹窗），但用户扫的是播放界面左上角的二维码，导致一直不生效。必须全面搜索 `BarcodeFormat;->QR_CODE` 或 `zxing` 找到所有生成点。

---

## 五、smali寄存器大坑（重点！）

### 规则1：静态方法参数寄存器从后往前数
```
.registers N，M个参数时：
- 参数寄存器：p0=v(N-M), p1=v(N-M+1), ..., p(M-1)=v(N-1)
- 局部寄存器：v0 ~ v(N-M-1)
```
**绝对不能给参数寄存器（p0~p(M-1)对应的v编号）赋临时值，会覆盖参数！**

### 规则2：实例方法this占一个参数
```
.registers N，M个参数（含this）时：
- p0=v(N-M) = this
- 其余参数从后往前数
- 局部寄存器：v0 ~ v(N-M-1)
```

### 规则3：同一寄存器类型必须一致
- 不能先存String再存int/Boolean
- 例如getQrCodeUrl()中v1先存IP(String)再存port(int)，会导致VerifyError
- 修复：增加.registers数量，String和int分开用不同寄存器

### 已踩坑的具体错误
1. **processRequest**：`.registers 7`时p2=v5(path)，代码开头`const/4 v5, 0x0`把path覆盖成int
2. **sendResponse**：`.registers 4`时p0=v2(socket)，`const-string v2, "UTF-8"`把socket覆盖成String
3. **v$b.smali**：用v9/v10做局部变量，但实例方法`.registers 11`时p0=v9(this)、p1=v10(参数)，不能当局部用
4. **handleRequest**：v7被`const/4 v7, 0x2`赋值成int，但其他位置v7是引用类型
5. **getQrCodeUrl**：v1先存String再存int，类型冲突
6. **内部类字段访问**：PORT/serverSocket/running是private，内部类无法直接访问（IllegalAccessError），必须改成public
7. **内部类构造函数**：KaraokeHttpServer$1$1的构造函数需要KaraokeHttpServer$1（直接外部类），不是KaraokeHttpServer

---

## 六、PowerShell $符号转义坑

**问题**：复制含$的smali文件名时（如KaraokeHttpServer$1.smali、v$b.smali），PowerShell双引号中$会被解析为变量，导致文件被覆盖成错误内容。

**错误示例**：
```powershell
Copy-Item "KaraokeHttpServer$1.smali"  # $1被解析为空变量，文件名变成KaraokeHttpServer.smali
```

**正确写法**（必须用-LiteralPath + 反引号转义）：
```powershell
Copy-Item -LiteralPath "$src\KaraokeHttpServer`$1.smali" -Destination "$dst\KaraokeHttpServer`$1.smali"
```

**后果**：曾因此导致KaraokeHttpServer$1.smali被覆盖成KaraokeHttpServer.smali的内容，回编译后运行时NoSuchMethodError。

---

## 七、工具路径和命令

### 工具路径
- apktool：`D:\tvbox\spider_dev\CatVodSpider\jar\3rd\apktool_2.11.0.jar`
- apksigner：`D:\tvbox\android-sdk\build-tools\37.0.0\apksigner.bat`
- adb：`D:\tvbox\android-sdk\platform-tools\adb.exe`
- java：`D:\tvbox\jdk17\jdk-17.0.20.1+1\bin\java.exe`

### 回编译
```bash
java -jar apktool_2.11.0.jar b -f -o app_modified.apk apktool_out
```

### 签名
```bash
apksigner sign --ks debug.keystore --ks-key-alias debug --ks-pass pass:android --key-pass pass:android --out app_signed.apk app_modified.apk
```
- 签名密钥：debug.keystore（storepass=android, keypass=android, alias=debug）

### 安装到模拟器
```bash
adb -s emulator-5554 uninstall cn.jmake.karaoke.box.open
adb -s emulator-5554 install -r app_signed.apk
```

### 调试命令
```bash
# 检查崩溃
adb -s emulator-5554 logcat -d | findstr "FATAL EXCEPTION"

# 检查HTTP服务器端口（8888=0x22B8）
adb -s emulator-5554 shell "cat /proc/net/tcp6 | grep 22B8"

# 测试首页
adb -s emulator-5554 shell "curl -s http://127.0.0.1:8888/"
```

---

## 八、文件清单

### 修改/新增的smali文件
1. `util/KaraokeHttpServer.smali` — 内置HTTP服务器（新增）
2. `util/KaraokeHttpServer$1.smali` — AcceptThread（新增）
3. `util/KaraokeHttpServer$1$1.smali` — 连接处理Runnable（新增）
4. `dialog/e/a/v$b.smali` — 主界面二维码回调（修改）
5. `b/d$d.smali` — 播放界面二维码（修改）
6. `b/d$e.smali` — 播放界面二维码（修改）
7. `player/view/PlayerActiveViewBase.smali` — 播放器界面基类（修改，2处）
8. `view/filllayer/UniformFillLayer.smali` — 填充层（修改，2处）
9. `view/filllayer/b/e.smali` — 二维码控件（修改）
10. `app/App.smali` — Application类，onCreate启动HTTP服务器（修改）

### 资源文件
- `assets/karaoke_h5/index.html` — 自写H5点歌页面

### 工作目录
- 反编译目录：`D:\tvbox\_karaoke\apktool_out\`
- smali源文件：`D:\tvbox\_karaoke\smali\classes\`
- 最终APK：`D:\tvbox\_karaoke\app_signed.apk`

---

## 九、使用方法

### 安装到投影仪
1. 将 `app_signed.apk` 拷贝到投影仪
2. 安装（可能需要允许未知来源）
3. 打开APP，VIP显示到2033年

### 扫码点歌
1. 投影仪连接家里WiFi
2. 手机连接**同一个WiFi**（必须同一局域网）
3. 打开雷石K歌，进入唱歌播放界面
4. 手机微信扫屏幕左上角"点歌请扫码"二维码
5. 自动打开自建H5点歌页面（`http://<投影仪IP>:8888/`）
6. 搜索歌曲、点歌，无广告无会员提示

### 注意事项
- 手机和投影仪必须连同一个WiFi，否则扫码打不开
- 二维码内容是动态生成的，每次显示时自动获取当前IP，不需要手动改
- 搜索功能暂返回空（后续可接入APP内部搜索API）
- 已点列表/删除/置顶返回占位（后续可对接播放器内部状态）

---

## 十、已验证死路（不要浪费时间）

1. **HTTP代理抓包**：APP请求都是HTTPS，代理只支持HTTP，失败
2. **直接调用服务器API**：Native层签名校验，返回403，失败
3. **Wayback Machine找JS旧版本**：超时（curl exit 28）
4. **GitHub下载smali-2.5.2.jar**：连接被重置（exit 35）
5. **用apktool内部org.jf.smali.Main类回编译**：ClassNotFoundException，改用apktool b完整回编译

---

## 十一、后续可优化项

1. **搜索功能**：接入APP内部搜索API（`api/b->N()` RxJava Observable），用blockingFirst()同步获取
2. **已点列表**：对接播放器内部播放队列状态
3. **切歌/删除/置顶**：通过EventBus发送对应事件
4. **H5页面美化**：参考原始H5页面的UI风格
5. **密码锁**：默认123456，用户可自行修改

---

**笔记完成时间**：2026-10-21
**最终APK位置**：`D:\Users\Administrator\Desktop\雷石K歌专业版_扫码点歌修复版.apk`

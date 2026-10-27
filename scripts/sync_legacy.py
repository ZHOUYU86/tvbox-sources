#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""云端老源自动同步（GitHub Actions 运行）。
从各上游直连拉取（Actions 服务器可直连 GitHub），按本地已验证映射写回仓库目录。
每个源独立容错；ouyang 同步后剥 // 注释（防 OK影视闪退）。
用法: python3 scripts/sync_legacy.py
"""
import io, json, os, re, shutil, sys, tempfile, urllib.request, zipfile

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) doubao-sync"}


def dl(url, timeout=120, binary=True):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def dl_text(url, timeout=120):
    return dl(url, timeout).decode("utf-8-sig", errors="replace")


def json_get(url, timeout=60):
    return json.loads(dl(url, timeout).decode("utf-8"))


def unzip_to_mem(data, base_dir, strip_root=False):
    """解压 zip 到 base_dir；strip_root 去掉顶层目录名"""
    tmp = tempfile.mkdtemp(prefix="synczip_")
    try:
        zp = os.path.join(tmp, "a.zip")
        open(zp, "wb").write(data)
        with zipfile.ZipFile(zp) as z:
            names = z.namelist()
            root = None
            if strip_root and names:
                root = names[0].split("/")[0]
            for n in names:
                if n.endswith("/"):
                    continue
                rel = n
                if root and n.startswith(root + "/"):
                    rel = n[len(root) + 1:]
                dst = os.path.join(base_dir, rel)
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                with z.open(n) as f, open(dst, "wb") as out:
                    shutil.copyfileobj(f, out)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def replace_dir(src, dst):
    if os.path.exists(dst):
        shutil.rmtree(dst)
    shutil.copytree(src, dst)


def replace_file(content, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    mode = "wb" if isinstance(content, bytes) else "w"
    with open(path, mode, encoding=None if isinstance(content, bytes) else "utf-8") as f:
        f.write(content)


def find_dir(base, name):
    for root, dirs, files in os.walk(base):
        if os.path.basename(root) == name:
            return root
    return None


def strip_js_comments(text):
    """剥掉 { 之前的 // 注释行（文本级）"""
    return re.sub(r'^\s*//.*$', '', text, flags=re.M)


def sync_xs():
    """小洒: qist/tvbox master.zip → xiaosa 目录 → xs/"""
    data = dl("https://github.com/qist/tvbox/archive/refs/heads/master.zip", 180)
    tmp = tempfile.mkdtemp(prefix="xs_")
    try:
        unzip_to_mem(data, tmp, strip_root=True)
        xiaosa = find_dir(tmp, "xiaosa")
        if not xiaosa:
            raise RuntimeError("xiaosa 目录未找到")
        replace_dir(xiaosa, "xs")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("[xs] OK")


def sync_fty():
    """泛泰信: mrgaoshuiquan/tvbox-config + fantaiying7/EXT"""
    base = "https://raw.githubusercontent.com/mrgaoshuiquan/tvbox-config/main"
    txt = dl_text(base + "/tvbox.json")
    replace_file(txt, "fty/api.json")
    # jar 列表
    jar_list = json_get("https://api.github.com/repos/mrgaoshuiquan/tvbox-config/contents/jar?ref=main")
    os.makedirs("fty/jar", exist_ok=True)
    n = 0
    for f in jar_list:
        if f.get("type") == "file":
            try:
                jd = dl(base + "/jar/" + f["name"], 120)
                replace_file(jd, os.path.join("fty/jar", f["name"]))
                n += 1
            except Exception as e:
                print(f"[fty] jar 下载失败 {f['name']}: {e}")
    # EXT JS
    ext = "https://raw.githubusercontent.com/fantaiying7/EXT/main"
    js_map = {"drpy2.min.js": "drpy2.min.js", "%E5%85%94%E5%B0%8F%E8%B4%9D.js": "兔小贝.js",
              "%E6%96%97%E9%B1%BC%E7%9B%B4%E6%92%AD.js": "斗鱼直播.js", "%E8%99%8E%E7%89%99.js": "虎牙.js"}
    for u, l in js_map.items():
        try:
            jd = dl(ext + "/" + u, 60)
            replace_file(jd, os.path.join("fty/FTY", l))
        except Exception as e:
            print(f"[fty] JS 下载失败 {l}: {e}")
    # spider.jar 到根 + md5 改写
    sp_src = os.path.join("fty/jar", "spider.jar")
    if os.path.exists(sp_src):
        import hashlib
        b = open(sp_src, "rb").read()
        replace_file(b, "fty/spider.jar")
        md5 = hashlib.md5(b).hexdigest()
        txt = txt.replace('"./jar/spider.jar"', '"./spider.jar;md5;' + md5 + '"')
        replace_file(txt, "fty/api.json")
    print(f"[fty] OK (jar={n})")


def sync_wex():
    """王二小: 9280.kstore.vip/newwex.json"""
    txt = None
    for u in ("https://9280.kstore.vip/newwex.json", "https://9280.kstore.vip/wex.json"):
        try:
            txt = dl_text(u)
            break
        except Exception:
            continue
    if txt is None:
        raise RuntimeError("wex 两个地址都失败")
    m = re.search(r'"spider"\s*:\s*"([^"]*)"', txt)
    if m:
        sp = m.group(1)
        url = sp.split(";")[0]
        md5 = sp.split(";", 1)[1] if ";" in sp else ""
        b = dl(url, 120)
        replace_file(b, "wex/spider.jar")
        txt = txt.replace(sp, "./spider.jar;" + md5)
    replace_file(txt, "wex/api.json")
    print("[wex] OK")


def sync_nf():
    """南风: yoursmile66/TVBox main 整仓"""
    tree = json_get("https://api.github.com/repos/yoursmile66/TVBox/git/trees/main?recursive=1")
    files = [x["path"] for x in tree.get("tree", []) if x.get("type") == "blob"]
    base = "https://raw.githubusercontent.com/yoursmile66/TVBox/main"
    os.makedirs("nf", exist_ok=True)
    n = 0
    for f in files:
        try:
            b = dl(base + "/" + f, 60)
            replace_file(b, os.path.join("nf", f))
            n += 1
        except Exception as e:
            print(f"[nf] 失败 {f}: {e}")
    print(f"[nf] OK ({n} files)")


def sync_feimao():
    """肥猫: xn--z7x900a.net/tv"""
    base = "http://xn--z7x900a.net"
    txt = dl_text(base + "/tv")
    m = re.search(r'"spider"\s*:\s*"([^"]*)"', txt)
    if m:
        sp = m.group(1)
        url = sp.split(";")[0]
        md5 = sp.split(";", 1)[1] if ";" in sp else ""
        b = dl(url, 120)
        replace_file(b, "feimao/spider.jar")
        txt = txt.replace(sp, "./spider.jar;" + md5)
    # 引用文件
    refs = set(re.findall(r'\./([^"\' )]+)', txt))
    for ref in refs:
        if ref.startswith("spider.jar") or ref.startswith("#"):
            continue
        try:
            b = dl(base + "/" + ref, 60)
            replace_file(b, os.path.join("feimao", ref))
        except Exception as e:
            print(f"[feimao] 引用文件失败 {ref}: {e}")
    replace_file(txt, "feimao/api.json")
    print("[feimao] OK")


def sync_cl():
    """厂长: cluntop/tvbox main.zip 整仓"""
    data = dl("https://github.com/cluntop/tvbox/archive/refs/heads/main.zip", 240)
    tmp = tempfile.mkdtemp(prefix="cl_")
    try:
        unzip_to_mem(data, tmp, strip_root=True)
        replace_dir(tmp, "cl")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("[cl] OK")


def sync_ouyang():
    """欧阳: adminouyang/231006 main.zip → tvbox/gao/XYQ.json → api.json（剥注释）"""
    data = dl("https://github.com/adminouyang/231006/archive/refs/heads/main.zip", 240)
    tmp = tempfile.mkdtemp(prefix="oy_")
    try:
        unzip_to_mem(data, tmp, strip_root=True)
        gao = os.path.join(tmp, "tvbox", "gao")
        xyq = os.path.join(gao, "XYQ.json")
        if os.path.exists(xyq):
            txt = open(xyq, encoding="utf-8-sig", errors="replace").read()
            txt = strip_js_comments(txt)
            replace_file(txt, "ouyang/api.json")
        else:
            candidates = []
            for root, dirs, files in os.walk(tmp):
                for fn in files:
                    if fn == "api.json":
                        candidates.append(os.path.join(root, fn))
            if candidates:
                candidates.sort(key=lambda p: -os.path.getsize(p))
                txt = open(candidates[0], encoding="utf-8-sig", errors="replace").read()
                txt = strip_js_comments(txt)
                replace_file(txt, "ouyang/api.json")
        # jar
        gao_jar = os.path.join(gao, "jar")
        if os.path.isdir(gao_jar):
            os.makedirs("ouyang/jar", exist_ok=True)
            for fn in os.listdir(gao_jar):
                src = os.path.join(gao_jar, fn)
                if os.path.isfile(src):
                    shutil.copy2(src, os.path.join("ouyang/jar", fn))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("[ouyang] OK")


def sync_lubin():
    """卢宾: lubin776/tvbox-api-backup main.zip + p.jar 外部"""
    data = dl("https://github.com/lubin776/tvbox-api-backup/archive/refs/heads/main.zip", 240)
    tmp = tempfile.mkdtemp(prefix="lb_")
    try:
        unzip_to_mem(data, tmp, strip_root=True)
        x4 = os.path.join(tmp, "tvbox", "X4菠菜pro.json")
        if os.path.exists(x4):
            txt = open(x4, encoding="utf-8-sig", errors="replace").read()
        else:
            cands = []
            for root, dirs, files in os.walk(tmp):
                for fn in files:
                    if fn.endswith(".json") and "菠菜" in fn:
                        cands.append(os.path.join(root, fn))
            if not cands:
                raise RuntimeError("lubin 未找到 X4菠菜pro.json")
            txt = open(cands[0], encoding="utf-8-sig", errors="replace").read()
        b = dl("https://0.12yue.de5.net/5/lib/p.jar", 120)
        replace_file(b, "lubin/p.jar")
        txt = txt.replace("https://0.12yue.de5.net/5/lib/p.jar", "./p.jar")
        replace_file(txt, "lubin/api.json")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("[lubin] OK")


def sync_dl():
    """东篱: chitue/dongliTV main.zip 整仓"""
    data = dl("https://github.com/chitue/dongliTV/archive/refs/heads/main.zip", 240)
    tmp = tempfile.mkdtemp(prefix="dl_")
    try:
        unzip_to_mem(data, tmp, strip_root=True)
        replace_dir(tmp, "dl")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("[dl] OK")


def sync_tvurl():
    """tvurl: ne7359/tvurl main 整仓（0821.json → api.json）"""
    tree = json_get("https://api.github.com/repos/ne7359/tvurl/git/trees/main?recursive=1")
    files = [x["path"] for x in tree.get("tree", []) if x.get("type") == "blob"]
    base = "https://raw.githubusercontent.com/ne7359/tvurl/main"
    os.makedirs("tvurl", exist_ok=True)
    n = 0
    for f in files:
        dst = "api.json" if f == "0821.json" else f
        minsize = 1000000 if f == "jar/fan.txt" else 100
        try:
            b = dl(base + "/" + f, 120)
            if len(b) >= minsize:
                replace_file(b, os.path.join("tvurl", dst))
                n += 1
        except Exception as e:
            print(f"[tvurl] 失败 {f}: {e}")
    print(f"[tvurl] OK ({n} files)")


def sync_zhenxin():
    """正兴: DodgeZhang/tvbox main.zip 整仓拉取"""
    data = dl("https://github.com/DodgeZhang/tvbox/archive/refs/heads/main.zip", 240)
    tmp = tempfile.mkdtemp(prefix="zx_")
    try:
        unzip_to_mem(data, tmp, strip_root=True)
        replace_dir(tmp, "zhenxin")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("[zhenxin] OK")


def sync_pg():
    """PG: 完整拉取配置+jar+所有lib文件"""
    base = "https://www.252035.xyz/p"
    os.makedirs("pg", exist_ok=True)
    txt = dl_text(base + "/jsm.json")
    replace_file(txt, "pg/pg.json")
    jar = dl(base + "/pg.jar", 120)
    replace_file(jar, "pg/pg.jar")
    lib_files = ["lib/aes.js", "lib/crypto-js.js", "lib/danmu.js", "lib/douban.js", "lib/drpy2.js"]
    for f in lib_files:
        try:
            b = dl(base + "/" + f, 60)
            replace_file(b, "pg/" + f)
        except Exception as e:
            print(f"[pg] lib 下载失败 {f}: {e}")
    print("[pg] OK")


def sync_aowu():
    """奥五: 完整拉取配置+专属jar"""
    txt = dl_text("https://9763.kstore.vip/aowu.json")
    replace_file(txt, "aowu/aowu.json")
    m = re.search(r'"spider"\s*:\s*"([^"]*)"', txt)
    if m:
        sp = m.group(1)
        url = sp.split(";")[0]
        md5 = sp.split(";", 1)[1] if ";" in sp else ""
        b = dl(url, 120)
        replace_file(b, "aowu/custom_spider.jar")
        txt = txt.replace(sp, "./custom_spider.jar;" + md5)
        replace_file(txt, "aowu/aowu.json")
    print("[aowu] OK")


def sync_wmz():
    """WMC: 完整拉取配置+专属jar"""
    txt = dl_text("https://8815.kstore.vip/tvbox/wmz")
    replace_file(txt, "wmz/wmz.json")
    m = re.search(r'"spider"\s*:\s*"([^"]*)"', txt)
    if m:
        sp = m.group(1)
        url = sp.split(";")[0]
        md5 = sp.split(";", 1)[1] if ";" in sp else ""
        b = dl(url, 120)
        replace_file(b, "wmz/lmw.jar")
        txt = txt.replace(sp, "./lmw.jar;" + md5)
        replace_file(txt, "wmz/wmz.json")
    print("[wmz] OK")


def main():
    ok = 0
    funcs = [
        ("fty", sync_fty), ("wex", sync_wex), ("nf", sync_nf), ("feimao", sync_feimao),
        ("cl", sync_cl), ("ouyang", sync_ouyang), ("lubin", sync_lubin),
        ("dl", sync_dl), ("tvurl", sync_tvurl), ("xs", sync_xs),
        ("zhenxin", sync_zhenxin), ("pg", sync_pg), ("aowu", sync_aowu), ("wmz", sync_wmz),
    ]
    for name, fn in funcs:
        try:
            fn()
            ok += 1
        except Exception as e:
            print(f"[{name}] FAIL: {type(e).__name__}: {e}")
    print(f"\n完成: {ok}/{len(funcs)} 个源同步成功")


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""GitHub Actions 每日自动更新 lives_tv.txt
拉取: epg.pw(freetv.fun 反代, 央视卫视地方) + iptv-org 港澳台
输出: lives_tv.txt (全中文台名, 分类: 央视/卫视/地方台/港澳台/其他)
"""
import urllib.request, re, io, sys, time

URLS = {
    'cn': 'https://m3u.ibert.me/txt/cn.txt',
    'hk': 'https://iptv-org.github.io/iptv/countries/hk.m3u',
    'mo': 'https://iptv-org.github.io/iptv/countries/mo.m3u',
    'tw': 'https://iptv-org.github.io/iptv/countries/tw.m3u',
}

PROV = {
    'beijing':'北京','tianjin':'天津','hebei':'河北','shanxi':'山西','shanxi1':'陕西','shaanxi':'陕西',
    'nei_monggol':'内蒙古','innermongolia':'内蒙古','liaoning':'辽宁','jilin':'吉林','heilongjiang':'黑龙江',
    'shanghai':'上海','jiangsu':'江苏','zhejiang':'浙江','anhui':'安徽','fujian':'福建','jiangxi':'江西',
    'shandong':'山东','henan':'河南','hubei':'湖北','hunan':'湖南','guangdong':'广东','guangxi':'广西',
    'hainan':'海南','chongqing':'重庆','sichuan':'四川','guizhou':'贵州','yunnan':'云南','xizang':'西藏',
    'tibet':'西藏','gansu':'甘肃','qinghai':'青海','ningxia':'宁夏','xinjiang':'新疆','shenzhen':'深圳',
    'xiamen':'厦门','yanbian':'延边','anshun':'安顺','harbin':'哈尔滨','lanzhou':'兰州','kunming':'昆明',
    'nanjing':'南京','nanning':'南宁','wuhan':'武汉','wuxi':'无锡','yantai':'烟台','changsha':'长沙',
    'changchun':'长春','chengdu':'成都','dalian':'大连','fuzhou':'福州','haikou':'海口','hangzhou':'杭州',
    'hohhot':'呼和浩特','huainan':'淮南','huangshan':'黄山','huizhou':'惠州','jiaxing':'嘉兴','jieyang':'揭阳',
    'jining':'济宁','jinzhou':'锦州','kaifeng':'开封','langfang':'廊坊','leshan':'乐山','liuzhou':'柳州',
    'loudi':'娄底','mianyang':'绵阳','mudanjiang':'牡丹江','nanping':'南平','neijiang':'内江','ningbo':'宁波',
    'qingdao':'青岛','sanya':'三亚','shangrao':'上饶','shenyang':'沈阳','shihezi':'石河子','shijiazhuang':'石家庄',
    'taiyuan':'太原','weihai':'威海','wenzhou':'温州','xiangyang':'襄阳','xinxiang':'新乡','xinyang':'信阳',
    'xuchang':'许昌','yaan':'雅安','yibin':'宜宾','yinchuan':'银川','zhaoqing':'肇庆','zhongshan':'中山',
    'zhuhai':'珠海','zibo':'淄博','zhumadian':'驻马店','changde':'常德','changzhi':'长治','chenzhou':'郴州',
    'dali':'大理','enshi':'恩施','fuyang':'阜阳','hechi':'河池','jiujiang':'九江','lianyungang':'连云港',
    'panjin':'盘锦','puer':'普洱','qiqihaer':'齐齐哈尔','qujing':'曲靖','suihua':'绥化','suining':'遂宁',
    'weinan':'渭南','wulanchabu':'乌兰察布','xingtai':'邢台','yangquan':'阳泉','yichun':'宜春','yuncheng':'运城',
    'yuxi':'玉溪','zhangzhou':'漳州','zhaotong':'昭通','guiyang':'贵阳','taizhou':'台州','taian':'泰安',
    'tangshan':'唐山','tongliao':'通辽','yueyang':'岳阳','zaozhuang':'枣庄','dandong':'丹东','datong':'大同',
    'deyang':'德阳','dazhou':'达州','eyang':'鄂州','ganzhou':'赣州','guangyuan':'广元','handan':'邯郸',
    'huaihua':'怀化','huanggang':'黄冈','jinan':'济南','jingdezhen':'景德镇','luoyang':'洛阳','meizhou':'梅州',
    'nanchang':'南昌','ningde':'宁德','panzhihua':'攀枝花','putian':'莆田','quanzhou':'泉州','shantou':'汕头',
    'shaoguan':'韶关','shaoxing':'绍兴','suqian':'宿迁','suzhou':'苏州','tonghua':'通化','weifang':'潍坊',
    'wuhu':'芜湖','xiaogan':'孝感','zunyi':'遵义','tongren':'铜仁','chifeng':'赤峰','heze':'菏泽',
    'hengshui':'衡水','siping':'四平','xian':'西安','xuzhou':'徐州','yangzhou':'扬州','zhangjiajie':'张家界',
    'zhenjiang':'镇江','changshu':'常熟','jiangyin':'江阴','yixing':'宜兴','taicang':'太仓','kunshan':'昆山',
    'haimen':'海门','rugao':'如皋','qidong':'启东','danyang':'丹阳','xinghua':'兴化','taixing':'泰兴',
    'jingjiang':'靖江','dongtai':'东台','dafeng':'大丰','jianhu':'建湖','shuyang':'沭阳','siyang':'泗阳',
    'sihong':'泗洪','jinhu':'金湖','xuyi':'盱眙','lianshui':'涟水','peixian':'沛县','fengxian':'丰县',
    'tongshan':'铜山','jiawang':'贾汪','qingzhou':'青州','tengzhou':'滕州','rushan':'乳山','laixi':'莱西',
    'laiwu':'莱芜','longkou':'龙口','haiyang':'海阳','penglai':'蓬莱','zhangjiagang':'张家港','liyang':'溧阳',
    'jurong':'句容','yangzhong':'扬中','rucheng':'如城','xiangshui':'响水','guanyun':'灌云','guannan':'灌南',
    'huaiyin':'淮阴','hongze':'洪泽','suining_js':'睢宁','xuanwei':'宣威','zaoyang':'枣阳','zhongwei':'中卫',
    'zouping':'邹平','zunhua':'遵化','kunming':'昆明','lincang':'临沧','lijiang':'丽江','nujiang':'怒江',
    'dehong':'德宏','wenshan':'文山','honghe':'红河','xishuangbanna':'西双版纳','chuxiong':'楚雄','diqing':'迪庆',
    'baoshan':'保山','shangri-la':'香格里拉','zhaotong':'昭通','qujing':'曲靖','chuzhou':'滁州','chizhou':'池州',
    "lu'an": "六安",'liuan':'六安','bozhou':'亳州','fuyang':'阜阳','huainan':'淮南','bengbu':'蚌埠','maanshan':'马鞍山',
    'wuhu':'芜湖','tongling':'铜陵','anqing':'安庆','huangshan':'黄山','xuancheng':'宣城','hefei':'合肥',
}

CCTV_CN = {
    'cctv1':'CCTV-1 综合','cctv-1':'CCTV-1 综合','cctv2':'CCTV-2 财经','cctv-2':'CCTV-2 财经',
    'cctv3':'CCTV-3 综艺','cctv-3':'CCTV-3 综艺','cctv4':'CCTV-4 中文国际','cctv-4':'CCTV-4 中文国际',
    'cctv5':'CCTV-5 体育','cctv-5':'CCTV-5 体育','cctv5+':'CCTV-5+ 体育赛事','cctv-5+':'CCTV-5+ 体育赛事',
    'cctv6':'CCTV-6 电影','cctv-6':'CCTV-6 电影','cctv7':'CCTV-7 国防军事','cctv-7':'CCTV-7 国防军事',
    'cctv8':'CCTV-8 电视剧','cctv-8':'CCTV-8 电视剧','cctv9':'CCTV-9 纪录','cctv-9':'CCTV-9 纪录',
    'cctv10':'CCTV-10 科教','cctv-10':'CCTV-10 科教','cctv11':'CCTV-11 戏曲','cctv-11':'CCTV-11 戏曲',
    'cctv12':'CCTV-12 社会与法','cctv-12':'CCTV-12 社会与法','cctv13':'CCTV-13 新闻','cctv-13':'CCTV-13 新闻',
    'cctv14':'CCTV-14 少儿','cctv-14':'CCTV-14 少儿','cctv15':'CCTV-15 音乐','cctv-15':'CCTV-15 音乐',
    'cctv16':'CCTV-16 奥林匹克','cctv-16':'CCTV-16 奥林匹克','cctv17':'CCTV-17 农业农村','cctv-17':'CCTV-17 农业农村',
    'cctv4k':'CCTV-4K 超高清','cctv-4k':'CCTV-4K 超高清','cctv8k':'CCTV-8K 超高清','cctv-8k':'CCTV-8K 超高清',
    'cetv1':'CETV-1 中国教育','cetv-1':'CETV-1 中国教育','cetv2':'CETV-2 中国教育','cetv-2':'CETV-2 中国教育',
    'cgtn':'CGTN 新闻','cctvnews':'CGTN 新闻','cgtn_english':'CGTN 英语','cgtn_documentary':'CGTN 纪录',
    'cgtn_arabic':'CGTN 阿语','cgtn_français':'CGTN 法语','cgtn_русский':'CGTN 俄语',
}

def fetch(url, timeout=30, tries=3):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={'User-Agent':'Mozilla/5.0 (doubao-agent)'})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                data = r.read()
            return data.decode('utf-8', errors='ignore')
        except Exception as e:
            last = e
            sys.stderr.write('fetch retry %d for %s: %s\n' % (i + 1, url, e))
            time.sleep(8 * (i + 1))
    raise last

def cn_name(name):
    n = name.strip()
    low = n.lower()
    hd = ''
    mq = re.match(r'^\[(hd|sd|bd|vga|4k)\]', low)
    if mq:
        hd = {'hd':'高清','sd':'标清','bd':'高清','vga':'标清','4k':'4K'}[mq.group(1)]
        n = n[mq.end():].strip()
        low = n.lower()
    if re.search(r'[\u4e00-\u9fff]', n):
        n = re.sub(r'[_\s]*\((\d+p|\d+i)\)[_\s]*$', '', n, flags=re.I).strip()
        n = re.sub(r'\s*\[.*?\]\s*$', '', n).strip()
        n = re.sub(r'[_\s]*\[.*?\]\s*$', '', n).strip()
        n = re.sub(r'_+$', '', n).strip()
        n = re.sub(r'^\s*_+\s*', '', n).strip()
        return n + (hd and '·' + hd or '')
    c = CCTV_CN.get(low)
    if c: return c + (hd and '·' + hd or '')
    m = re.match(r'^cctv[-_]?(\d{1,2})(\+)?\s*[_\-(]?\s*(hd|4k|8k)?', low)
    if m:
        num = m.group(1); plus = m.group(2) or ''
        base = CCTV_CN.get('cctv' + num)
        if base:
            tag2 = ''
            if '4k' in low or '8k' in low: tag2 = '超高清'
            elif 'hd' in low: tag2 = '高清'
            return base + (plus and '·+ 体育赛事' or '') + (tag2 and '·'+tag2 or '')
    m = re.match(r'^cctv[-_]?4k', low)
    if m: return 'CCTV-4K 超高清'
    m = re.match(r'^cctv[-_]?8k', low)
    if m: return 'CCTV-8K 超高清'
    m = re.match(r'^cetv[-_]?(\d)', low)
    if m: return 'CETV-%s 中国教育' % m.group(1)
    m = re.match(r'^cgtn', low)
    if m: return 'CGTN 新闻'
    base_n = re.sub(r'\s*[\[(].*?[\])]\s*$', '', n, flags=re.I).strip().lower()
    if 'phoenix' in low: return '凤凰' + ('资讯' if 'info' in low else '中文') + (hd and '·' + hd or '')
    if 'rthk' in low:
        mm = re.search(r'31|32|33|34|35', low)
        return ('港台电视' + (mm.group(0) if mm else '')) + (hd and '·' + hd or '')
    if 'hoy' in low: return 'HOY TV' + (hd and '·' + hd or '')
    if 'tdm' in low:
        mm = re.search(r'ch(\d)', low)
        ch = mm.group(1) if mm else ''
        names = {'2':'澳门有线','3':'澳广视卫星','4':'澳广视体育','5':'澳广视资讯','6':'澳广视综艺'}
        return names.get(ch, '澳广视' + ch) + (hd and '·' + hd or '')
    if 'jade' in low: return '翡翠台(TVB)' + (hd and '·' + hd or '')
    if 'tvbs' in low: return ('TVBS新闻' if 'news' in low else 'TVBS亚洲') + (hd and '·' + hd or '')
    if 'ebc' in low: return ('东森财经' if 'financ' in low else '东森新闻') + (hd and '·' + hd or '')
    if 'set' in low: return '三立新闻' + (hd and '·' + hd or '')
    if 'ftv' in low: return '民视' + (hd and '·' + hd or '')
    if 'cts' in low: return '华视' + (hd and '·' + hd or '')
    if 'ttv' in low: return '台视' + (hd and '·' + hd or '')
    if 'cti' in low: return '中天综合' + (hd and '·' + hd or '')
    if 'momo' in low: return 'MOMO综合台' + (hd and '·' + hd or '')
    if 'celestial' in low: return '天映电影' + (hd and '·' + hd or '')
    if 'mei ah' in low: return '美亚电影' + (hd and '·' + hd or '')
    if 'tvn' in low: return 'tvN亚洲' + (hd and '·' + hd or '')
    if 'lotus' in low: return '莲花卫视' + (hd and '·' + hd or '')
    if 'macau' in low: return '澳门有线' + (hd and '·' + hd or '')
    if 'hbo' in low: return 'HBO亚洲' + (hd and '·' + hd or '')
    if 'hakka' in low: return '客家电视台' + (hd and '·' + hd or '')
    if 'good' in low: return '好消息电视台' + (hd and '·' + hd or '')
    if 'indigenous' in low: return '原住民族电视台' + (hd and '·' + hd or '')
    if 'supreme' in low: return '清海无上师' + (hd and '·' + hd or '')
    if 'wxtv' in low: return '世界电视' + (hd and '·' + hd or '')
    if 'discovery' in low: return 'Discovery探索' + (hd and '·' + hd or '')
    if 'axn' in low: return 'AXN' + (hd and '·' + hd or '')
    m = re.match(r'^([a-z0-9_]+)_satellite_tv(_|$)', low)
    if m:
        p = PROV.get(m.group(1).replace('_',''))
        if p: return p + '卫视' + (hd and '·' + hd or '')
    m = re.match(r'^([a-z0-9_]+)_tv$', low)
    if m:
        p = PROV.get(m.group(1).replace('_',''))
        if p: return p + '电视台' + (hd and '·' + hd or '')
    m = re.match(r'^([a-z0-9_]+)_comprehensive_news_channel$', low)
    if m:
        p = PROV.get(m.group(1).replace('_',''))
        if p: return p + '新闻综合' + (hd and '·' + hd or '')
    out = n
    for k,v in sorted(PROV.items(), key=lambda x:-len(x[0])):
        kk = k.replace('_',' ')
        if kk in low:
            out = out.replace(k.capitalize(), v).replace(k.upper(), v).replace(k, v)
            break
    if out != n:
        return out + (hd and '·' + hd or '')
    return n + (hd and '·' + hd or '')

def parse_txt(text):
    items = []; cat = ''
    for line in text.splitlines():
        line = line.strip()
        if not line: continue
        if line.endswith('#genre#'):
            cat = line[:-len('#genre#')].strip(); continue
        if ',' in line:
            name, url = line.split(',', 1)
            name = name.strip(); url = url.strip()
            if url.startswith(('rtp://','igmp://')): continue
            items.append((cat, name, url))
    return items

def parse_m3u(text):
    items = []; cat = '其他'; name = None
    for line in text.splitlines():
        line = line.strip()
        if not line: continue
        if line.startswith('#EXTINF'):
            m = re.search(r'group-title="([^"]*)"', line)
            if m: cat = m.group(1)
            name = line.split(',')[-1].strip()
        elif line.startswith('#EXTM3U') or line.startswith('#'):
            continue
        else:
            url = line.strip()
            if url.startswith(('rtp://','igmp://')): continue
            if name:
                items.append((cat, name, url))
                name = None
    return items

def main():
    srcs = []
    try:
        srcs += parse_txt(fetch(URLS['cn']))
    except Exception as e:
        sys.stderr.write('cn fetch fail: %s\n' % e)
    for k in ('hk','mo','tw'):
        try:
            srcs += parse_m3u(fetch(URLS[k]))
        except Exception as e:
            sys.stderr.write('%s fetch fail: %s\n' % (k, e))
    if not srcs:
        sys.exit(1)
    seen = {}
    for cat, name, url in srcs:
        if url in seen:
            old = seen[url]
            new = cn_name(name)
            if not re.search(r'[\u4e00-\u9fff]', old) and re.search(r'[\u4e00-\u9fff]', new):
                seen[url] = new
            continue
        seen[url] = cn_name(name)
    groups = {'央视':[], '卫视':[], '地方台':[], '港澳台':[], '其他':[]}
    for url, name in seen.items():
        if not name: name = url
        if re.match(r'^CCTV|^CETV|^CGTN', name): groups['央视'].append((name,url))
        elif re.search(r'卫视', name): groups['卫视'].append((name,url))
        elif any(k in name for k in ['凤凰','翡翠','明珠','港台','TVB','ViuTV','有线','HOY','开电视','RTHK','莲花','澳广视','澳门','华视','台视','民视','东森','TVBS','三立','中天','中视','客家','原住民','大爱','好消息','公视','MOMO','新唐人','tvN','TVN','HBO','天映','美亚']):
            groups['港澳台'].append((name,url))
        elif re.search(r'新闻|综合|电视台|频道|TV|高清|4K|影院|电影|剧场|卡通|少儿|教育|科教|体育|音乐|纪实|纪录|戏曲|财经|生活|公共|影视|综艺|购物|旅游|法治|军事|国际|文化', name):
            groups['地方台'].append((name,url))
        else:
            groups['其他'].append((name,url))
    lines = []
    for gname in ['央视','卫视','地方台','港澳台','其他']:
        items = groups[gname]
        if not items: continue
        lines.append(gname + ',#genre#')
        for name,url in items:
            lines.append(name + ',' + url)
    with io.open('lives_tv.txt', 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')
    total = len(seen)
    zh = sum(1 for n in seen.values() if re.search(r'[\u4e00-\u9fff]', n))
    sys.stdout.write('total=%d chinese=%d (%d%%) groups=%s\n' % (total, zh, 100.0*zh/total if total else 0, {k:len(v) for k,v in groups.items()}))

if __name__ == '__main__':
    main()

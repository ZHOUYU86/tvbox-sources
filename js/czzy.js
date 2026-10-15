// 厂长资源 drpy2 JS 爬虫（自用版，基于本地 tvurl/js/厂长资源.js 适配当前站点结构）
// 主站 www.4kcz.com，请求必须带 MOBILE_UA + Cookie: esc_search_captcha=1（过 WAF 关键）
// 播放页 .videoplay iframe src 的 url= 参数即 m3u8 直链，lazy 直接输出
var rule = {
    title: '厂长资源',
    host: 'https://www.4kcz.com',
    url: '/fyclassfyfilter',
    filterable: 0,// 分类筛选关闭（当前分类直接用 class_url）
    searchUrl: '/page/fypage?s=**',
    searchable: 0,// 站长站搜索接口已失效，关闭搜索
    headers: {
        'User-Agent': 'MOBILE_UA',
        'Cookie': 'esc_search_captcha=1'
    },
    class_name: '全部&豆瓣电影Top250&高分影视&最新电影&热映中&站长推荐&电影&电视剧&动画&国产剧&日剧&韩剧&美剧&海外剧&俄罗斯电影&加拿大电影&华语电影&印度电影&日本电影&欧美电影&法国电影&英国电影&韩国电影&纪录片',
    class_url: 'movie_bt&dbtop250&gaofenyingshi&zuixindianying&reyingzhong&/movie_bt_series/zhanchangtuijian&/movie_bt_series/dyy&/movie_bt_series/dianshiju&/movie_bt_series/dohua&/movie_bt_series/guochanju&/movie_bt_series/rj&/movie_bt_series/hj&/movie_bt_series/mj&/movie_bt_series/hwj&/movie_bt_series/eluosidianying&/movie_bt_series/jianadadianying&/movie_bt_series/huayudianying&/movie_bt_series/yindudianying&/movie_bt_series/ribendianying&/movie_bt_series/meiguodianying&/movie_bt_series/faguodianying&/movie_bt_series/yingguodianying&/movie_bt_series/hanguodianying&movie_bt//movie_bt_tags/jlpp',
    play_parse: true,
    // lazy：抓播放页 → iframe src 的 url= 参数 → m3u8 直链
    lazy: `js:
        var html = request(input);
        var m = html.match(/[?&]url=([^&'"]+\.m3u8[^&'"]*)/);
        if (m) {
            try { input = decodeURIComponent(m[1]) } catch(e) { input = m[1] }
        } else {
            var m2 = html.match(/https?:\\/\\/[^"'<>\\s]+\\.m3u8[^"'<>\\s]*/);
            input = m2 ? m2[0] : input;
        }
    `,
    推荐: '.bt_img;ul&&li;*;*;*;*',
    double: true,
    一级: '.bt_img&&ul&&li;h3.dytit&&Text;img.lazy&&data-original;.jidi&&Text;a&&href',
    二级: {
        "title": "h1&&Text;.moviedteail_list li&&a&&Text",
        "img": "div.dyimg img&&src",
        "desc": ".moviedteail_list li:eq(3) a&&Text;.moviedteail_list li:eq(2) a&&Text;.moviedteail_list li:eq(1) a&&Text;.moviedteail_list li:eq(7)&&Text;.moviedteail_list li:eq(5)&&Text",
        "content": ".yp_context&&Text",
        "tabs": ".mi_paly_box span",
        "lists": ".paly_list_btn:eq(#id) a"
    },
    搜索: '.search_list&&ul&&li;*;*;*;*',
}

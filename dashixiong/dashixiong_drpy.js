var rule = {
    title:'大师兄影视',
    host:'https://www.lzhuanqiu.com',
    homeUrl:'',
    url:'/fyclass/pfypage',
    detailUrl:'/q/fyid',
    searchUrl:'/v/pgs/?search_key=**',
    searchable:2,
    headers:{
        'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer':'https://www.lzhuanqiu.com/'
    },
    timeout:10000,
    class_url:'dianyingpian&lianxuju&zongyipian&dongmanpian&dianyingjieshu&duanju1',
    class_name:'电影片&连续剧&综艺片&动漫片&电影解说&短剧',
    推荐:'.tuwen&&ul&&li;.pic&&a&&img&&data-original;.biaoti&&a&&Text;.pic&&span&&Text;a&&href',
    double:true,
    limit:6,
    play_parse:true,
    lazy:'js:let html=fetch(input,fetch_params);let m=html.match(/url:\\s*[\'\"]([^\'\"]+\\.m3u8[^\'\"]*)[\'\"]/);input=m?m[1]:\"\";',
    一级:'.tuwen&&ul&&li;.pic&&a&&img&&data-original;.biaoti&&a&&Text;.pic&&span&&Text;a&&href',
    二级:'*',
    搜索:'.tuwen&&ul&&li;.pic&&a&&img&&data-original;.biaoti&&a&&Text;.pic&&span&&Text;a&&href',
}

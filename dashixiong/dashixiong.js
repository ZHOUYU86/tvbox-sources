/**
 * 大师兄影视 TVBox JS爬虫
 * 网站: https://www.lzhuanqiu.com/
 */

var BASE_URL = "https://www.lzhuanqiu.com";
var UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36";

var CATEGORIES = [
    { type_id: "dianyingpian", type_name: "电影片" },
    { type_id: "lianxuju", type_name: "连续剧" },
    { type_id: "zongyipian", type_name: "综艺片" },
    { type_id: "dongmanpian", type_name: "动漫片" },
    { type_id: "dianyingjieshu", type_name: "电影解说" },
    { type_id: "duanju1", type_name: "短剧" }
];

function req(url) {
    var resp = fetch(url, {
        headers: { "User-Agent": UA, "Referer": BASE_URL + "/" }
    });
    var code = resp.code;
    var body = resp.body;
    if (code != 200) {
        return "";
    }
    return body;
}

function decodeHtml(str) {
    if (!str) return "";
    str = str.replace(/&#(\d+);/g, function(m, n) { return String.fromCharCode(n); });
    str = str.replace(/&amp;/g, "&").replace(/&lt;/g, "<").replace(/&gt;/g, ">").replace(/&quot;/g, '"');
    return str;
}

function parseList(html) {
    var items = [];
    var pattern = /<div class="pic"><a href="(https?:\/\/www\.lzhuanqiu\.com\/q\/[^"]*)"><img[^>]*data-original="([^"]*)"[^>]*><\/a><span>([^<]*)<\/span><\/div>\s*<div class="biaoti"><a[^>]*>([^<]*)<\/a><\/div>\s*<p>([^<]*)<\/p>/g;
    var m;
    while ((m = pattern.exec(html)) !== null) {
        var url = m[1];
        var pic = m[2];
        var status = decodeHtml(m[3]);
        var title = decodeHtml(m[4]);
        var actors = decodeHtml(m[5]);
        var vod_id = url.replace(/\/$/, "").split("/").pop();
        items.push({
            vod_id: vod_id,
            vod_name: title,
            vod_pic: pic,
            vod_remarks: status,
            vod_actor: actors
        });
    }
    return items;
}

function init(cfg) {
}

function home() {
    return JSON.stringify({ class: CATEGORIES });
}

function homeVod() {
    var html = req(BASE_URL + "/");
    var items = parseList(html);
    return JSON.stringify({ list: items });
}

function category(tid, pg, filter, extend) {
    var url;
    if (pg == 1) {
        url = BASE_URL + "/" + tid + "/";
    } else {
        url = BASE_URL + "/" + tid + "/p" + pg + "/";
    }
    var html = req(url);
    var items = parseList(html);
    
    // 解析总页数
    var pageCount = 1;
    var pagePattern = new RegExp("/" + tid + "/p(\\d+)/", "g");
    var pm;
    while ((pm = pagePattern.exec(html)) !== null) {
        var p = parseInt(pm[1]);
        if (p > pageCount) pageCount = p;
    }
    
    return JSON.stringify({
        page: parseInt(pg),
        pagecount: pageCount,
        list: items
    });
}

function detail(ids) {
    var id = ids.split(",")[0];
    var url = BASE_URL + "/q/" + id + "/";
    var html = req(url);
    
    // 标题
    var title = id;
    var titleMatch = html.match(/property="og:title" content="([^"]*)"/);
    if (titleMatch) {
        title = titleMatch[1];
        var bookMatch = title.match(/《([^》]*)》/);
        if (bookMatch) {
            title = bookMatch[1];
        } else {
            title = title.replace(/[_\-].*$/, "");
        }
    }
    title = decodeHtml(title);
    
    // 封面
    var pic = "";
    var picMatch = html.match(/property="og:image" content="([^"]*)"/);
    if (picMatch) pic = picMatch[1];
    
    // 简介
    var desc = "";
    var descMatch = html.match(/property="og:description" content="([^"]*)"/);
    if (descMatch) desc = decodeHtml(descMatch[1]);
    
    // 演员
    var actor = "";
    var actorMatch = html.match(/property="og:video:actor" content="([^"]*)"/);
    if (actorMatch) actor = decodeHtml(actorMatch[1]);
    
    // 导演
    var director = "";
    var directorMatch = html.match(/property="og:video:director" content="([^"]*)"/);
    if (directorMatch) director = decodeHtml(directorMatch[1]);
    
    // 解析播放源
    var playSources = [];
    var boxBlocks = html.split(/<div[^>]*class="box"[^>]*>/);
    for (var i = 1; i < boxBlocks.length; i++) {
        var block = boxBlocks[i];
        var nameMatch = block.match(/<b>([^<]*)<\/b>/);
        if (!nameMatch) continue;
        var sourceName = decodeHtml(nameMatch[1].trim());
        
        var bofangMatch = block.match(/<div class="bofang">([\s\S]*?)<\/div>/);
        if (!bofangMatch) continue;
        var epHtml = bofangMatch[1];
        
        var episodes = [];
        var epPattern = /<a[^>]*title="([^"]*)"[^>]*href="([^"]*)"[^>]*>/g;
        var em;
        while ((em = epPattern.exec(epHtml)) !== null) {
            var epTitle = decodeHtml(em[1]);
            var epUrl = em[2];
            if (epUrl.indexOf("/") === 0) epUrl = BASE_URL + epUrl;
            episodes.push(epTitle + "$" + epUrl);
        }
        
        if (episodes.length > 0) {
            playSources.push(sourceName + "$" + episodes.join("#"));
        }
    }
    
    var vodPlayUrl = playSources.join("$$");
    
    // 备用：如果没解析到播放源
    if (!vodPlayUrl) {
        var allLinks = html.match(/<a[^>]*href="(https?:\/\/www\.lzhuanqiu\.com\/vh\/[^"]*)"[^>]*>([^<]*)<\/a>/g);
        if (allLinks) {
            var eps = [];
            for (var j = 0; j < allLinks.length; j++) {
                var lm = allLinks[j].match(/href="([^"]*)"[^>]*>([^<]*)</);
                if (lm) {
                    eps.push(decodeHtml(lm[2]) + "$" + lm[1]);
                }
            }
            if (eps.length > 0) {
                vodPlayUrl = "默认$" + eps.join("#");
            }
        }
    }
    
    var detail = {
        vod_id: id,
        vod_name: title,
        vod_pic: pic,
        vod_content: desc,
        vod_actor: actor,
        vod_director: director,
        vod_play_url: vodPlayUrl
    };
    
    return JSON.stringify({ list: [detail] });
}

function play(flag, id, flags) {
    var html = req(id);
    var playUrl = "";
    
    // 提取DPlayer的video url
    var urlMatch = html.match(/url:\s*['"]([^'"]+\.m3u8[^'"]*)['"]/);
    if (urlMatch) {
        playUrl = urlMatch[1];
    } else {
        // 备用：提取任何m3u8链接
        var m3u8Match = html.match(/https?:\/\/[^\s"'<>]+\.m3u8[^\s"'<>]*/);
        if (m3u8Match) {
            playUrl = m3u8Match[0];
        }
    }
    
    return JSON.stringify({ parse: 0, url: playUrl });
}

function search(wd, quick, pg) {
    var url = BASE_URL + "/v/pgs/?search_key=" + encodeURIComponent(wd);
    if (pg && pg > 1) url += "&page=" + pg;
    var html = req(url);
    var items = parseList(html);
    return JSON.stringify({ list: items });
}

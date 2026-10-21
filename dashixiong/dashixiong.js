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
    try {
        // TVBox JS环境用java函数发起HTTP请求
        var resp = java.get(url, {
            headers: {
                "User-Agent": UA,
                "Referer": BASE_URL + "/"
            }
        });
        if (resp) {
            if (typeof resp === "string") return resp;
            if (resp.body) return resp.body;
            if (resp.result) return resp.result;
            if (resp.content) return resp.content;
            return resp;
        }
        return "";
    } catch(e) {
        // 备用方式
        try {
            var resp2 = java.http(url, {
                method: "GET",
                headers: {
                    "User-Agent": UA,
                    "Referer": BASE_URL + "/"
                }
            });
            if (resp2) {
                if (typeof resp2 === "string") return resp2;
                if (resp2.body) return resp2.body;
                if (resp2.result) return resp2.result;
                return resp2;
            }
            return "";
        } catch(e2) {
            return "";
        }
    }
}

function decodeHtml(str) {
    if (!str) return "";
    str = str.replace(/&#(\d+);/g, function(m, n) { return String.fromCharCode(n); });
    str = str.replace(/&amp;/g, "&").replace(/&lt;/g, "<").replace(/&gt;/g, ">").replace(/&quot;/g, '"');
    return str;
}

function parseList(html) {
    var items = [];
    if (!html) return items;
    
    var blockPattern = /<li[^>]*>[\s\S]*?<\/li>/g;
    var blocks = html.match(blockPattern);
    if (!blocks) return items;
    
    for (var i = 0; i < blocks.length; i++) {
        var block = blocks[i];
        var urlMatch = block.match(/href="(https?:\/\/www\.lzhuanqiu\.com\/q\/[^"]*)"/);
        if (!urlMatch) continue;
        var url = urlMatch[1];
        var vod_id = url.replace(/\/$/, "").split("/").pop();
        
        var picMatch = block.match(/data-original="([^"]*)"/);
        var pic = picMatch ? picMatch[1] : "";
        
        var titleMatch = block.match(/class="biaoti"[^>]*>[\s\S]*?<a[^>]*>([^<]*)<\/a>/);
        if (!titleMatch) titleMatch = block.match(/title="([^"]*)"/);
        var title = titleMatch ? decodeHtml(titleMatch[1]) : vod_id;
        
        var remarkMatch = block.match(/<span>([^<]*)<\/span>/);
        var remark = remarkMatch ? decodeHtml(remarkMatch[1]) : "";
        
        var actorMatch = block.match(/<p>([^<]*)<\/p>/);
        var actor = actorMatch ? decodeHtml(actorMatch[1]) : "";
        
        items.push({
            vod_id: vod_id,
            vod_name: title,
            vod_pic: pic,
            vod_remarks: remark,
            vod_actor: actor
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
    if (!pg || pg == "1" || pg == 1) {
        url = BASE_URL + "/" + tid + "/";
    } else {
        url = BASE_URL + "/" + tid + "/p" + pg + "/";
    }
    var html = req(url);
    var items = parseList(html);
    
    var pageCount = 1;
    if (html) {
        var pagePattern = new RegExp("/" + tid + "/p(\\d+)/", "g");
        var pm;
        while ((pm = pagePattern.exec(html)) !== null) {
            var p = parseInt(pm[1]);
            if (p > pageCount) pageCount = p;
        }
    }
    
    return JSON.stringify({
        page: parseInt(pg) || 1,
        pagecount: pageCount,
        list: items
    });
}

function detail(ids) {
    var id = ids.split(",")[0];
    var url = BASE_URL + "/q/" + id + "/";
    var html = req(url);
    
    var title = id;
    if (html) {
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
    }
    
    var pic = "";
    if (html) {
        var picMatch = html.match(/property="og:image" content="([^"]*)"/);
        if (picMatch) pic = picMatch[1];
    }
    
    var desc = "";
    if (html) {
        var descMatch = html.match(/property="og:description" content="([^"]*)"/);
        if (descMatch) desc = decodeHtml(descMatch[1]);
    }
    
    var actor = "";
    if (html) {
        var actorMatch = html.match(/property="og:video:actor" content="([^"]*)"/);
        if (actorMatch) actor = decodeHtml(actorMatch[1]);
    }
    
    var director = "";
    if (html) {
        var directorMatch = html.match(/property="og:video:director" content="([^"]*)"/);
        if (directorMatch) director = decodeHtml(directorMatch[1]);
    }
    
    var playSources = [];
    if (html) {
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
    }
    
    var vodPlayUrl = playSources.join("$$");
    
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
    
    if (html) {
        var urlMatch = html.match(/url:\s*['"]([^'"]+\.m3u8[^'"]*)['"]/);
        if (urlMatch) {
            playUrl = urlMatch[1];
        } else {
            var m3u8Match = html.match(/https?:\/\/[^\s"'<>]+\.m3u8[^\s"'<>]*/);
            if (m3u8Match) {
                playUrl = m3u8Match[0];
            }
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

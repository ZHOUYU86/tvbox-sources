package com.github.catvod.spider;

import android.content.Context;
import android.util.Log;

import com.github.catvod.bean.Class;
import com.github.catvod.bean.Result;
import com.github.catvod.bean.Vod;
import com.github.catvod.crawler.Spider;

import org.json.JSONObject;

import java.net.InetAddress;
import java.net.UnknownHostException;
import java.security.MessageDigest;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.TimeUnit;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

import okhttp3.Dns;
import okhttp3.OkHttpClient;
import okhttp3.Request;
import okhttp3.Response;

/**
 * 可可影视（keke2.app / kkys01.com / kekys.com）jar 爬虫 —— 苹果CMS 网页版 + cdndefend JS 挑战
 *
 * 站点实测（2026-10-13）：
 *   挑战:   首页首次访问返回 850 挑战页，JS 用 SHA1(token+i) 计算 cookie（cdndefend_js_cookie）
 *           已破解：token 固定 a0_0x2a54[0]，n1=token[0] 的 16 进制值，
 *           暴力 i 使 sha1(token+i)[n1]==0xB0 && [n1+1]==0x0B 即得 cookie；
 *           实测当前 cookie=cdndefend_js_cookie=26F4497D23979FF11C34B67261D2FEF78DC78DA452882（长期有效）
 *           若失效（返回 850），本类自动从挑战页提取 token 重算。
 *   分类:   /channel/{tid}.html 是分类首页（48条混合），真正可翻页列表在
 *           /show/{tid}------.html（第1页，18条）+ /show/{tid}-----3-{page}.html（第N页）
 *           tid: 1电影 2剧集 3动漫 4综艺 6短剧
 *   列表:   条目 <a href="/detail/{id}.html" class="v-item">，图片 <img data-original="...">，
 *           片名 <div class="v-item-title">（不带 style 的才是片名，带 display:none 的是站名水印）
 *   分页:   每页18条；分页导航 <div class="pagenation-box"> 内 page-item-next 为"下一页"，
 *           其 href 为 /show/{tid}-----3-{page+1}.html（有下一页则总页数=当前页+1，无则=当前页）
 *   详情:   /detail/{id}.html
 *           标题 .detail-title 内第2个 <strong>（第1/3个是水印站名）
 *           简介 .detail-desc p；导演/演员 .detail-info-row-side("导演:") + .detail-info-row-main
 *   线路:   .source-list-box-main 内 .source-item .source-item-label（线路名，顺序=N）
 *   集数:   .episode-list-box-main 内多个 .episode-list 块，第N个块=第N个线路的集数；
 *           集数 <a class="episode-item" href="/play/{id}-{sid}-{nid}.html"><span>集名</span></a>
 *   播放:   /play/{id}-{sid}-{nid}.html 内 JS：const playSource = { src: "https://.../index.m3u8?...", ...}
 *           正则 src:\s*"([^"]+)" 提取 m3u8 直链
 *   搜索:   /search?k={关键词}&t={签名}，t 每次从最新首页 HTML 抓取（首页热搜链接自带，
 *           正则 search\?k=[^"&]*&amp;t=([^"&]+)），t 不能跨页面复用；
 *           结果 <a class="search-result-item">，标题 .title，图片第一个 img data-original
 *
 * 容错：
 *   1. cookie 失效自动重算（挑战页动态提取 token 暴力 SHA1）
 *   2. 图片 &amp; 还原、相对路径补全域名
 *   3. 线路名与集数按顺序一一对应输出
 */
public class WwwKeke extends Spider {

    private static final String SITE = "https://www.keke2.app";
    private static final String UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36";

    /** 已破解的 cdndefend cookie（token=26F4497D23979FF11C34B67261D2FEF78DC78DA4 + i=52882） */
    private static volatile String COOKIE = "cdndefend_js_cookie=26F4497D23979FF11C34B67261D2FEF78DC78DA452882";

    private static final OkHttpClient CLIENT = createClient();

    private static OkHttpClient createClient() {
        try {
            javax.net.ssl.TrustManager[] trustAll = new javax.net.ssl.TrustManager[]{
                    new javax.net.ssl.X509TrustManager() {
                        public void checkClientTrusted(java.security.cert.X509Certificate[] chain, String authType) {
                        }

                        public void checkServerTrusted(java.security.cert.X509Certificate[] chain, String authType) {
                        }

                        public java.security.cert.X509Certificate[] getAcceptedIssuers() {
                            return new java.security.cert.X509Certificate[0];
                        }
                    }
            };
            javax.net.ssl.SSLContext sc = javax.net.ssl.SSLContext.getInstance("TLS");
            sc.init(null, trustAll, new java.security.SecureRandom());
            return new OkHttpClient.Builder()
                    .connectTimeout(15, TimeUnit.SECONDS)
                    .readTimeout(25, TimeUnit.SECONDS)
                    .sslSocketFactory(sc.getSocketFactory(), (javax.net.ssl.X509TrustManager) trustAll[0])
                    .hostnameVerifier((hostname, session) -> true)
                    .dns(new Dns() {
                        @Override
                        public List<InetAddress> lookup(String hostname) throws UnknownHostException {
                            List<InetAddress> list = new ArrayList<>();
                            try {
                                list.addAll(Dns.SYSTEM.lookup(hostname));
                            } catch (Exception ignored) {
                            }
                            if (list.isEmpty()) throw new UnknownHostException(hostname);
                            return list;
                        }
                    })
                    .build();
        } catch (Exception e) {
            return new OkHttpClient.Builder()
                    .connectTimeout(15, TimeUnit.SECONDS)
                    .readTimeout(25, TimeUnit.SECONDS)
                    .build();
        }
    }

    /** 列表条目：<a href="/detail/{id}.html" class="v-item"> ... </a> */
    private static final Pattern ITEM_PAT = Pattern.compile("<a href=\"/detail/(\\d+)\\.html\"[^>]*class=\"v-item\"([\\s\\S]*?)</a>");
    /** 图片 lazy 属性 */
    private static final Pattern PIC_PAT = Pattern.compile("data-original=\"([^\"]+)\"");
    /** 片名：无 style 的 v-item-title（带 display:none 的是水印） */
    private static final Pattern TITLE_PAT = Pattern.compile("<div class=\"v-item-title\">([^<]+)</div>");
    /** 分页"下一页"链接：/show/{tid}-----3-{page}.html */
    private static final Pattern NEXT_PAGE_PAT = Pattern.compile("href=\"/show/\\d+-----\\d+-(\\d+)\\.html\"[^>]*class=\"page-item-next\"");
    /** 详情标题：detail-title 内第2个 strong */
    private static final Pattern DET_TITLE_PAT = Pattern.compile("<div class=\"detail-title\">([\\s\\S]*?)</div>");
    private static final Pattern STRONG_PAT = Pattern.compile("<strong>([^<]+)</strong>");
    /** 简介 */
    private static final Pattern DESC_PAT = Pattern.compile("class=\"detail-desc\"[^>]*>\\s*<p>([\\s\\S]*?)</p>");
    /** 信息行：side("导演:") + main */
    private static final Pattern INFO_ROW_PAT = Pattern.compile("<div class=\"detail-info-row-side\">([^<]{1,10})</div>\\s*<div class=\"detail-info-row-main\">([\\s\\S]*?)</div>");
    /** 线路名：.source-item 内 .source-item-label */
    private static final Pattern LINE_PAT = Pattern.compile("<a href=\"#\" class=\"source-item[^\"]*\">\\s*<span class=\"source-item-label\">([^<]+)</span>");
    /** 集数块：.episode-list 块（一个线路一个；块内仅 a 标签，第一个 </div> 即块结束） */
    private static final Pattern EP_LIST_PAT = Pattern.compile("<div class=\"episode-list\"([\\s\\S]*?)</div>");
    /** 集数链接：href="/play/{id}-{sid}-{nid}.html" class="episode-item"><span>集名</span> */
    private static final Pattern EP_PAT = Pattern.compile("href=\"/play/\\d+-(\\d+)-(\\d+)\\.html\"[^>]*class=\"episode-item\"[^>]*>\\s*<span>([^<]+)</span>");
    /** 播放地址：const playSource = { src: "..." } */
    private static final Pattern M3U8_PAT = Pattern.compile("src:\\s*\"([^\"]+)\"");
    /** 首页搜索签名 t */
    private static final Pattern T_PAT = Pattern.compile("search\\?k=[^\"&]*&amp;t=([^\"&]+)");
    /** 搜索结果块：<a href="/detail/{id}.html" class="search-result-item"> */
    private static final Pattern SEARCH_ITEM_PAT = Pattern.compile("<a href=\"/detail/(\\d+)\\.html\" class=\"search-result-item\"([\\s\\S]*?)</a>");
    /** 搜索标题 .title */
    private static final Pattern SEARCH_TITLE_PAT = Pattern.compile("<div class=\"title\">([^<]+)</div>");
    /** 挑战页 token：a0_0x2a54=['token',...] */
    private static final Pattern TOKEN_PAT = Pattern.compile("a0_0x2a54=\\[([^;\\]]*)\\]");

    private Map<String, String> headers() {
        Map<String, String> h = new HashMap<>();
        h.put("User-Agent", UA);
        h.put("Referer", SITE + "/");
        h.put("Accept", "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8");
        return h;
    }

    /** SHA1 求 cookie：sha1(token+i)[n1]==0xB0 && [n1+1]==0x0B */
    private String solveCookie(String challengeHtml) {
        try {
            Matcher m = TOKEN_PAT.matcher(challengeHtml);
            if (!m.find()) return null;
            String[] parts = m.group(1).split(",");
            if (parts.length == 0) return null;
            String token = parts[0].trim().replaceAll("['\"]", "");
            if (token.isEmpty()) return null;
            int n1 = Integer.parseInt(token.substring(0, 1), 16);
            MessageDigest md = MessageDigest.getInstance("SHA-1");
            for (int i = 0; i < 500000; i++) {
                byte[] d = md.digest((token + i).getBytes("UTF-8"));
                if ((d[n1] & 0xFF) == 0xB0 && (d[n1 + 1] & 0xFF) == 0x0B) {
                    return "cdndefend_js_cookie=" + token + i;
                }
            }
        } catch (Exception e) {
            Log.d("TV-KEKE", "solveCookie err: " + e.getMessage());
        }
        return null;
    }

    private String get(String url) {
        Exception lastErr = null;
        for (int attempt = 0; attempt < 6; attempt++) {
            try {
                Request.Builder builder = new Request.Builder().url(url);
                for (Map.Entry<String, String> e : headers().entrySet()) {
                    builder.header(e.getKey(), e.getValue());
                }
                builder.header("Cookie", COOKIE);
                try (Response resp = CLIENT.newCall(builder.build()).execute()) {
                    if (resp.body() == null) continue;
                    String body = resp.body().string();
                    int code = resp.code();
                    // cdndefend 挑战：850 状态或内容含挑战脚本 → 重算 cookie
                    if (code == 850 || (body != null && body.contains("cdndefend"))) {
                        String newCookie = solveCookie(body);
                        if (newCookie != null) {
                            Log.d("TV-KEKE", "cookie refreshed");
                            COOKIE = newCookie;
                            continue;
                        }
                        return null;
                    }
                    if (body != null && body.length() > 200) {
                        Log.d("TV-KEKE", "get OK: " + url + " len=" + body.length());
                        return body;
                    }
                }
            } catch (Exception e) {
                lastErr = e;
            }
        }
        Log.d("TV-KEKE", "get failed: " + url + " err=" + (lastErr == null ? "null" : lastErr.getMessage()));
        return null;
    }

    /** 图片还原：&amp; -> &；/ 开头 -> 补域名 */
    private String fullPic(String pic) {
        if (pic == null || pic.isEmpty()) return "";
        pic = pic.replace("&amp;", "&");
        if (pic.startsWith("//")) return "https:" + pic;
        if (pic.startsWith("/")) return SITE + pic;
        return pic;
    }

    private String cleanText(String s) {
        if (s == null) return "";
        return s.replaceAll("<[^>]+>", "").replaceAll("\\s+", " ").trim();
    }

    @Override
    public void init(Context context, String extend) {
    }

    @Override
    public String homeContent(boolean filter) {
        try {
            String[][] classes = {
                    {"1", "电影"}, {"2", "剧集"}, {"3", "动漫"}, {"4", "综艺"}, {"6", "短剧"}
            };
            List<Class> list = new ArrayList<>();
            for (String[] c : classes) {
                list.add(new Class(c[0], c[1]));
            }
            List<Vod> items = new ArrayList<>();
            try {
                String html = get(SITE + "/");
                if (html != null) {
                    items = parseList(html);
                }
                Log.d("TV-KEKE", "home items=" + items.size());
            } catch (Exception ignored) {
            }
            return Result.string(list, items);
        } catch (Exception e) {
            return Result.error("首页失败: " + e.getMessage());
        }
    }

    /** 解析列表条目（首页/分类页通用） */
    private List<Vod> parseList(String html) {
        List<Vod> items = new ArrayList<>();
        if (html == null || html.isEmpty()) return items;
        Matcher m = ITEM_PAT.matcher(html);
        while (m.find()) {
            try {
                String id = m.group(1);
                String block = m.group(2);
                String pic = "";
                Matcher pm = PIC_PAT.matcher(block);
                if (pm.find()) pic = fullPic(pm.group(1));
                String title = "";
                Matcher tm = TITLE_PAT.matcher(block);
                if (tm.find()) title = tm.group(1).trim();
                if (title.isEmpty()) continue;
                items.add(new Vod(id, title, pic, ""));
            } catch (Exception ignored) {
            }
        }
        return items;
    }

    /** 解析搜索结果条目（search-result-item 块） */
    private List<Vod> parseSearchList(String html) {
        List<Vod> items = new ArrayList<>();
        if (html == null || html.isEmpty()) return items;
        Matcher m = SEARCH_ITEM_PAT.matcher(html);
        while (m.find()) {
            try {
                String id = m.group(1);
                String block = m.group(2);
                String pic = "";
                Matcher pm = PIC_PAT.matcher(block);
                if (pm.find()) pic = fullPic(pm.group(1));
                String title = "";
                Matcher tm = SEARCH_TITLE_PAT.matcher(block);
                if (tm.find()) title = tm.group(1).trim();
                if (title.isEmpty()) continue;
                items.add(new Vod(id, title, pic, ""));
            } catch (Exception ignored) {
            }
        }
        return items;
    }

    /** 抓最新搜索签名 t（每次从首页拿，不能跨页面复用） */
    private String fetchT() {
        try {
            String html = get(SITE + "/");
            if (html == null) return null;
            Matcher m = T_PAT.matcher(html);
            if (m.find()) {
                String t = m.group(1);
                Log.d("TV-KEKE", "t=" + t);
                return t;
            }
        } catch (Exception ignored) {
        }
        return null;
    }

    @Override
    public String categoryContent(String tid, String pg, boolean filter, HashMap<String, String> extend) {
        try {
            int pageNo = 1;
            try {
                pageNo = Integer.parseInt(pg);
            } catch (NumberFormatException ignored) {
            }
            String url = (pageNo <= 1)
                    ? SITE + "/show/" + tid + "------.html"
                    : SITE + "/show/" + tid + "-----3-" + pageNo + ".html";
            String html = get(url);
            if (html == null) return Result.error("分类为空");
            List<Vod> items = parseList(html);
            Log.d("TV-KEKE", "cat " + url + " items=" + items.size());
            // 总页数：有"下一页"则至少 pageNo+1，否则当前页
            int pageTotal = pageNo;
            Matcher nm = NEXT_PAGE_PAT.matcher(html);
            if (nm.find()) {
                try {
                    int next = Integer.parseInt(nm.group(1));
                    if (next > pageTotal) pageTotal = next;
                } catch (NumberFormatException ignored) {
                }
            }
            if (items.size() < 18 && pageNo > 1) pageTotal = pageNo;
            return Result.get().vod(items).page(pageNo, pageTotal, 18, items.size()).string();
        } catch (Exception e) {
            return Result.error("分类失败: " + e.getMessage());
        }
    }

    @Override
    public String searchContent(String key, boolean quick, String pg) {
        try {
            if (!"1".equals(pg)) {
                return Result.get().vod(new ArrayList<Vod>()).page(2, 1, 18, 0).string();
            }
            String t = fetchT();
            if (t == null) return Result.error("搜索签名获取失败");
            String url = SITE + "/search?k=" + java.net.URLEncoder.encode(key, "UTF-8") + "&t=" + t;
            String html = get(url);
            List<Vod> items = parseSearchList(html);
            if (items.isEmpty()) items = parseList(html);
            Log.d("TV-KEKE", "search " + key + " items=" + items.size());
            return Result.get().vod(items).page(1, 1, items.size(), items.size()).string();
        } catch (Exception e) {
            return Result.error("搜索失败: " + e.getMessage());
        }
    }

    @Override
    public String searchContent(String key, boolean quick) {
        return searchContent(key, quick, "1");
    }

    @Override
    public String detailContent(List<String> ids) {
        try {
            String id = ids.get(0);
            String url = SITE + "/detail/" + id + ".html";
            String html = get(url);
            if (html == null) return Result.error("详情为空");

            String name = "";
            Matcher dm0 = DET_TITLE_PAT.matcher(html);
            if (dm0.find()) {
                Matcher sm = STRONG_PAT.matcher(dm0.group(1));
                int idx = 0;
                while (sm.find()) {
                    idx++;
                    if (idx == 2) {
                        name = sm.group(1).trim();
                        break;
                    }
                }
            }

            String pic = "";
            Matcher pm = PIC_PAT.matcher(html);
            if (pm.find()) pic = fullPic(pm.group(1));

            String director = "";
            String actor = "";
            String year = "";
            String desc = "";
            Matcher dm = DESC_PAT.matcher(html);
            if (dm.find()) desc = cleanText(dm.group(1));
            Matcher im = INFO_ROW_PAT.matcher(html);
            while (im.find()) {
                String label = im.group(1).trim();
                String val = cleanText(im.group(2));
                if (val.isEmpty()) continue;
                if (label.contains("导演") && director.isEmpty()) director = val;
                else if (label.contains("演员") && actor.isEmpty()) actor = val;
                else if (label.contains("首映") && year.isEmpty()) year = val;
            }

            Vod vod = new Vod(id, name, pic, "");
            vod.setVodDirector(director);
            vod.setVodActor(actor);
            vod.setVodYear(year);
            vod.setVodContent(desc);

            // 线路名（source-item 顺序）
            List<String> lineNames = new ArrayList<>();
            Matcher lm = LINE_PAT.matcher(html);
            while (lm.find()) lineNames.add(lm.group(1).trim());
            if (lineNames.isEmpty()) lineNames.add("线路1");

            // 集数块（episode-list 顺序，与线路一一对应）
            List<String> panelEps = new ArrayList<>();
            Matcher pm2 = EP_LIST_PAT.matcher(html);
            while (pm2.find()) panelEps.add(pm2.group(1));
            // 修正：episode-list 每个块结束于 </div></div>，若 HTML 结构特殊则整页回退
            if (panelEps.isEmpty()) {
                int a = html.indexOf("<div class=\"episode-list\"");
                if (a >= 0) panelEps.add(html.substring(a));
            }

            StringBuilder fromSb = new StringBuilder();
            StringBuilder urlSb = new StringBuilder();
            int lineCount = Math.min(lineNames.size(), panelEps.size());
            if (lineCount == 0 && !panelEps.isEmpty()) lineCount = 1;
            for (int i = 0; i < lineCount; i++) {
                String lineName = (i < lineNames.size()) ? lineNames.get(i) : ("线路" + (i + 1));
                String panel = panelEps.get(i);
                StringBuilder eps = new StringBuilder();
                Matcher em = EP_PAT.matcher(panel);
                while (em.find()) {
                    String epText = em.group(3).trim();
                    String epUrl = SITE + "/play/" + id + "-" + em.group(1) + "-" + em.group(2) + ".html";
                    if (eps.length() > 0) eps.append("#");
                    eps.append(epText).append("$").append(epUrl);
                }
                if (eps.length() == 0) continue;
                if (fromSb.length() > 0) fromSb.append("$$$");
                if (urlSb.length() > 0) urlSb.append("$$$");
                fromSb.append(lineName);
                urlSb.append(eps);
            }
            vod.setVodPlayFrom(fromSb.toString());
            vod.setVodPlayUrl(urlSb.toString());
            return Result.string(vod);
        } catch (Exception e) {
            return Result.error("详情失败: " + e.getMessage());
        }
    }

    @Override
    public String playerContent(String flag, String id, List<String> vipFlags) {
        try {
            String html = get(id);
            if (html == null) return Result.error("播放页为空");
            Matcher m = M3U8_PAT.matcher(html);
            String m3u8 = null;
            while (m.find()) {
                String cand = m.group(1).trim();
                if (cand.startsWith("http") && (cand.contains(".m3u8") || cand.endsWith(".mp4"))) {
                    m3u8 = cand;
                    break;
                }
            }
            if (m3u8 == null) {
                Matcher m2 = M3U8_PAT.matcher(html);
                if (m2.find()) m3u8 = m2.group(1).trim();
            }
            if (m3u8 == null) return Result.error("播放地址解析失败");

            JSONObject result = new JSONObject();
            result.put("parse", 0);
            result.put("jx", 0);
            result.put("url", m3u8);
            JSONObject header = new JSONObject();
            header.put("User-Agent", UA);
            header.put("Referer", SITE + "/");
            result.put("header", header);
            return result.toString();
        } catch (Exception e) {
            return Result.error("播放失败: " + e.getMessage());
        }
    }
}

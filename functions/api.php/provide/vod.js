// 大师兄影视 API - Cloudflare Pages Functions 版本
// 部署后接口地址: https://zhouyu86-bh1.pages.dev/api.php/provide/vod

const BASE_URL = "https://www.lzhuanqiu.com";
const HEADERS = {
  "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
  "Referer": BASE_URL + "/"
};

const CATEGORIES = {
  "1": ["dianyingpian", "电影片"],
  "2": ["lianxuju", "连续剧"],
  "3": ["zongyipian", "综艺片"],
  "4": ["dongmanpian", "动漫片"],
  "5": ["dianyingjieshu", "电影解说"],
  "6": ["duanju1", "短剧"]
};

async function fetchHtml(url, options) {
  try {
    const r = await fetch(url, { headers: HEADERS, ...options });
    return await r.text();
  } catch (e) {
    return "";
  }
}

function decodeHtml(s) {
  if (!s) return "";
  return s.replace(/&#(\d+);/g, (m, n) => String.fromCharCode(parseInt(n)));
}

function parseList(html) {
  const items = [];
  const blocks = html.match(/<li[^>]*>[\s\S]*?<\/li>/g) || [];
  for (const block of blocks) {
    const urlM = block.match(/href="(https?:\/\/www\.lzhuanqiu\.com\/q\/[^"]*)"/);
    if (!urlM) continue;
    const url = urlM[1];
    const vodId = url.replace(/\/$/, "").split("/").pop();
    const picM = block.match(/data-original="([^"]*)"/);
    const pic = picM ? picM[1] : "";
    let titleM = block.match(/class="biaoti"[^>]*>[\s\S]*?<a[^>]*>([^<]*)<\/a>/);
    if (!titleM) titleM = block.match(/title="([^"]*)"/);
    const title = titleM ? decodeHtml(titleM[1]) : vodId;
    const remarkM = block.match(/<span>([^<]*)<\/span>/);
    const remark = remarkM ? decodeHtml(remarkM[1]) : "";
    items.push({
      vod_id: vodId,
      vod_name: title,
      vod_pic: pic,
      vod_remarks: remark
    });
  }
  return items;
}

async function getCategoryList(tid, pg) {
  const cat = CATEGORIES[tid] || CATEGORIES["1"];
  const slug = cat[0];
  const url = pg == 1 ? `${BASE_URL}/${slug}/` : `${BASE_URL}/${slug}/p${pg}/`;
  const html = await fetchHtml(url);
  const items = parseList(html);
  let pagecount = 1;
  const pages = html.match(new RegExp(`/${slug}/p(\\d+)/`, "g"));
  if (pages) {
    const nums = pages.map(p => parseInt(p.match(/p(\d+)/)[1]));
    pagecount = Math.max(...nums);
  }
  return { items, pagecount };
}

async function getDetail(vodId) {
  const url = `${BASE_URL}/q/${vodId}/`;
  const html = await fetchHtml(url);
  
  let title = vodId;
  const titleM = html.match(/property="og:title" content="([^"]*)"/);
  if (titleM) {
    title = titleM[1];
    const bookM = title.match(/《([^》]*)》/);
    if (bookM) title = bookM[1];
    else title = title.replace(/[_\-].*$/, "");
  }
  title = decodeHtml(title);
  
  let pic = "";
  const picM = html.match(/property="og:image" content="([^"]*)"/);
  if (picM) pic = picM[1];
  
  let desc = "";
  const descM = html.match(/property="og:description" content="([^"]*)"/);
  if (descM) desc = decodeHtml(descM[1]);
  
  let actor = "";
  const actorM = html.match(/property="og:video:actor" content="([^"]*)"/);
  if (actorM) actor = decodeHtml(actorM[1]);
  
  let director = "";
  const directorM = html.match(/property="og:video:director" content="([^"]*)"/);
  if (directorM) director = decodeHtml(directorM[1]);
  
  // 解析播放源
  const playFromList = [];
  const playUrlList = [];
  const boxBlocks = html.split(/<div[^>]*class="box"[^>]*>/);
  for (let i = 1; i < boxBlocks.length; i++) {
    const block = boxBlocks[i];
    const nameM = block.match(/<b>([^<]*)<\/b>/);
    if (!nameM) continue;
    const sourceName = decodeHtml(nameM[1].trim());
    const bofangM = block.match(/<div class="bofang">([\s\S]*?)<\/div>/);
    if (!bofangM) continue;
    const episodes = [];
    const epRegex = /<a[^>]*title="([^"]*)"[^>]*href="([^"]*)"[^>]*>/g;
    let em;
    while ((em = epRegex.exec(bofangM[1])) !== null) {
      let epTitle = decodeHtml(em[1]);
      let epUrl = em[2];
      if (epUrl.startsWith("/")) epUrl = BASE_URL + epUrl;
      episodes.push(`${epTitle}$${epUrl}`);
    }
    if (episodes.length > 0) {
      episodes.reverse();
      playFromList.push(sourceName);
      playUrlList.push(episodes.join("#"));
    }
  }
  
  const vodPlayFrom = playFromList.join("$$$");
  const vodPlayUrl = playUrlList.join("$$$");
  
  let vodYear = "";
  const yearM = desc.match(/(\d{4})年/);
  if (yearM) vodYear = yearM[1];
  
  return {
    vod_id: vodId,
    vod_name: title,
    vod_pic: pic,
    vod_year: vodYear,
    vod_area: "",
    vod_lang: "",
    vod_content: desc,
    vod_actor: actor,
    vod_director: director,
    vod_play_from: vodPlayFrom,
    vod_play_url: vodPlayUrl
  };
}

async function getPlayUrl(playPageUrl) {
  const html = await fetchHtml(playPageUrl);
  const m = html.match(/url:\s*['"]([^'"]+\.m3u8[^'"]*)['"]/);
  if (m) return m[1];
  const m2 = html.match(/https?:\/\/[^\s"'<>]+\.m3u8[^\s"'<>]*/);
  if (m2) return m2[0];
  return "";
}

async function search(wd) {
  try {
    const formData = new URLSearchParams();
    formData.append("search_key", wd);
    formData.append("search_leixing", "影片");
    
    const r = await fetch(`${BASE_URL}/cgi/search`, {
      method: "POST",
      headers: { ...HEADERS, "Content-Type": "application/x-www-form-urlencoded" },
      body: formData.toString(),
      redirect: "follow"
    });
    const html = await r.text();
    return parseList(html);
  } catch (e) {
    return [];
  }
}

function jsonResponse(data) {
  return new Response(JSON.stringify(data), {
    headers: {
      "Content-Type": "application/json; charset=utf-8",
      "Access-Control-Allow-Origin": "*"
    }
  });
}

export async function onRequest(context) {
  const { request } = context;
  const url = new URL(request.url);
  const params = url.searchParams;
  
  // 播放解析接口
  if (params.has("play")) {
    const playUrl = params.get("play");
    const m3u8 = await getPlayUrl(playUrl);
    return jsonResponse({ url: m3u8, parse: 0 });
  }
  
  // 搜索接口
  if (params.has("wd")) {
    const wd = params.get("wd");
    const items = await search(wd);
    return jsonResponse({ list: items });
  }
  
  const ac = params.get("ac") || "list";
  
  if (ac === "list") {
    const classes = Object.entries(CATEGORIES).map(([k, v]) => ({
      type_id: k,
      type_name: v[1]
    }));
    return jsonResponse({ class: classes });
  }
  
  if (ac === "detail") {
    const t = params.get("t") || "1";
    const pg = parseInt(params.get("pg") || "1");
    const ids = params.get("ids") || "";
    
    if (ids) {
      const vod = await getDetail(ids);
      return jsonResponse({ list: [vod] });
    } else {
      const { items, pagecount } = await getCategoryList(t, pg);
      return jsonResponse({
        page: pg,
        pagecount: pagecount,
        list: items
      });
    }
  }
  
  // 默认返回分类
  const classes = Object.entries(CATEGORIES).map(([k, v]) => ({
    type_id: k,
    type_name: v[1]
  }));
  return jsonResponse({ class: classes });
}

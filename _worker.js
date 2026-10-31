// 可可影视代理 - Cloudflare Pages _worker.js
// 部署后: https://zhouyu86-bh1.pages.dev/keke/xxx  =>  https://www.keke2.app/xxx
// 云端抓取绕过本地网络 420 风控
export default {
  async fetch(request) {
    const url = new URL(request.url);
    const path = url.pathname;

    // 只处理 /keke/ 前缀
    if (!path.startsWith('/keke/')) {
      return new Response('keke proxy: use /keke/<path>', { status: 404 });
    }

    // 拼接目标 URL：/keke/ => https://www.keke2.app/
    let target = 'https://www.keke2.app/' + path.slice('/keke/'.length);
    if (url.search) target += url.search;

    const headers = {
      'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
      'Referer': 'https://www.keke2.app/',
      'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
      'Accept-Language': 'zh-CN,zh;q=0.9',
      'Upgrade-Insecure-Requests': '1',
      'Cookie': 'cdndefend_js_cookie=26F4497D23979FF11C34B67261D2FEF78DC78DA452882'
    };

    try {
      const resp = await fetch(target, { headers, redirect: 'follow' });
      const body = await resp.text();

      // 重写响应里的站点 URL：www.keke2.app -> 当前代理域名/keke
      const host = url.origin;
      const rewritten = body
        .replace(/https:\/\/www\.keke2\.app\//g, host + '/keke/')
        .replace(/https:\/\/keke2\.app\//g, host + '/keke/')
        .replace(/\/\/keke2\.app\//g, host + '/keke/');

      return new Response(rewritten, {
        status: resp.status,
        headers: {
          'Content-Type': resp.headers.get('Content-Type') || 'text/html; charset=utf-8',
          'Cache-Control': 'no-store'
        }
      });
    } catch (e) {
      return new Response('keke proxy error: ' + e.message, { status: 502 });
    }
  }
};

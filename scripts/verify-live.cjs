/* Run from the normal Mac terminal: node scripts/verify-live.cjs */
const fs = require('fs');
const path = require('path');
const assert = require('node:assert/strict');
let playwright;
try { playwright = require('playwright'); } catch {
  const cache = path.join(process.env.HOME, '.npm', '_npx');
  for (const name of fs.existsSync(cache) ? fs.readdirSync(cache) : []) {
    const pkg = path.join(cache, name, 'node_modules', 'playwright');
    if (fs.existsSync(pkg)) { playwright = require(pkg); break; }
  }
}
if (!playwright) throw new Error('Playwright missing. Install with npm install --no-save playwright, then npx playwright install chromium.');
const BASE = process.env.ALLALARM_VERIFY_BASE || 'https://cyber.allalarm.app';
(async () => {
  const browser = await playwright.chromium.launch({headless:true});
  try {
    const context = await browser.newContext();
    const page = await context.newPage();
    const errors = []; page.on('pageerror', e => errors.push(e.message));
    const response = await page.goto(BASE+'/', {waitUntil:'networkidle'});
    assert.equal(response.status(),200);
    const canonicalBase = 'https://cyber.allalarm.app';
    const policy = await page.locator('meta[http-equiv="Content-Security-Policy"]').getAttribute('content');
    assert.match(policy, /worker-src 'self'/);
    assert.match(policy, /manifest-src 'self'/);
    assert.equal(await page.locator('link[rel="canonical"]').getAttribute('href'),canonicalBase+'/');
    assert.equal(await page.locator('meta[name="twitter:card"]').getAttribute('content'),'summary_large_image');
    assert.equal(await page.locator('meta[property="og:image"]').getAttribute('content'),canonicalBase+'/assets/social-card.png');
    const history = await context.newPage();
    await history.goto(BASE+'/updates/', {waitUntil:'networkidle'});
    const commitLinks = history.locator('.history-entry a[href^="https://github.com/konaito/hacker-news/commit/"]');
    assert(await commitLinks.count() > 0);
    if (process.env.ALLALARM_EXPECT_COMMIT)
      assert.equal(await commitLinks.first().getAttribute('href'), 'https://github.com/konaito/hacker-news/commit/'+process.env.ALLALARM_EXPECT_COMMIT);
    await history.setViewportSize({width:390,height:844});
    assert.equal(await history.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
    await history.close();
    assert.equal(await page.locator('.reading-card').count(),2);
    for (const url of ['https://qiita.com/konaito/items/16a6d2c5da7d144efe95','https://note.com/konaito/n/n7afe40a9a1e8'])
      assert.equal(await page.locator(`.reading-card[href="${url}"]`).count(),1);
    const checked = await page.evaluate(async base => {
      const get = async url => { const r=await fetch(url,{cache:'no-store'});if(!r.ok)throw Error(url+' HTTP '+r.status);return r; };
      const parser=new DOMParser();
      const sitemap=parser.parseFromString(await (await get('/sitemap.xml')).text(),'application/xml');
      if(sitemap.querySelector('parsererror'))throw Error('Invalid sitemap');
      const urls=[...sitemap.querySelectorAll('loc')].map(n=>n.textContent);
      for(const url of urls){
        if(new URL(url).origin!==base)throw Error('Wrong sitemap origin');
        const doc=parser.parseFromString(await (await get(new URL(url).pathname)).text(),'text/html');
        if(doc.querySelector('link[rel="canonical"]')?.getAttribute('href')!==url)throw Error('Wrong canonical '+url);
        if(doc.querySelector('meta[name="twitter:card"]')?.content!=='summary_large_image')throw Error('Missing card '+url);
        for(const ld of doc.querySelectorAll('script[type="application/ld+json"]'))JSON.parse(ld.textContent);
      }
      const manifest=await (await get('/manifest.webmanifest')).json();
      if(manifest.display!=='standalone'||manifest.scope!=='/')throw Error('Manifest invalid');
      for(const icon of manifest.icons){const b=await(await get(icon.src)).arrayBuffer();const v=new DataView(b);if(`${v.getUint32(16)}x${v.getUint32(20)}`!==icon.sizes)throw Error('Icon dimensions');}
      const b=await(await get('/assets/social-card.png')).arrayBuffer();const v=new DataView(b);if(v.getUint32(16)!==1200||v.getUint32(20)!==630)throw Error('Social image dimensions');
      for(const asset of ['/favicon.ico','/icons/app/apple-touch-icon.png','/offline.html','/feed.xml','/robots.txt'])await get(asset);
      const feed=parser.parseFromString(await(await get('/feed.xml')).text(),'application/xml');if(feed.querySelector('parsererror'))throw Error('Invalid RSS');
      await get('/sw.js');
      if(!await(await get('/pwa.js')).text().then(t=>t.includes("updateViaCache: 'none'")))throw Error('Worker update cache bypass');
      if(!await(await get('/robots.txt')).text().then(t=>t.includes('Sitemap: '+base+'/sitemap.xml')))throw Error('Robots sitemap');
      return urls.length;
    }, canonicalBase);
    await page.locator('#search').fill('Gyazo');
    assert.equal(await page.locator('#news-rows tr:visible').count(),1);
    await page.locator('.org-button:visible').click();assert(await page.locator('#detail-dialog').isVisible());
    await page.keyboard.press('Escape');await page.locator('#search').fill('');
    await page.setViewportSize({width:390,height:844});
    assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
    await page.evaluate(async()=>{await Promise.race([navigator.serviceWorker.ready,new Promise((_,reject)=>setTimeout(()=>reject(Error("Service worker activation timed out")),60000))]);});
    await page.reload({waitUntil:'networkidle'});
    assert(await page.evaluate(()=>!!navigator.serviceWorker.controller));
    await context.setOffline(true);
    await page.reload({waitUntil:'domcontentloaded'});
    assert(await page.locator('.offline-status').isVisible());
    await page.goto(BASE+'/unvisited-offline-check/',{waitUntil:'domcontentloaded'});
    assert.equal(await page.locator('h1').textContent(),'接続できません');
    assert.deepEqual(errors,[]);
    console.log(`PASS production: ${checked} pages; SEO, cards, icons, RSS, CSP, search/dialog, mobile, service worker and offline fallback`);
  } finally { await browser.close(); }
})().catch(e=>{console.error(e);process.exitCode=1;});

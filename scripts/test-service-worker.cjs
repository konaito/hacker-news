const vm = require('node:vm');
const fs = require('node:fs');
const assert = require('node:assert/strict');
const handlers = {}, data = new Map(), removed = [];
let connected = true, waits = [];
const cache = {
  addAll: async urls => urls.forEach(u => data.set('https://example.test'+u,new Response(u))),
  put: async (req,r) => data.set(typeof req === 'string' ? req : req.url,r)
};
const context = {
  self: {location:{origin:'https://example.test'},clients:{claim:async()=>{}},addEventListener:(t,h)=>handlers[t]=h},
  caches: {open:async()=>cache,keys:async()=>['allalarm-old','unrelated'],delete:async key=>removed.push(key),match:async req=>data.get(typeof req === 'string' ? 'https://example.test'+req : req.url)?.clone()},
  fetch: async()=>{if(!connected)throw Error('offline');return new Response('fresh');},
  URL,Response,Promise
};
vm.runInNewContext(fs.readFileSync('public/sw.js','utf8'),context);
(async()=>{
  handlers.install({waitUntil:p=>waits.push(p)});await Promise.all(waits);waits=[];
  handlers.activate({waitUntil:p=>waits.push(p)});await Promise.all(waits);assert.deepEqual(removed,['allalarm-old']);
  async function request(url,mode='navigate',method='GET') {
    let response;waits=[];
    handlers.fetch({request:{method,url,mode},waitUntil:p=>waits.push(p),respondWith:p=>response=p});
    if(!response)return undefined;
    const result=await response;await Promise.all(waits);return result;
  }
  assert.equal(await (await request('https://example.test/news/visited/')).text(),'fresh');
  assert.equal(await request('https://other.test/'),undefined);
  assert.equal(await request('https://example.test/','navigate','POST'),undefined);
  connected=false;
  assert.equal(await (await request('https://example.test/news/visited/')).text(),'fresh');
  assert.equal(await (await request('https://example.test/news/missing/')).text(),'/offline.html');
  assert.equal((await request('https://example.test/missing.png','no-cors')).type,'error');
  console.log('PASS service worker: precache, own-cache cleanup, fresh/cached navigation, offline fallback, failed assets, cross-origin and POST bypass');
})().catch(e=>{console.error(e);process.exitCode=1;});

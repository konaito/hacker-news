"""Validate generated SEO metadata, crawlable pages and install assets."""
import json,re,struct
from pathlib import Path
from html.parser import HTMLParser
import xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'public'
class Head(HTMLParser):
    def __init__(self):super().__init__();self.meta={};self.links={};self.ld=[];self.capture=False;self.buffer='';self.headings=0
    def handle_starttag(self,t,attrs):
        a=dict(attrs)
        if t=='meta':self.meta[a.get('name',a.get('property'))]=a.get('content')
        if t=='link':self.links.setdefault(a.get('rel'),[]).append(a.get('href'))
        if t=='h1':self.headings+=1
        if t=='script' and a.get('type')=='application/ld+json':self.capture=True;self.buffer=''
    def handle_data(self,d):
        if self.capture:self.buffer+=d
    def handle_endtag(self,t):
        if t=='script' and self.capture:self.ld.append(json.loads(self.buffer));self.capture=False
records=json.loads((ROOT/'data/incidents.json').read_text())
pages=[OUT/'index.html']+list((OUT/'news').glob('*/index.html'))+list((OUT/'archive').glob('*/index.html'))
urls=set()
for page in pages:
    p=Head();p.feed(page.read_text())
    assert len(p.links['canonical'])==1;url=p.links['canonical'][0];assert url not in urls;urls.add(url)
    assert url.startswith('https://hackernews.allalarm.app/')
    assert p.headings==1, f'H1 count: {page}'
    assert p.meta['description'] and p.meta['twitter:card']=='summary_large_image'
    assert p.meta['og:url']==url and p.meta['og:image']==p.meta['twitter:image']
    assert p.links['manifest']==['/manifest.webmanifest'] and p.ld
    assert 'noindex' not in p.meta['robots']
for r in records:assert (OUT/'news'/r['id']/'index.html').exists()==(r['publication_status']=='published')
sitemap=ET.parse(OUT/'sitemap.xml');locs={n.text for n in sitemap.findall('.//{http://www.sitemaps.org/schemas/sitemap/0.9}loc')};assert urls==locs
ET.parse(OUT/'feed.xml')
m=json.loads((OUT/'manifest.webmanifest').read_text());assert m['scope']=='/' and m['display']=='standalone' and m['start_url']=='/'
for i in m['icons']:
    p=OUT/i['src'].lstrip('/');data=p.read_bytes();assert data[:8]==b'\x89PNG\r\n\x1a\n';w,h=struct.unpack('>II',data[16:24]);assert f'{w}x{h}'==i['sizes']
assert {i['purpose'] for i in m['icons']}=={'any','maskable'}
data=(OUT/'assets/social-card.png').read_bytes();assert struct.unpack('>II',data[16:24])==(1200,630)
sw=(OUT/'sw.js').read_text();assert '__VERSION__' not in sw
for asset in re.findall(r"'(/[^']+)'",sw.split('self.addEventListener')[0]):assert (OUT/asset.lstrip('/')).exists()
assert (OUT/'favicon.ico').exists() and (OUT/'icons/app/apple-touch-icon.png').exists()
print(f'SEO/PWA passed: {len(pages)} canonical pages, sitemap, RSS, JSON-LD, cards, icons and cache assets')

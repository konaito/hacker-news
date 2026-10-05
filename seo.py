"""Generate crawlable article/archive pages, social metadata and PWA assets."""
import json,re,hashlib
from html import escape
from pathlib import Path
from xml.sax.saxutils import escape as xml_escape
from updates import load_history, render_entry
BASE='https://hackernews.allalarm.app'
NAME='ALLALARM CYBER JOURNAL'
DESCRIPTION='国内・海外のハッキング、情報漏洩、ランサムウェアの主要ニュースを出典付きで整理。確認状況、被害規模、公表日から検索できます。'
def metadata(title,description,url,kind='website'):
    values={'description':description,'robots':'index,follow,max-image-preview:large','twitter:card':'summary_large_image','twitter:title':title,'twitter:description':description,'twitter:image':BASE+'/assets/social-card.png','twitter:image:alt':'ALLALARM CYBER JOURNAL — ハッキング・情報漏洩ニュース'}
    tags=''.join(f'<meta name="{k}" content="{escape(v,quote=True)}">' for k,v in values.items())
    og={'og:type':kind,'og:locale':'ja_JP','og:site_name':NAME,'og:title':title,'og:description':description,'og:url':url,'og:image':BASE+'/assets/social-card.png','og:image:width':'1200','og:image:height':'630','og:image:type':'image/png','og:image:alt':values['twitter:image:alt']}
    tags+=''.join(f'<meta property="{k}" content="{escape(v,quote=True)}">' for k,v in og.items())
    return tags+f'<link rel="canonical" href="{escape(url,quote=True)}"><link rel="icon" href="/favicon.ico" sizes="any"><link rel="icon" type="image/png" sizes="48x48" href="/icons/app/favicon-48.png"><link rel="apple-touch-icon" sizes="180x180" href="/icons/app/apple-touch-icon.png"><link rel="manifest" href="/manifest.webmanifest"><meta name="theme-color" content="#0b3670"><meta name="apple-mobile-web-app-capable" content="yes"><meta name="apple-mobile-web-app-title" content="ALLALARM"><link rel="alternate" type="application/rss+xml" title="ALLALARM 新着ニュース" href="/feed.xml">'
def ld(value):return '<script type="application/ld+json">'+json.dumps(value,ensure_ascii=False).replace('<','\\u003c')+'</script>'
def enhance(root,page,records,cutoff):
    out=root/'public'; urls=[(BASE+'/',cutoff)]
    history = load_history(root)
    published_ids = {r['id'] for r in records}
    preview = '<section class="side-panel history-preview" aria-labelledby="history-heading"><h2 id="history-heading">更新履歴</h2><ol class="history-list">' + ''.join(render_entry(entry, published_ids, details=False) for entry in history[:3]) + '</ol><a href="/updates/">すべての更新履歴を見る</a></section>'
    page = page.replace('<aside class="sidebar" aria-label="ニュースの補足">', '<aside class="sidebar" aria-label="ニュースの補足">' + preview)
    page = page.replace('<nav aria-label="フッターナビゲーション">', '<nav aria-label="フッターナビゲーション"><a href="/updates/">更新履歴</a>')
    page=re.sub(r'<meta (?:name="(?:description|theme-color)"|property="og:[^"]+") [^>]*>','',page)
    page=re.sub(r'<link rel="(?:canonical|icon)"[^>]*>','',page)
    page=page.replace('</head>',metadata(NAME+'｜ハッキング・情報漏洩ニュース',DESCRIPTION,BASE+'/')+ld({'@context':'https://schema.org','@graph':[{'@type':'Organization','@id':BASE+'/#organization','name':NAME,'url':BASE+'/','logo':BASE+'/icons/app/icon-512.png'},{'@type':'WebSite','@id':BASE+'/#website','name':NAME,'url':BASE+'/','inLanguage':'ja','publisher':{'@id':BASE+'/#organization'}},{'@type':'CollectionPage','name':NAME,'url':BASE+'/','description':DESCRIPTION,'inLanguage':'ja','mainEntity':{'@type':'ItemList','itemListElement':[{'@type':'ListItem','position':i+1,'url':BASE+'/news/'+r['id']+'/','name':r['title']} for i,r in enumerate(records)]}}]})+'</head>')
    def anchor(m):
        attrs=m[1]; rid=re.search(r'data-detail="([^"]+)"',attrs)[1]
        return '<a'+attrs+' href="/news/'+rid+'/">'+m[2]+'</a>'
    page=re.sub(r'<button([^>]*data-detail="[^"]+"[^>]*)>(.*?)</button>',anchor,page,flags=re.S)
    page=page.replace('</body>','<script src="/pwa.js" defer></script></body>')
    def shell(title,desc,url,body,structured,kind='website'):
        return '<!doctype html><html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+escape(title)+'</title>'+metadata(title,desc,url,kind)+ld(structured)+'<link rel="stylesheet" href="/style.css"><script src="/pwa.js" defer></script></head><body><header class="site-header"><div class="header-inner"><a class="brand" href="/"><strong>'+NAME+'</strong></a></div></header><main class="container article-page">'+body+'</main><footer class="site-footer"><div class="container"><a href="/">ニュース一覧に戻る</a> · <a href="/updates/">更新履歴</a> · <a href="/feed.xml">RSS</a></div></footer></body></html>'
    history_url = BASE + '/updates/'
    history_body = '<nav aria-label="パンくず"><a href="/">ホーム</a> / 更新履歴</nav><h1>更新履歴</h1><p>記事の追加・内容更新とサイトの変更を、記録日時の新しい順に掲載しています。日時は日本時間です。</p><p class="detail-note">過去の履歴は保存されたコミット差分から復元しています。今後の自動更新は調査完了時に記録します。事件の発生日・公表日やデプロイ完了時刻とは異なります。変更のなかった調査は履歴に含めません。</p><ol class="history-list">' + ''.join(render_entry(entry, published_ids) for entry in history) + '</ol>'
    history_dest = out / 'updates'
    history_dest.mkdir(exist_ok=True)
    history_dest.joinpath('index.html').write_text(shell('更新履歴｜' + NAME, '記事の追加・内容更新とサイトの変更履歴。日時は日本時間で表示します。', history_url, history_body, {'@context': 'https://schema.org', '@type': 'CollectionPage', 'name': '更新履歴', 'url': history_url}))
    history_date = history[0]['timestamp'] if history else cutoff
    urls[0] = (BASE + '/', max(cutoff, history_date))
    urls.append((history_url, history_date))
    actual={r['id']:r for r in json.loads((root/'data/incidents.json').read_text())}
    for r in records:
        url=BASE+'/news/'+r['id']+'/'
        modified=max(actual.get(r['id'],{}).get('last_verified_at',r['date']),actual.get(r['id'],{}).get('first_seen_at','2026-10-06'))
        urls.append((url,modified)); dest=out/'news'/r['id']; dest.mkdir(parents=True,exist_ok=True)
        links=''.join(f'<li><a href="{escape(u,quote=True)}" rel="noopener noreferrer" target="_blank">{escape(n)}</a></li>' for n,u in r['sources'])
        body=f'<nav aria-label="パンくず"><a href="/">ホーム</a> / ニュース</nav><article><p>{escape(r["org"])} · <time datetime="{r["date"]}">{r["date"]}</time></p><h1>{escape(r["title"])}</h1><p class="badge {r["kind"]}">{escape(r["label"])}</p>'
        body+=r.get('rich') or f'<p>{escape(r["body"])}</p><p>{escape(r["note"])}</p>'
        body+=f'<h2>出典</h2><ul>{links}</ul><p class="detail-note">公表・続報日：{r["date"]}。確認状況と被害規模は参照した発表時点の情報です。</p></article>'
        structured={'@context':'https://schema.org','@graph':[{'@type':'NewsArticle','headline':r['title'],'description':r['body'],'datePublished':actual.get(r['id'],{}).get('first_seen_at','2026-10-06'),'dateModified':max(modified,actual.get(r['id'],{}).get('first_seen_at','2026-10-06')),'inLanguage':'ja','mainEntityOfPage':url,'image':[BASE+'/assets/social-card.png'],'author':{'@type':'Organization','name':NAME,'url':BASE+'/'},'publisher':{'@id':BASE+'/#organization','@type':'Organization','name':NAME,'logo':{'@type':'ImageObject','url':BASE+'/icons/app/icon-512.png'}},'citation':[u for n,u in r['sources']]},{'@type':'BreadcrumbList','itemListElement':[{'@type':'ListItem','position':1,'name':'ホーム','item':BASE+'/'},{'@type':'ListItem','position':2,'name':r['title'],'item':url}]}]}
        dest.joinpath('index.html').write_text(shell(r['title']+'｜'+NAME,r['body'],url,body,structured,'article'))
    # Remove pages for candidates that are no longer published.
    allowed={r['id'] for r in records}
    for old in (out/'news').glob('*/index.html'):
        if old.parent.name not in allowed:old.unlink();old.parent.rmdir()
    for month in sorted({r['date'][:7] for r in records}):
        subset=[r for r in records if r['date'].startswith(month)];url=BASE+'/archive/'+month+'/'
        dest=out/'archive'/month;dest.mkdir(parents=True,exist_ok=True); title=month+'のハッキング・情報漏洩ニュース'
        body='<a href="/">ホーム</a><h1>'+title+'</h1><ul>'+''.join(f'<li><time>{r["date"]}</time> <a href="/news/{r["id"]}/">{escape(r["title"])}</a></li>' for r in subset)+'</ul>'
        dest.joinpath('index.html').write_text(shell(title+'｜'+NAME,DESCRIPTION,url,body,{'@context':'https://schema.org','@type':'CollectionPage','name':title,'url':url}))
        urls.append((url,max(r['date'] for r in subset)))
    active_months={r['date'][:7] for r in records}
    for old in (out/'archive').glob('*/index.html'):
        if old.parent.name not in active_months:old.unlink();old.parent.rmdir()
    page=page.replace('<h2>月別ダイジェスト</h2>','<h2>月別ダイジェスト</h2><p><a href="/feed.xml">RSSで新着を読む</a></p>')
    page=re.sub(r'<button class="text-button" data-month="([^"]+)">この月の事件を見る</button>',r'<a class="text-button" href="/archive/\1/">この月の事件を見る</a>',page)
    out.joinpath('index.html').write_text(page)
    out.joinpath('sitemap.xml').write_text('<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'+''.join(f'<url><loc>{xml_escape(u)}</loc><lastmod>{d}</lastmod></url>' for u,d in urls)+'</urlset>')
    out.joinpath('feed.xml').write_text('<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel><title>'+NAME+'</title><link>'+BASE+'/</link><description>'+xml_escape(DESCRIPTION)+'</description><language>ja</language>'+''.join('<item><title>'+xml_escape(r['title'])+'</title><link>'+BASE+'/news/'+r['id']+'/</link><guid isPermaLink="true">'+BASE+'/news/'+r['id']+'/</guid><description>'+xml_escape(r['body'])+'</description></item>' for r in records)+'</channel></rss>')
    version=hashlib.sha256((page+history_dest.joinpath('index.html').read_text()+(out/'app.js').read_text()+(out/'style.css').read_text()+(out/'pwa.js').read_text()+(root/'service-worker.js').read_text()).encode()).hexdigest()[:16]
    out.joinpath('sw.js').write_text((root/'service-worker.js').read_text().replace('__VERSION__',version))

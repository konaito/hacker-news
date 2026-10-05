# -*- coding: utf-8 -*-
"""Build a static, source-grounded cybersecurity news dashboard."""
from pathlib import Path
from html import escape as e
import re

ROOT = Path(__file__).parent
OUT = ROOT / 'public'

def icon(name):
    return f'<svg class="icon" viewBox="0 0 24 24" aria-hidden="true"><use href="#icon-{name}"/></svg>'

symbols = []
for f in sorted((OUT / 'icons').glob('*.svg')):
    s = f.read_text()
    inside = s[s.index('>', s.index('<svg')) + 1:s.rindex('</svg>')]
    symbols.append(f'<symbol id="icon-{f.stem}" viewBox="0 0 24 24">{inside}</symbol>')
sprite = '<svg class="sprite" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">'+''.join(symbols)+'</svg>'

import json
from collections import Counter
incident_data = json.loads((ROOT/'data/incidents.json').read_text())
source_data = {s['id']: s for s in json.loads((ROOT/'data/sources.json').read_text())}
published = [r for r in incident_data if r['publication_status'] == 'published']
categories = sorted({r['category'] for r in published})
records = []
for r in published:
    records.append(dict(id=r['id'],date=r['published_at'],org=r['company'],title=r['title'],kind={'confirmed_leak':'confirmed','possible_leak':'possible','disruption':'disruption','confirmed_access':'confirmed'}[r['status']],label=r['display_label'],body=r['summary'],note=r['note'],sources=[(source_data[s]['title'],source_data[s]['url']) for s in r['sources']],category=r['category'],region='国内' if r['region']=='JP' else '海外'))
ai = re.findall(r'<article class="ai-report[^\"]*">.*?</article>', (ROOT/'ai-content.html').read_text(), flags=re.S)
for i,(date,title,summary) in enumerate([
    ('2026-09-10','AIが侵入から盗んだデータの処理まで使われる実例を報告','Anthropicが、AIを使う攻撃者の偵察・侵入・データ処理を報告。観測した悪用活動に関する調査です。'),
    ('2026-09-29','GLM-5.3の自律的な攻撃コード生成能力を警告','研究環境での評価に基づく事前警告。実際の大規模侵入を確認した事件報告とは区別します。')]):
    url='https://www.anthropic.com/threat-intelligence-report-september-2026' if i==0 else 'https://www.anthropic.com/research/glm-5-3-and-the-spread-of-advanced-cyber-capabilities'
    records.append(dict(id=f'ai-{i}',date=date,org='Anthropic / Frontier Red Team' if i else 'Anthropic / Threat Intelligence',title=title,kind='ai',label='能力の評価・警告' if i else '悪用活動の調査報告',body=summary,note='',sources=[('Anthropic｜一次レポート',url)],category='AI・セキュリティ',region='海外',rich=ai[i]))
records.sort(key=lambda r:r['date'],reverse=True)

def detail(r):
    if r.get('rich'):return r['rich']
    links=''.join(f'<a href="{e(u,quote=True)}" target="_blank" rel="noopener noreferrer">{e(n)}{icon("external-link")}</a>' for n,u in r['sources'])
    return f'<p class="dialog-org">{e(r["org"])}</p><h2>{e(r["title"])}</h2><div class="detail-meta"><time>{r["date"].replace("-",".")}</time><span class="badge {r["kind"]}">{e(r["label"])}</span><span>{r["region"]} / {r["category"]}</span></div><p>{e(r["body"])}</p><p class="detail-note">{e(r["note"])}</p><div class="sources"><strong>出典</strong>{links}</div><p class="source-date">記載内容は参照した発表・報道時点のものです。</p>'

def row(r):
    search=e(' '.join([r['org'],r['title'],r['body'],r['category']]),quote=True)
    return f'<tr data-id="{r["id"]}" data-kind="{r["kind"]}" data-region="{r["region"]}" data-category="{r["category"]}" data-date="{r["date"]}" data-search="{search}"><td class="date-cell"><time datetime="{r["date"]}">{r["date"][5:].replace("-",".")}</time><span>2026</span></td><th scope="row"><button class="org-button" data-detail="{r["id"]}">{e(r["org"])}</button></th><td><span class="badge {r["kind"]}">{e(r["label"])}</span></td><td class="summary-cell">{e(r["title"])}</td><td class="region-cell">{r["region"]}</td><td class="category-cell">{r["category"]}</td><td><a class="source-button" href="{e(r["sources"][0][1],quote=True)}" target="_blank" rel="noopener noreferrer" aria-label="{e(r["org"],quote=True)}の出典を開く">{icon("external-link")}</a></td></tr>'

cards=[]
for i,r in enumerate(records[:3]):
    new='<span class="new-label">LATEST</span>' if i==0 else ''
    cards.append(f'<article class="update-card"><div class="card-date">{new}<time datetime="{r["date"]}">{r["date"].replace("-",".")}</time></div><h3><button data-detail="{r["id"]}">{e(r["org"])}<span>{e(r["title"])}</span></button></h3><p>{e(r["body"])}</p><div class="card-tags"><span class="badge {r["kind"]}">{e(r["label"])}</span><span class="tag">{r["region"]}</span><span class="tag">{r["category"]}</span></div></article>')
counts = Counter(r['kind'] for r in records)
regions = Counter(r['region'] for r in records)
tab_specs=[('all','すべて',len(records)),('confirmed','漏洩・閲覧確認',counts['confirmed']),('possible','漏洩の可能性',counts['possible']),('disruption','業務障害',counts['disruption']),('ai','AI関連',counts['ai']),('国内','国内',regions['国内']),('海外','海外',regions['海外'])]
tabs=''.join(f'<button class="filter-tab {"active" if i==0 else ""}" data-filter="{v}" aria-pressed="{"true" if i==0 else "false"}">{n}<span>{c}</span></button>' for i,(v,n,c) in enumerate(tab_specs))
options=''.join(f'<option>{e(c)}</option>' for c in sorted(set(categories+['AI・セキュリティ'])))
templates=''.join(f'<template id="detail-{r["id"]}">{detail(r)}</template>' for r in records)
brand='<strong>ALLALARM <span>CYBER JOURNAL</span></strong><span class="brand-caption">ハッキング・情報漏洩の動向を読む</span>'

page='''<!doctype html><html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ALLALARM CYBER JOURNAL｜ハッキング・情報漏洩ニュースまとめ</title><meta name="description" content="2026年9月〜10月6日の国内・海外のハッキング、情報漏洩とAI関連ニュースを出典付きで整理。検索・絞り込みで主要事案を確認。"><link rel="canonical" href="https://hackernews.allalarm.app/"><meta name="theme-color" content="#0b3670"><meta property="og:type" content="website"><meta property="og:locale" content="ja_JP"><meta property="og:title" content="ALLALARM CYBER JOURNAL"><meta property="og:description" content="ハッキングと情報漏洩。この1か月に、何が起きたのか。"><meta property="og:url" content="https://hackernews.allalarm.app/"><link rel="icon" type="image/svg+xml" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' height='32' rx='7' fill='%231368cc'/%3E%3Cpath d='M9 23 16 8 23 23M12 18h8' fill='none' stroke='white' stroke-width='3'/%3E%3C/svg%3E"><link rel="stylesheet" href="/style.css"><link rel="preload" href="/fonts/LINESeedJP_OTF_Rg.woff2" as="font" type="font/woff2" crossorigin><script src="/app.js" defer></script></head><body id="top">''' + sprite + '''<a class="skip-link" href="#main">本文へ移動</a>
<header class="site-header"><div class="header-inner"><a class="brand" href="#top">''' + brand + '''</a><nav class="desktop-nav" aria-label="メインナビゲーション"><a class="selected" href="#updates">最新ニュース</a><a href="#incidents">インシデント一覧</a><a href="#analysis">AI関連</a><button data-about>このサイトについて</button></nav><form class="search-form" role="search"><label class="sr-only" for="search">ニュースを検索</label>''' + icon('search') + '''<input type="search" id="search" placeholder="ニュースを検索…" autocomplete="off"><button type="submit" aria-label="検索">''' + icon('search') + '''</button></form></div></header>
<main id="main" class="container"><div class="hero-layout"><section class="hero" aria-labelledby="hero-title"><div class="hero-copy"><div class="hero-kicker"><span>MONTHLY DIGEST</span><p>2026年9月〜10月のサイバーセキュリティ</p></div><h1 id="hero-title">ハッキングと情報漏洩。<br>この1か月に、<br class="small-break">何が起きたのか。</h1><p class="hero-summary">企業・団体の情報漏洩、ランサムウェア、AIを使う攻撃。<br>主要ニュースを整理し、被害と確認状況を出典付きで伝えます。</p><a class="primary-button" href="#incidents">主要インシデントを読む</a></div><div class="hero-image"><img src="/assets/cybersecurity-news.png" alt="サイバーセキュリティをテーマにした新聞と都市のイメージ" width="1774" height="887" fetchpriority="high"><span>イメージ画像</span></div></section><aside class="hero-aside"><p>正確な情報で、<br>より安全なデジタル社会へ。</p><div class="blue-rule"></div><span>情報基準日</span><time datetime="2026-10-06">2026年10月6日</time><small>対象期間：9月1日〜10月6日</small></aside></div>
<section class="metrics" aria-label="収録事案の概要">'''
for name,heading,value,note in [('shield-check','収録インシデント','<strong>15</strong><span>事案</span>','主要事案を選定・全件網羅ではありません'),('database','漏洩・不正閲覧を確認','<strong>7</strong><span>事案</span>','可能性のみの事案は含みません'),('globe','国内・海外の事案','<strong>12</strong><span>国内</span><b>/</b><strong>3</strong><span>海外</span>','別途、AI関連の2報告を収録'),('file-text','タイムズカーの本人確認書類','<span>約</span><strong>160万</strong>','漏洩したアカウント数')]:
    page+=f'<div class="metric"><span class="metric-icon">{icon(name)}</span><div><h2>{heading}</h2><p>{value}</p><small>{note}</small></div></div>'
page+='''</section><div class="dashboard-layout"><div class="main-column"><section id="updates"><div class="section-head"><h2>最新アップデート</h2><a href="#incidents">すべての収録ニュースを見る</a></div><div class="update-grid">''' + ''.join(cards) + '''</div></section><section id="incidents" class="incident-section"><div class="section-head"><h2>インシデント一覧</h2><button class="text-button" data-about>掲載基準について</button></div><p class="section-description">公表・続報の日付順に掲載。組織名を選ぶと、被害の詳細と出典を確認できます。</p><div class="filter-tabs" role="group" aria-label="ニュースの種類で絞り込み">''' + tabs + '''</div><div class="filter-controls"><div class="select-wrap"><label class="sr-only" for="month-filter">公表月</label><select id="month-filter"><option value="all">2026年9月〜10月</option><option value="2026-10">2026年10月</option><option value="2026-09">2026年9月</option></select>''' + icon('chevron-down') + '''</div><div class="select-wrap"><label class="sr-only" for="category-filter">カテゴリ</label><select id="category-filter"><option value="all">すべてのカテゴリ</option>''' + options + '''</select>''' + icon('chevron-down') + '''</div><div class="select-wrap"><label class="sr-only" for="region-filter">地域</label><select id="region-filter"><option value="all">すべての地域</option><option>国内</option><option>海外</option></select>''' + icon('chevron-down') + '''</div><div class="sort-control"><label for="sort">並び替え</label><div class="select-wrap"><select id="sort"><option value="desc">公表日（新しい順）</option><option value="asc">公表日（古い順）</option></select>''' + icon('chevron-down') + '''</div></div></div><div class="search-state" id="search-state" hidden><span></span><button id="clear-search">検索を解除</button></div><div class="table-scroll" role="region" aria-label="ニュース一覧" tabindex="0"><table class="news-table"><caption class="sr-only">ハッキング・情報漏洩ニュースとAI関連報告</caption><thead><tr><th scope="col">公表日</th><th scope="col">組織・サービス名</th><th scope="col">確認状況</th><th scope="col">概要</th><th scope="col">地域</th><th scope="col">カテゴリ</th><th scope="col">出典</th></tr></thead><tbody id="news-rows">''' + ''.join(row(r) for r in records) + '''</tbody></table></div><div id="empty-state" class="empty-state" hidden>''' + icon('search') + '''<h3>該当するニュースがありません</h3><p>検索語や絞り込み条件を変えてお試しください。</p><button id="reset-filters" class="outline-button">条件をリセット</button></div><div class="table-bottom"><button id="load-more" class="outline-button">''' + icon('chevron-down') + '''さらに読み込む</button><p id="result-count" aria-live="polite">17件中10件を表示</p><p class="table-note">日付は発生日ではなく公表・続報日です。AI関連報告は事件数に含めていません。</p></div><noscript><p>JavaScriptを有効にすると検索・絞り込みと詳細表示を利用できます。出典リンクはそのまま閲覧できます。</p></noscript></section></div><aside class="sidebar" aria-label="ニュースの補足"><section class="side-panel"><div class="side-title">''' + icon('calendar-days') + '''<h2>この期間の要点</h2></div><ul class="takeaways"><li>タイムズカーで本人確認書類の流出</li><li>Gyazoで大量のユーザー関連データが流出</li><li>京王グループで営業システムに障害</li><li>AIによる実際の悪用と能力の警告を公表</li></ul><div class="side-callout">''' + icon('info') + '''<p>「人」「アカウント」「データ件数」は別の単位です。被害人数として合算しません。</p></div></section><section class="side-panel"><div class="side-title">''' + icon('info') + '''<h2>掲載・更新のルール</h2></div><p>公式発表と報道をもとに、漏洩確認、漏洩の可能性、業務障害を区別しています。各事案の状態は参照した発表時点のものです。</p><button class="text-button" data-about>編集方針と出典について</button></section><section class="side-panel archive"><div class="side-title">''' + icon('calendar-days') + '''<h2>公表月から探す</h2></div><button data-month="2026-10"><span>2026年10月 <small>1日〜6日</small></span><strong>3件</strong></button><button data-month="2026-09"><span>2026年9月</span><strong>14件</strong></button><p>AI関連2報告を含む収録ニュースの件数</p></section><section class="side-panel analysis" id="analysis"><div class="side-title">''' + icon('chart-no-axes-combined') + '''<h2>AIとサイバー攻撃</h2></div><article><button data-detail="ai-0"><span class="analysis-icon">''' + icon('bot') + '''</span><span><strong>AIが変える攻撃の規模と速度</strong><time datetime="2026-09-10">2026.09.10</time><span>観測された悪用活動の報告を読む。</span></span></button></article><article><button data-detail="ai-1"><span class="analysis-icon dark">''' + icon('shield-check') + '''</span><span><strong>GLM-5.3の攻撃能力と安全対策</strong><time datetime="2026-09-29">2026.09.29</time><span>研究による能力評価と実害の区別。</span></span></button></article></section></aside></div></main><footer class="site-footer"><div class="footer-inner"><a class="brand" href="#top">''' + brand + '''</a><nav aria-label="フッターナビゲーション"><button data-about>このサイトについて</button><button data-about>編集方針・出典</button><a href="/fonts/OFL.txt">フォントライセンス</a><a href="/icons/LICENSE.txt">アイコンライセンス</a></nav><p>© 2026 ALLALARM CYBER JOURNAL</p><small>LINE Seed JP © LY Corporation · Lucide icons<br>Hacker News / Y Combinatorとは関係ありません。</small></div></footer><dialog id="detail-dialog" aria-labelledby="dialog-heading"><button class="dialog-close" aria-label="詳細を閉じる">''' + icon('x') + '''</button><div id="dialog-content"></div></dialog><template id="about-content"><p class="dialog-org">ALLALARM CYBER JOURNAL</p><h2>このサイトと編集方針</h2><p>2026年9月1日〜10月6日に公表・続報・報道された主要ニュースを整理した、独立したニュース要約サイトです。</p><h3>対象と情報の確認</h3><p>国内12事案、海外3事案とAI関連2報告を収録しています。すべての事件を網羅した件数ではなく、期間内に攻撃が始まった事案だけの一覧でもありません。</p><p>企業・機関の公式発表を優先し、報道に基づく事項は媒体名を記載しています。「漏洩確認」「不正閲覧確認」「漏洩の可能性」「業務障害」を区別し、各事案に出典を付けています。情報基準日は2026年10月6日です。自動更新は行っていません。</p><h3>数字と日付の読み方</h3><p>日付は公表・続報・報道の日です。初報と続報がある案件は最新の参照日で並べています。データ件数には同じ人の複数記録や匿名ユーザーが含まれるため、人数に換算したり合算したりしていません。</p><h3>AI関連の報告</h3><p>実際の悪用活動と研究環境での能力評価は別の区分です。掲載した国内事件をAIやGLM-5.3による攻撃と結びつける根拠は、参照した発表にはありません。</p><h3>デザインと使用素材</h3><p>フォントはLINEヤフーのLINE Seed JP（SIL Open Font License 1.1）、アイコンはLucideを使用しています。ヘッダーの写真はAI生成のイメージであり、特定の事件を撮影した写真ではありません。</p></template>''' + templates + '''</body></html>'''
cutoff = max([r['last_verified_at'] for r in published] or ['2026-09-01'])
incident_count = len(published)
page = page.replace('<strong>15</strong>', f'<strong>{incident_count}</strong>').replace('<strong>7</strong>', f'<strong>{counts["confirmed"]}</strong>').replace('<strong>12</strong>', f'<strong>{sum(r["region"]=="JP" for r in published)}</strong>').replace('<strong>3</strong><span>海外</span>', f'<strong>{sum(r["region"]!="JP" for r in published)}</strong><span>海外</span>')
page = page.replace('17件中10件を表示', f'{len(records)}件中{min(10,len(records))}件を表示')
page = page.replace('国内12事案、海外3事案', f'国内{sum(r["region"]=="JP" for r in published)}事案、海外{sum(r["region"]!="JP" for r in published)}事案')
page = page.replace('自動更新は行っていません。','一次情報を優先し、根拠が不足する候補は検証待ちとして公開対象から除外します。')
months = Counter(r['date'][:7] for r in records)
month_options = '<option value="all">すべての公表月</option>' + ''.join(f'<option value="{m}">{m[:4]}年{int(m[5:])}月</option>' for m in sorted(months,reverse=True))
page = re.sub(r'(<select id="month-filter">).*?(</select>)',lambda m:m[1]+month_options+m[2],page)
archive = ''.join(f'<button data-month="{m}"><span>{m[:4]}年{int(m[5:])}月</span><strong>{n}件</strong></button>' for m,n in sorted(months.items(),reverse=True))
page = re.sub(r'<button data-month="2026-10">.*?<p>AI関連2報告',archive+'<p>AI関連2報告',page,flags=re.S)
page = page.replace('2026-10-06',cutoff).replace('2026年10月6日',f'{cutoff[:4]}年{int(cutoff[5:7])}月{int(cutoff[8:])}日')
digests = json.loads((ROOT/'data/monthly-digests.json').read_text())
digest_html = '<section class="side-panel"><div class="side-title"><h2>月別ダイジェスト</h2></div>' + ''.join(f'<article><h3>{e(d["title"])}</h3><p>{e(d["summary"])}</p><button class="text-button" data-month="{e(d["month"],quote=True)}">この月の事件を見る</button></article>' for d in sorted(digests,key=lambda d:d['month'],reverse=True)) + '</section>'
page = page.replace('<section class="side-panel analysis"',digest_html+'<section class="side-panel analysis"')
page = page.replace('対象期間：9月1日〜10月6日',f'対象期間：2026年9月1日〜{cutoff}')
page = page.replace('2026年9月〜10月のサイバーセキュリティ','2026年9月からのサイバーセキュリティ')
page = page.replace('この1か月に、','公開情報から、')
page = page.replace('<span>2026</span></td>', '<span>2026</span></td>')
OUT.joinpath('index.html').write_text(page)
OUT.joinpath('sitemap.xml').write_text(f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>https://hackernews.allalarm.app/</loc><lastmod>{cutoff}</lastmod></url></urlset>')
print(f'Built dashboard: {len(records)} news items, {len(published)} published incidents.')

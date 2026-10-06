# ALLALARM Cyber Journal

出典に基づく日本語のサイバー事件ニュースサイト。公開先: https://cyber.allalarm.app/

## GitHub Pagesで公開

公開リポジトリ: [konaito/hacker-news](https://github.com/konaito/hacker-news)。公開先: https://cyber.allalarm.app/ 。旧 `hackernews.allalarm.app` はCloudflare Pagesの転送専用サイトで、新ドメインの同じパスへ301転送します。

旧ドメインの転送元は `legacy-redirect/`。転送変更時だけこのディレクトリをCloudflare Pages project `allalarm-hackernews` に公開し、通常のニュース更新はGitHub Pagesにだけ配信します。

`main`へのpush（PRのマージを含む）→ `.github/workflows/github-pages.yml` → データ検証 → build → ページ・SEO/PWA・Service Worker検証 → 同じコミットでの再ビルド一致確認 → GitHub Pagesへ公開。

PRでは検証だけを実行します。公開対象は `public/` のみ。デプロイ用のCloudflare SecretsやOpenAI APIキーは不要です。GitHub Pagesの公開元はGitHub Actions、カスタムドメインは `cyber.allalarm.app`。Cloudflare DNSの `cyber` CNAMEは `konaito.github.io` を指し、プロキシをOFFにします。DNSはCloudflareで管理し、ニュースサイトはGitHub Pagesで配信します。

GitHub Pagesは `_headers` に対応しないため、CSPとreferrer policyはHTMLのmetaで設定しています。独自のHTTPセキュリティヘッダーやworkerのno-cacheヘッダーは設定できません。Service Workerは `updateViaCache: 'none'` とnetwork-firstを維持します。

```sh
gh run list --repo konaito/hacker-news --workflow github-pages.yml
python3 scripts/deploy.py
```

`deploy.py` はmainのActionsを起動します。push完了と公開成功は別なので、Actionsの結果を確認してください。`setup-github.py` は公開リポジトリとPagesを設定する補助スクリプトです。既存のprivateリポジトリを自動公開せず、コミット・pushやDNS変更も行いません。

## 更新履歴

トップページの「更新履歴」と `/updates/` は、公開版のGitコミット履歴から直接生成します。mainの履歴を新しいコミットから順に表示し、コミットメッセージ・日本時間のコミット日時・GitHubの差分リンクを掲載します。サイト保守や未掲載候補の調査のコミットも含みます。変更のない監査はコミットを作らないため履歴も増えません。`data/updates.json` への手動追記は不要です。

Actionsは全履歴を取得し（`fetch-depth: 0`）、デプロイ対象のコミットを含めて生成します。浅いcloneでのbuildは履歴欠落を防ぐため失敗します。ローカルでコミット前に生成したHTMLは直前のHEADの履歴で、Actionsが最新コミットから再生成したものを配信します。履歴表示のためのブラウザ側GitHub API呼び出しはありません。

## 新着・広域の2つの監査ループ

このMacのLaunchAgent `app.allalarm.cyber-news-audit` はload時と3600秒ごとに `scripts/hourly-audit.py` を実行します。Macのスリープ・電源OFF中は停止します。

新着ループは `--mode fresh` で直近72時間の重要ニュースと続報を優先します。広域ループ `app.allalarm.cyber-news-backfill` はload時と21600秒（6時間）ごとに `--mode historical` で2026-09-01以降の取りこぼし・全pending・持ち越し候補を調査します。既存Codexログインを使い、共通指示 `.codex/news-audit.md` とモード別指示に従います。一次情報または独立した信頼できる2媒体の本文確認を掲載条件とし、単一報道はpending。毎回origin/mainを取得してfast-forwardで同期し、変更を検証・コミット・pushします。調査担当はCloudflare認証を読み取らず、公開はGitHub Actionsに任せます。

main以外・origin未設定・未コミット作業・履歴の分岐がある場合は止めてユーザーの作業を守ります。重複起動はロックで防止。push失敗は次回に再試行。監査状態はGit除外の `.audit/fresh/` と `.audit/historical/` に分けて保存します。候補ごとの判断と探索経路を記録し、検証・GitHub同期完了後だけ成功時刻を更新します。共有ロックで同時編集を防ぎ、広域ループは新着の完了を最大30分待ちます。調査上限は新着25分・広域50分です。新着実行時に広域が動いていれば新着は次回へ延期します。

```sh
launchctl print gui/$(id -u)/app.allalarm.cyber-news-audit
```

設定ファイル: `~/Library/LaunchAgents/app.allalarm.cyber-news-audit.plist` と `~/Library/LaunchAgents/app.allalarm.cyber-news-backfill.plist`。

## 編集・検証

事件: `data/incidents.json`。出典: `data/sources.json`。月別編集: `data/monthly-digests.json`。作者の記事カード: `data/featured-reading.json`。AI解説: `ai-content.html`。

```sh
python3 scripts/validate.py
python3 build.py
python3 scripts/check-page.py
python3 scripts/check-seo-pwa.py
node scripts/test-service-worker.cjs
node --check public/app.js
node --check public/pwa.js
node --check public/sw.js
python3 -m http.server 4173 --directory public
```

`python3 scripts/validate.py --links` はHTTP検証です。403等はブラウザで本文を確認し、到達だけで主張の根拠としないでください。

## 本番検証

通常のTerminalで実行:

```sh
cd ~/hacker-news && node scripts/verify-live.cjs
```

このMacのPlaywrightを使い、本番のcanonical・Xカード・JSON-LD・sitemap・RSS・アイコン寸法・記事カード・CSP・検索・詳細・モバイル幅・Service Worker・オフライン動作を確認します。

## SEO・PWA・素材

`seo.py` が公開事件の `/news/<id>/` と月別 `/archive/<month>/`、canonical、OGP/Xカード、JSON-LD、sitemap、RSSを生成します。PWAはmanifestとservice workerでインストール・保存済みページのオフライン閲覧に対応。iPhoneはSafariの共有→ホーム画面に追加、Androidはブラウザのインストールメニューを使用します。オンラインはネットワークを優先し、オフライン情報には案内を表示します。

`service-worker.js` は元テンプレート、`public/sw.js` は内容由来の版を持つ生成物です。新しいworkerは次回アプリ起動・タブ再オープン時に有効になります。検索順位・リッチリザルト・Xカード表示は保証できません。

LINE Seed JP（SIL OFL）とLucideを自己ホスト。ライセンスは `public/fonts/OFL.txt` と `public/icons/LICENSE.txt`。生成画像の条件は `ASSET_NOTES.txt`。アプリアイコン原本は `public/icons/app/app-icon-original.png`、共有画像は `public/assets/social-card.png`。

# ALLALARM Cyber Journal

出典に基づく日本語のサイバー事件ニュースサイト。公開先: https://hackernews.allalarm.app/

## GitHub Actionsへの移行

意図するprivateリポジトリ: `konaito/hacker-news`。現在の設定が完了したかはremoteとGitHubで確認してください。

通常のMac Terminal（ghでkonaitoにログイン済み）から、一度だけ実行:

```sh
cd ~/hacker-news && python3 scripts/setup-github.py
```

アカウント・origin・検証結果を確認し、privateリポジトリを作成、既存ローカルCloudflare認証をActions Secretsへ登録、レビュー済み変更をコミットしmainへpushします。認証値は引数やログに出しません。異なるoriginや既存のpublic/未接続の内容入りリポジトリには接続しません。失敗時は原因を解消して再実行できます。force pushは行いません。

## 公開パイプライン

`main`へのpush（PRのマージを含む）→ `.github/workflows/cloudflare-pages.yml` → データ検証 → build → ページ・SEO/PWA・Service Worker検証 → 生成物の再現性確認 → Cloudflare Pagesへ公開。

PRでは検証だけを実行し、デプロイ用Secretsは使いません。公開対象は `public/` のみ。Cloudflare Pages project `allalarm-hackernews`、production branch `main`、既存ドメインを継続使用します。デプロイ用Secretsは `CLOUDFLARE_API_TOKEN` と `CLOUDFLARE_ACCOUNT_ID`。OpenAI APIキーはデプロイに不要です。

Actionsを確認:

```sh
gh run list --repo konaito/hacker-news --workflow cloudflare-pages.yml
```

デプロイ失敗後の手動再実行:

```sh
python3 scripts/deploy.py
```

このコマンドはActionsを起動します。ローカルからCloudflareへ直接公開しません。push完了とデプロイ成功は別の状態なので、Actionsの結果を確認してください。

## 更新履歴

トップページの「更新履歴」と `/updates/` で、記事の追加・内容更新・掲載取り下げを日本時間で確認できます。過去分は保存されたコミット差分から復元し、今後は毎時監査の調査完了時に公開記事・出典の実際の差分から `data/updates.json` に記録します。日時は事件の公表日やデプロイ完了時刻ではありません。未掲載候補だけの変更、確認日だけの変更、変更のない調査は公開履歴を増やしません。手動で公開記事やサイトを変更するときも、このファイルに日時・要約・変更記事を追記してください。生成HTMLを直接編集する必要はありません。

## 毎時監査

このMacのLaunchAgent `app.allalarm.cyber-news-audit` はload時と3600秒ごとに `scripts/hourly-audit.py` を実行します。Macのスリープ・電源OFF中は停止します。

既存Codexログインを使い、`.codex/news-audit.md` に沿って新着と2026-09-01以降の過去漏れ・続報・pending候補を調査します。一次情報または独立した信頼できる2媒体の本文確認を掲載条件とし、単一報道はpending。毎回origin/mainを取得してfast-forwardで同期し、変更を検証・コミット・pushします。調査担当はCloudflare認証を読み取らず、公開はGitHub Actionsに任せます。

main以外・origin未設定・未コミット作業・履歴の分岐がある場合は止めてユーザーの作業を守ります。重複起動はロックで防止。push失敗は次回に再試行。監査状態はGit除外の `.audit/` に保存します。

```sh
launchctl print gui/$(id -u)/app.allalarm.cyber-news-audit
```

設定ファイル: `~/Library/LaunchAgents/app.allalarm.cyber-news-audit.plist`。

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

# ALLALARM Cyber Journal

2026年9月1日〜10月6日に公表された主要なハッキング・情報漏洩ニュースの静的サイト。

公開先: https://hackernews.allalarm.app/

## 編集・プレビュー

事件記事の内容は `data/incidents.json` と `data/sources.json`、月別編集データは `data/monthly-digests.json`、AI解説は `ai-content.html`、ページ生成は `build.py`、スタイルは `public/style.css`、検索・絞り込み・詳細表示は `public/app.js` にあります。

```sh
python3 build.py
python3 -m http.server 4173 --directory public
```

## Cloudflare Pagesへの公開

プロジェクト名: `allalarm-hackernews`。本番ブランチ: `main`。

環境変数 `CLOUDFLARE_API_TOKEN` と `CLOUDFLARE_ACCOUNT_ID` を安全に設定してから実行:

```sh
npx wrangler pages deploy public --project-name allalarm-hackernews --branch main
```

アップロード対象は `public/` のみ。認証情報をソースや公開ファイルに保存しないでください。

フォントはLINE Seed JP（Regular/Bold、SIL OFL 1.1）、アイコンはLucide 1.52.0を自己ホストしています。ライセンスは `public/fonts/OFL.txt` と `public/icons/LICENSE.txt` に同梱しています。

ヘッダーのイメージ画像は組み込み画像生成ツールで生成。生成条件は `ASSET_NOTES.txt`、サイト内の保存先は `public/assets/cybersecurity-news.png` です。

各事案の状態は参照した発表時点のものです。更新時は一次発表を確認し、本文・情報基準日・sitemap.xmlの最終更新日を揃えてください。

## 毎時監査（このMac）

LaunchAgent `app.allalarm.cyber-news-audit` が起動時と3600秒ごとに `scripts/hourly-audit.py` を実行します。毎時00分固定ではなく起動から毎時です。Macのスリープ・電源OFF中は停止します。

Codexの既存ログインを利用。監査指示は `.codex/news-audit.md`。新着と2026-09-01以降の過去漏れを調査し、候補を照合します。単一報道はpending、一次情報または独立した2報道を確認したものだけ公開。重複・日付・単位・出典の検証後にbuildし、変更時だけローカルcommitしてCloudflare Pagesへ公開します。originがあればpushも実行します。現在originは未設定です。

重複起動はロック、ユーザーの未コミット作業があれば実行を延期。失敗した公開は次回再試行。監査完了日時とログはGit除外の `.audit/` に記録します。Cloudflare認証はリポジトリ外の `~/.config/allalarm/cloudflare.json`（0600）。

状態確認: `launchctl print gui/$(id -u)/app.allalarm.cyber-news-audit`。停止: `launchctl bootout gui/$(id -u)/app.allalarm.cyber-news-audit`。設定ファイル: `~/Library/LaunchAgents/app.allalarm.cyber-news-audit.plist`。

`python3 scripts/validate.py --links` は全出典のHTTP検証。403等は本文のブラウザ確認が必要です。リンク到達だけでは内容の裏付けになりません。

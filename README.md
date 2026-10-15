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

## GitHub ActionsでのClaude定期監査

`.github/workflows/news-audit.yml` がGitHub-hosted runner上のClaude Codeで調査から公開まで実行します。Macの起動・ログインやCodex CLIは不要です。

- 新着: `17 * * * *`（UTC）、毎時17分。直近72時間を重ねて主要ニュースと続報を探索。
- 広域: `43 */6 * * *`（UTC）、6時間ごと。日本時間03:43・09:43・15:43・21:43に、2026-09-01以降の取りこぼしと保留候補を調査。
- 手動: Actionsの「Claude cybersecurity news audit」から `fresh` / `historical` を選んで実行。

GitHubのスケジュールには遅延があり、正確な時刻の実行は保証されません。公開リポジトリで長期間活動がない場合、GitHubが定期実行を無効化することがあります。2モードは共有concurrencyで直列に実行し、実行中の監査を次の起動で打ち切りません。

Claudeは読み取り権限のジョブでWeb検索・出典本文の確認・記事データの編集・監査報告を担当し、終了前に `scripts/actions-audit.py check` で報告と実データの不整合を修正します。別の書き込み権限ジョブが信頼済みのリポジトリから検証スクリプトを実行し、実差分と報告、一次発表または独立した2媒体の本文確認記録、国内外の媒体一覧確認、選択済み再調査候補を検証します。検証済みデータをビルドしてmainに反映し、再利用可能なPagesワークフローが対象コミットを再検証してデプロイします。Claudeが更新したスクリプトを公開処理に取り込むことはありません。

調査は新着25分・広域50分で制限します。持越し再調査は新着最大8件・広域最大20件を確認日時が古い順に処理し、残りは次回へ回します。未完了・報告不正では記事データを公開せず、次回は新しいrunnerでやり直します。部分データと報告は14日間のActions artifactに保存します。

候補と成功状態は専用の `news-audit-state` ブランチの `state.json` に保存します。欠落した候補を解決扱いにせず、失敗した調査から拾った候補は未検証のまま追跡します。本文確認や調査の真偽を形式検証だけで保証するものではありません。mainと成功チェックポイントはatomic pushで同時に同期し、push失敗時は成功日時を進めません。変更なしの監査は状態ブランチだけを更新し、公開の更新履歴にはコミットを追加しません。調査中にmainが進んだ場合は古い記事データを採用せず、候補を保持して次回再調査します。

`GITHUB_TOKEN`によるpushだけでは後続ワークフローが通常起動しないため、監査ワークフローからPagesワークフローを直接呼び出します。同期成功とデプロイ成功は別です。デプロイ失敗はActionsでログを確認して再実行できます。次回の正常な監査でもデプロイを実行します。

### 認証設定

[リポジトリのActions Secrets](https://github.com/konaito/hacker-news/settings/secrets/actions)に、次のどちらか1つを登録します。

- `CLAUDE_CODE_OAUTH_TOKEN`: Claude契約を使う場合。手元で `claude setup-token` を実行して発行。
- `ANTHROPIC_API_KEY`: Claude APIを使う場合。両方ある場合はOAuthを優先。

値はチャット、ソース、ログ、artifactに含めません。認証が未設定ならワークフローは明示的に失敗し、調査完了として扱いません。Claude認証をローカルファイルから自動転送する機能はありません。

旧Mac LaunchAgents `app.allalarm.cyber-news-audit` / `app.allalarm.cyber-news-backfill` は移行後は無効化します。既存の未コミット作業と調査資料はローカルに保持します。旧 `scripts/hourly-audit.py` は手動復旧用に残しますが、通常の定期実行には使いません。状態の初期化時に過去の未解決候補を移行し、既存の検証待ちレコードも引き続き追跡します。

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

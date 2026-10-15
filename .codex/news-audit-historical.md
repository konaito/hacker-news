実行モード: historical（6時間ごとの広域調査）。この指示が共通指示の調査範囲を具体化する。
2026-09-01以降の取りこぼし・続報・pendingと、両モードの過去報告で未解決のdeferred候補を調査する。GitHub Actionsでは持越し再調査はrunnerが選んだ最大20件を必須とし、残りは次回以降に回す。選択は成功報告での確認日時が古い候補から順番に行い、未選択の候補もGitHubのnews-audit-stateブランチに保持する。前回報告から消えた候補も取り落とさない。新着専用ループの報告も読み、発見済み候補を重複追加しない。
必須経路は domestic_media / international_media / official / historical の4つ。social_leadsは任意。月・週・業種・地域を変えて過去記事を検索し、主要媒体のアーカイブを開く。前回 .audit/historical/last-success.json のcoverageとsummaryから調査済み範囲を把握し、同じ検索だけを繰り返さない。初回は旧 .audit/last-success.json も参考にする。
必須候補を確認し、未調査の期間・地域・業種を広げる。summaryに今回調べた範囲と次回優先する範囲を記録する。全件を確認・網羅したとは主張しない。調査は40分を目安に区切り、45分以内に報告を保存し、50分の制限までに終了する。
報告先は .audit/historical/current-report.json。modeはhistorical。必須4経路のcoverageを記録する。共通指示のcurrent-report.jsonのパスはこのモード用パスに読み替える。

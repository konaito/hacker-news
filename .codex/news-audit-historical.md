実行モード: historical（6時間ごとの広域調査）。この指示が共通指示の調査範囲を具体化する。
2026-09-01以降の取りこぼし・続報・全pendingと、両モードの前回報告にあるdeferred候補を調査する。新着専用ループの報告も読み、発見済み候補を重複追加しない。
必須経路は domestic_media / international_media / official / historical の4つ。social_leadsは任意。月・週・業種・地域を変えて過去記事を検索し、主要媒体のアーカイブを開く。前回 .audit/historical/last-success.json のcoverageとsummaryから調査済み範囲を把握し、同じ検索だけを繰り返さない。初回は旧 .audit/last-success.json も参考にする。
毎回全pendingとdeferredを確認した上で、未調査の期間・地域・業種を広げる。summaryに今回調べた範囲と次回優先する範囲を記録する。全事件を網羅したとは主張しない。50分以内に報告まで完了する。
報告先は .audit/historical/current-report.json。modeはhistorical。必須4経路のcoverageを記録する。共通指示のcurrent-report.jsonのパスはこのモード用パスに読み替える。

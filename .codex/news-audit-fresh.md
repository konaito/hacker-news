実行モード: fresh（毎時の新着専用）。この指示が共通指示の調査範囲を具体化する。
直近72時間の公表・続報をメインで調べ、前回 .audit/fresh/last-success.json 以降の重要ニュースを最優先する。初回は旧 .audit/last-success.json も参考にする。
必須経路は domestic_media / international_media / official / social_leads の4つ。全期間の過去漏れ監査・全pending再検証は広域ループが担当するためここでは行わない。直近ニュースに関係するpendingと、両モードの前回報告にあるhighかつdeferred候補は追跡する。
過去事件でも新しい続報なら扱う。重要ニュースの発見・本文検証を先に終え、25分以内に報告まで完了する。調査時間不足の候補はdeferredとして次回へ渡す。本文確認を省略して掲載しない。
報告先は .audit/fresh/current-report.json。modeはfresh。必須4経路のcoverageを記録する。共通指示のcurrent-report.jsonのパスはこのモード用パスに読み替える。

実行モード: fresh（毎時の新着専用）。この指示が共通指示の調査範囲を具体化する。
直近72時間の公表・続報をメインで調べ、前回 .audit/fresh/last-success.json 以降の重要ニュースを最優先する。初回は旧 .audit/last-success.json も参考にする。
必須経路は domestic_media / international_media / official / social_leads の4つ。全期間の過去漏れ監査は広域ループが担当する。GitHub Actionsでは持越し再調査はrunnerが選んだ最大8件を必須とし、選ばれていない持越し全件の再調査で新着探索の時間を使い切らない。選択は成功報告での確認日時が古い候補から順番に行い、未選択の候補もGitHubのnews-audit-stateブランチに保持する。直近ニュースの重要候補は追加調査してよい。前回報告から消えた候補も取り落とさない。
過去事件でも新しい続報なら扱う。重要ニュースの発見・本文検証を先に終え、調査は20分を目安に区切り、22分以内に報告を保存する。runnerの25分の制限までに検証と終了の余裕を残す。調査時間不足の候補はdeferredとして次回へ渡す。本文確認を省略して掲載しない。
報告先は .audit/fresh/current-report.json。modeはfresh。必須4経路のcoverageを記録する。共通指示のcurrent-report.jsonのパスはこのモード用パスに読み替える。

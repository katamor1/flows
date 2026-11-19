# Wordで受けた決定を仕様JSONに反映する

未決事項を仕様JSONから決定票へ出し、レビュー担当者が Word で状態と回答を入力する。取り込みは項目IDと元の仕様の SHA-256 を照合し、編集可能な欄だけを機械的に読む。同じ仕様と決定票を入力した場合、同じ JSON を出力する。

取り込んだ決定は仕様本文を見直すための入力になる。仕様と決定を並べて再評価し、変更する記述、影響するコードおよびテスト、残る未決事項を確認する。判断の取り込みと人による仕様の承認はそれぞれ記録する。

既存の仕様 JSON の `open_issues` を対象にした単独の試作スクリプトを使う。出力先には新しいファイル名を指定する。Word で「状態」と「決定内容」を編集し、変更履歴を確定して保存する。状態は `未決`、`保留`、`決定` のいずれかを入力する。

```powershell
$decisionPython = 'C:\path\to\python.exe'
$decisionOfficeCli = 'C:\path\to\Bob-bundled\officecli.exe'
$decisionTool = 'packages/routine-spec-officecli/word_decision_poc.py'
& $decisionPython -X utf8 -S -B $decisionTool export --officecli $decisionOfficeCli --spec spec.json --out decisions.docx
# Word で決定票を編集し、保存する
& $decisionPython -X utf8 -S -B $decisionTool import --spec spec.json --word decisions.docx --out review-context.json
```

Bob に `review-context.json` を渡し、決定ごとに変更する仕様箇所と既存記述との矛盾を確認する。インターフェイス、状態遷移、エラー時の動作、制約、対応するコードと単体テストを見直し、変更根拠の項目IDと未決事項を記録する。改訂した仕様は仕様書キットで検証し、レビュー後にコード生成と単体テスト仕様の更新へ進む。

2026年11月20日に既存のアラーム仕様を使い、Bob 同梱の OfficeCLI で出力した決定票に回答を1件入力する検査を実行した。取り込み、残る未決3件、同じ内容での JSON の再現性、異なる仕様ハッシュの拒否を確認した。入力編集も OfficeCLI で模擬した。Word 上での手入力と Bob チャットによる再評価は別途確認する。

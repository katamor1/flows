# 固定テンプレートの保守記録

`build_template.py` は単体テスト仕様書用の固定DOCXを一度だけ作成する保守用ツールです。案件ごとのレンダリングには使用しません。既存プログラム仕様書テンプレートをバイトコピーし、OfficeCLIの4件の `raw-set` で本文、スタイル、ヘッダ、フッタを置換しました。PythonによるDOCX/ZIP/XMLパートの直接書込みは行っていません。

実行前にdocumentsスキルの `container_tools/mark_artifact_operation_started.mjs --operation-kind create --expected-output-count 1 --output-format docx` をbundled Nodeで一度だけ実行し、終了コード0を確認しました。マーカーの再実行は不要です。

## 固定様式

- A4縦、左右18mm相当、本文と表10.5ptのYu Gothic。黒い見出し、薄青い表見出し、薄灰の罫線。
- `repeat:view.environment/assumptions/case_index/case_steps/families/static_checks/coverage/open_issues` の8表。すべて見出し1行と原型1行、入れ子表なし、見出し繰返し、行高自動、明細行のページ間分割を許可。
- 詳細手順はケースID手順、初期条件と入力、期待結果と判定、根拠の4列。
- ヘッダは文書IDと関数名、フッタは版と状態およびPAGE/NUMPAGES。
- ケース一覧、詳細、パラメータ族、静的確認、仕様対応表は新ページから開始。過密化を避け、可読性を優先。

## 証拠

`template-commands.json` はOfficeCLI命令、`template-batch.full.json` は各命令の応答、`officecli-invocations.json` は実行引数と終了コードです。すべて `OFFICECLI_NO_AUTO_RESIDENT=1` を指定し、最後に `close` を実行しました。

`validate-template.stdout.json` は成功、エラー0件です。`template-audit.json` はcaption、原型トークン、列数、繰返し見出し、可変行高、A4、ヘッダ文書ID、PAGE/NUMPAGES、既存テンプレート非変更を読取り検査しています。

完成文書の全ページレンダリングと視覚QAは、例JSONと固定レンダラーを統合した後に主スレッドで実施します。構造検査を視覚QAの代替とは扱いません。

保持したテンプレートSHA-256: `fc1faab6615db0d90b77bf25d614a740c50cd0ee529026d8c219211764683138`

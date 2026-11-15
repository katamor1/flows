---
name: routine-spec-doc
description: Use when drafting or revising C90 RTOS routine specifications and generating Word deliverables from JSON with the fixed routine-spec-officecli profile in IBM Bob.
---

# JSON正本からOfficeCLIでWordを生成する

案件ごとに編集するのは、パッケージ外のJSON正本と確認記録である。配布済の固定アダプターが編集命令を作り、OfficeCLIがWordの行複製・差込み・文書属性設定・OOXML検査を行う。

環境票にあるPython 3.12と、承認されたBob同梱OfficeCLI実体の絶対パスを使う。追加のPythonライブラリは不要。以下の `<skill>` はこのスキルディレクトリの絶対パス。

```powershell
& '<python>' -S -B '<skill>/scripts/specflow.py' doctor --officecli '<officecli.exe>'
& '<python>' -S -B '<skill>/scripts/specflow.py' describe --officecli '<officecli.exe>'
& '<python>' -S -B '<skill>/scripts/specflow.py' new-job --officecli '<officecli.exe>' --workspace '<案件ルート>' --job alarm-01
```

返された `source/spec.json` を管理正本として編集する。既存案件ではnew-jobを使わず、正本とpackage-lockを維持する。記述方法と対象範囲は [references/authoring.md](references/authoring.md) を参照する。

```powershell
& '<python>' -S -B '<skill>/scripts/specflow.py' validate --officecli '<officecli.exe>' --workspace '<案件ルート>' --job alarm-01
& '<python>' -S -B '<skill>/scripts/specflow.py' render --officecli '<officecli.exe>' --workspace '<案件ルート>' --job alarm-01 --run r001
```

次回の展開は新しいrun IDを指定する。出力にはWord、入力控え、OfficeCLI命令列・実行結果・構造検査結果、内容と書式の照合結果、manifestが含まれる。Wordへの仕様変更はJSON正本へ戻して再展開する。

OfficeCLIの実体・版・ハッシュや固定資材が不一致なら、その理由と必要な配布版を示して停止する。別版の自動取得、python-docx等への切替、スクリプト・スキーマ・テンプレートの再生成による自己修復は行わない。保守担当が互換性を検証して版を改訂する。

この版は10周期連続ON判定ルーチン、`draft_trial` に限定する。ガウスフィルタや閾値変更は対応外として不足項目を整理し、別のプロファイル改訂へ分ける。RTOS API・ABI・時間予算は正式資料に従い、不明点を推測で確定しない。

OOXML検査の成功と、業務内容・表示・制御コードの試験合格は別に扱う。文量や行数を変更した場合は全ページの表示を確認し、実施できなければ未確認として報告する。

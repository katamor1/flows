---
name: routine-unit-test-spec
description: Use when creating or revising the frozen AlarmQualification_Update C90 unit-test specification and generating Word from JSON through the routine-unit-test-officecli profile in IBM Bob.
---

# 固定入力から単体テスト仕様書を生成する

このスキルは `AlarmQualification_Update` の試作単体テスト仕様書を扱う。案件のJSON正本を編集し、配布済みの固定スクリプトが検証とOfficeCLI命令の組立てを行う。Word内部の行複製・差込み・文書属性設定・構造検査はOfficeCLIが行う。

環境票で確認したPython 3.12と、Bob同梱OfficeCLI 1.0.144の実体の絶対パスを使う。Pythonは標準ライブラリだけを使う。`<skill>` はこのスキルディレクトリ、`<code-job>` は対象の既存コードPoCディレクトリの絶対パス。

```powershell
& '<python>' -S -B '<skill>/scripts/utflow.py' doctor --officecli '<officecli.exe>'
& '<python>' -S -B '<skill>/scripts/utflow.py' describe --officecli '<officecli.exe>'
& '<python>' -S -B '<skill>/scripts/utflow.py' new-job --officecli '<officecli.exe>' --code-job '<code-job>' --workspace '<案件ルート>' --job alarm-ut-01
```

`new-job` はコードPoCの `input/spec.json`、`src/AlarmQualification.c`、`include/AlarmQualification.h`、`generation-record.json` を読み、固定ハッシュと生成来歴を照合する。コピーした入力を `inputs/` と `input-lock.json` に固定し、`source/unit-test-spec.json` と全項目未実施の `records/execution-record.json` を作る。既存jobは上書きしない。

案件で編集するのは `source/unit-test-spec.json` と作者・レビュー・表示確認等の記録である。[記述規約](references/authoring.md) に従い、仕様由来の期待値とコード由来の追加観点を区別する。新規仕様に旧ログから合格を転記しない。この版の実施記録は全項目 `not_executed`、証跡配列は空に限定する。

```powershell
& '<python>' -S -B '<skill>/scripts/utflow.py' validate --officecli '<officecli.exe>' --workspace '<案件ルート>' --job alarm-ut-01
& '<python>' -S -B '<skill>/scripts/utflow.py' render --officecli '<officecli.exe>' --workspace '<案件ルート>' --job alarm-ut-01 --run r001
```

次の展開では新しいrun IDを使う。成功したrunだけを公開する。出力にはJSON控え、Word、対応表、入力ロックと実施記録の控え、OfficeCLI命令・応答・構造検査、内容・書式照合、ハッシュと利用版を含むmanifestを保存する。Wordでの内容修正はJSON正本へ戻して再展開する。

固定資材・入力・OfficeCLI実体・jobロックが一致しなければ理由を報告して停止する。別版の取得、文書生成器の切替、ロック書換え、スクリプト・スキーマ・テンプレートの再生成で回避しない。固定資材の改訂は保守者が新しい版として行う。

対象は固定された1ルーチンの `draft_trial` である。試験実行器、要求承認、RTOS接続、WCET測定は含まない。構造・内容照合が成功しても表示確認や試験合格にはしない。文量変更後は全ページを確認し、未確認なら未確認と報告する。Bobから実施していない作業を「Bobで検証済み」と記録しない。

---
name: routine-unit-test-spec
description: Create a generic unit-test specification from locked program/C/H inputs and render Word with OfficeCLI. Supports finite JSON values, arbitrary routines, dynamic traceability, and unexecuted records.
---

# プロジェクト入力から単体テスト仕様書を作る

0.2.0は任意のプログラム仕様・C/Hを案件ごとに固定し、JSON正本からOfficeCLI 1.0.144でWordを生成する。Python 3.12標準ライブラリのみを使う。固定資材を作者が変更せず、案件のsource/unit-test-spec.jsonを編集する。

```powershell
& '<python>' -X utf8 -S -B '<skill>/scripts/utflow.py' doctor --officecli '<absolute-officecli.exe>'
& '<python>' -X utf8 -S -B '<skill>/scripts/utflow.py' describe --officecli '<absolute-officecli.exe>'
& '<python>' -X utf8 -S -B '<skill>/scripts/utflow.py' new-job --officecli '<absolute-officecli.exe>' --code-job '<code-job>' --unit-test-spec '<authored-ut.json>' --workspace '<jobs-root>' --job project-ut
```

`--code-job`はjob.json 0.2.0/0.1.0のspec/source/header/generation_recordを読み、生成記録の実ハッシュと追加file_hashesを確認する。ルーチン名、ファイル名、正本ハッシュは案件ごとに異なる。生成記録は来歴の申告であり電子署名ではない。別プロジェクトでは`--program-spec FILE --source FILE --header FILE`を使える。その場合は来歴を`external/not_provided`と明記し、生成記録を作らない。

`--unit-test-spec FILE`は作者が原仕様から期待値を定めた0.2.0正本を検証して取り込む。省略時はtarget・仮定・課題を反映した未記入スケルトンを作る。summaryや確認項目が未記入のままではvalidate/renderが失敗する。案件IDは新規にし、既存案件を上書きしない。

[記述規約](references/authoring.md)に従いcases/families/static_checks/coverageを記述する。casesの初期条件・入力・期待値は任意の有限JSON値で、式・Pythonとして実行しない。比較名はequals/unchanged/predicate/within_tolerance等を文章で定義できる。familiesは直積または1 alphabetの有限系列を記述し、combination_countとcalls_per_instanceからcall_countを検算する。

原仕様の仮定・手順・制約・検証例・インターフェース・振る舞いの宣言を、IDまたはJSON Pointerでcoverageへ対応付ける。未検証はunverified、呼出し側はcaller、範囲外はout_of_scopeとし、理由を残す。各確認項目のspec_refsとcoverageは双方向で一致させる。原仕様の仮定・課題は空でもそのまま引き継ぐ。

```powershell
& '<python>' -X utf8 -S -B '<skill>/scripts/utflow.py' validate --officecli '<absolute-officecli.exe>' --workspace '<jobs-root>' --job project-ut
& '<python>' -X utf8 -S -B '<skill>/scripts/utflow.py' render --officecli '<absolute-officecli.exe>' --workspace '<jobs-root>' --job project-ut --run r001
```

確認項目のIDを追加・変更したらrecords/execution-record.jsonも対応する全IDをnot_executed/evidence=[]で更新する。この文書生成器は試験を実行せず、旧集計ログのpassedを取り込まない。原仕様の状態を作者が正しく引き継ぎ、ツールが承認状態を作らない。

成功runにはunit-test-spec.docx、JSON控え、入力ロック、全項目未実施記録、traceability、OfficeCLI命令・応答・構造検査、全テキスト・書式の照合とmanifestを保存する。空欄リストの「該当なし」は表示viewだけに追加し、JSON正本のハッシュを変えない。

固定資材・OfficeCLI実体・jobロック・入力のハッシュ不一致を検出したら停止し、ロック書換えや生成器の変更で回避しない。新しい版は保守工程で配布する。.gitattributesはskill/job内のbyteを改行変換から守る。

表示の全ページ確認、Bobでのスキル起動、C90実行、実RTOS、正式コンパイラ、WCET、要求承認はこのコマンドの検証外である。未確認事項は未確認として報告する。旧0.1.0仕様の再現には保存済み0.1.0 ZIPを使う。

# 汎用jobの入力と実行手順（0.2.0）

## JSON正本

`prepare` は任意のルーチンのJSONを受け付ける。必須の共通項目は次のとおり。仕様の原バイト列をjobへコピーしてSHA-256を固定し、その他の項目も原文のまま保存する。

| 項目 | 契約 |
| --- | --- |
| `document.id` | 仕様書の識別子 |
| `document.routine_id` | ルーチンの識別子 |
| `document.routine_name` | 対象関数のC識別子。標準C/Hのファイル名にも使う |
| `document.status` | 仕様の状態。試作・承認待ち等をそのまま引き継ぐ |
| `interface.language` | `C90` |
| `interface.prototype` | 対象関数のC90プロトタイプ宣言 |
| `interface.type_definitions` | ヘッダへ展開する型定義。型定義不要なら空文字 |

アラーム例の `behavior`、`trial_assumptions`、`constraints` 等の構造やID数は必須スキーマではない。業務ルール・エラー・時間・状態等は提供された仕様から読み取る。共通項目だけで動作が決まらない場合、prepare成功を理由に未定義の業務ルールを補わない。

元のフル仕様（例：`schema_version=0.1.0`）も、共通項目と対象の業務契約を持つ新しい最小仕様（例：`schema_version=0.2.0`、状態なし・型定義空）も入力にできる。製品全体の入力ハッシュ制限は設けず、各jobにコピーした正本の改変検知は維持する。profileを指定する場合だけ、targetハッシュでその試験・依存資産と仕様を結び付ける。profileを用意しなくてもコード生成用jobは準備できる。

## 環境と新規job

チームが用意したPython 3.12とClangを使う。固定Pythonスクリプトは標準ライブラリだけを使う。Clangと同じフォルダの `llvm-nm` が必要で、試験実行時は対象ホスト用のリンカー・SDKも必要。Python、Clang、正式RTOS SDK等は配布物に含めない。

以下のパスは実際の絶対パスに置き換える。jobの保存先は配布パッケージの外に置く。job/generation/run IDは先頭が英数字、その後は英数字・`_`・`-` の合計64文字以内とし、新規IDを使う。

```powershell
& '<python>' -X utf8 -S -B '<skill>/scripts/codegen.py' doctor
& '<python>' -X utf8 -S -B '<skill>/scripts/codegen.py' prepare --spec '<spec.json>' --workspace '<job-root>' --job routine-01
```

独立試験と依存資産が提供されている場合は、[プロファイルの契約](verification-profile.md) を確認し、準備時に追加する。

```powershell
& '<python>' -X utf8 -S -B '<skill>/scripts/codegen.py' prepare --spec '<spec.json>' --verification-profile '<verification-profile.json>' --workspace '<job-root>' --job routine-tested-01
```

仕様、展開済みヘッダ、指定プロファイルとその依存資産を読み、`job.json` の `source` に示されたファイルへUTF-8のC90本体を作る。例えば `routine_name=RangeClamp` なら `src/RangeClamp.c` と `include/RangeClamp.h` になる。完成済みの実装はprepareで提供しない。`traceability.md` も作る。

## 生成記録と検証

`--agent`、`--agent-version`、`--bob-executed`、`--note` は実態を記入する。次の `no` はBob未実行の場合。実際にBobで生成した場合だけ `--agent 'IBM Bob'`、実際のBob版、`--bob-executed yes` とする。

```powershell
& '<python>' -X utf8 -S -B '<skill>/scripts/codegen.py' record --workspace '<job-root>' --job routine-01 --generation g001 --agent '<実際のAI/実行環境名>' --agent-version '<実際の版/識別子>' --bob-executed no --note '<実際の作業内容と未決事項>'
& '<python>' -X utf8 -S -B '<skill>/scripts/codegen.py' verify --workspace '<job-root>' --job routine-01 --clang '<clang.exe>' --run r001
```

同一jobの編集・record・verifyは直列に行う。record/verify間も本体・対応表を変更しない。固定資産や生成記録と現在の内容が一致しなければverifyは停止する。verifyは検査した入力・本体のスナップショットを保存し、そのコピーをコンパイルする。実行中の変更を合格として採用しない。

本体を修正したらg002等の新世代を記録し、r002等の新runで検証する。過去の世代/runは上書きしない。入力・固定ヘッダ・試験・サポートの変更が必要なら新規jobを作る。ロックを手で書き換えて不一致を解消しない。

検証結果は `qa/<run>/verification.json` を読み、実際のコマンド・ツール版・ハッシュ・最適化別結果を確認する。合格/不合格は実結果から報告し、コンパイルや試験の失敗も残す。試験なしでは `status=compiled_only` / `test_execution=not_provided`、試験ありでO0/O2とも成功した場合は `status=passed` と報告する。出力やチェック数をサンプルの固定値と照合しない。

`records/<generation>.json` の `input_spec_sha256`、`source_sha256`、`header_sha256` と複数資産の `file_hashes` は、その世代が何に基づくかを示す。QAスナップショットは `qa/<run>/snapshot/` に保存される。生成コードと対応表の正式な履歴もGit等で保存する。

環境・入力・資材の不一致は原因を報告する。別ツールの自動取得や検査の弱体化で回避しない。正式RTOSビルド・DLL ABI・結合・実機時間の検証は、チームの正式手順で別途行う。

## サンプルと移行

- `assets/examples/range-clamp/`：状態を持たない `RangeClamp` の仕様と独立ホスト試験。profileなしならコンパイル検査、同梱profile指定なら試験ありの手順を試せる。
- `assets/examples/sample-hold/`：状態と提供APIを使う `SampleHold_Update` の合成試験。提供ヘッダとモックを同梱する。実RTOSのAPIや正式SDKの代替ではない。
- `assets/examples/alarm-regression/`：[旧アラーム案件](alarm-profile.md) の正本と独立試験を0.2.0で扱う例。0.1.0を保存したまま新規jobを準備する。

例えばRangeClampの独立試験を指定する準備は次のとおり。例の処理や期待値を他の案件へ固定条件として持ち込まない。

```powershell
& '<python>' -X utf8 -S -B '<skill>/scripts/codegen.py' prepare --spec '<skill>/assets/examples/range-clamp/spec.json' --verification-profile '<skill>/assets/examples/range-clamp/verification-profile.json' --workspace '<job-root>' --job clamp-01
```

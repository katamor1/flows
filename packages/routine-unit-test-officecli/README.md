# IBM Bob向け 単体テスト仕様書OfficeCLIキット 0.1.0

固定プログラム仕様書とC90ソースを入力として、JSON正本からWord単体テスト仕様書を展開する。対象は `RTN-ALM-001 / AlarmQualification_Update` 1ルーチンの `draft_trial`。固定スクリプトが検査と編集命令の組立てを行い、OfficeCLIがWordの行複製・差込み・文書属性設定・OOXML構造検査を行う。

このキットは試験設計と文書生成のPoCである。動的試験実行器は含まない。全ケース・列挙族・静的確認を未実施で作成し、既存の合格ログからケース別結果を転記しない。要求承認、RTOS接続、WCET測定、Bobチャットからの受入は別に記録する。

## 必要な環境と配布

- Windows、Python 3.12。標準ライブラリだけを使用し、pipによる依存導入は不要。
- Bob同梱OfficeCLI 1.0.144。実体のSHA-256は `release.json` で固定する。
- 固定入力を含む既存コードPoCのディレクトリ。`input/spec.json`、`src/AlarmQualification.c`、`include/AlarmQualification.h`、`generation-record.json` が必要。

OfficeCLI・Python・認証情報はZIPへ同梱しない。版や実体が変わった場合は保守担当が互換性を確認し、新配布版を作る。不一致時の自動取得や生成器切替は行わない。

配布ZIPの `.bob/skills/routine-unit-test-spec/` と `.bob/rules/30-routine-unit-test-spec.md` を対象プロジェクトへ取り込む。既存 `.bob` 全体は置換しない。チームは同じGit版を共有する。`distribution.json` は配布来歴であり、Bobのプラグインmanifestではない。MCPや自動承認の設定は含めない。

## 実行

環境に合う絶対パスを指定する。`$utCodeJob` は対象の既存コードPoC、`$utJobs` はパッケージ外の案件ルートとする。

```powershell
$utPython = 'C:\path\to\python.exe'
$utOffice = 'C:\path\to\Bob-bundled\officecli.exe'
$utProject = 'C:\work\control-project'
$utSkill = Join-Path $utProject '.bob/skills/routine-unit-test-spec'
$utCodeJob = 'C:\work\routine-code-poc'
$utJobs = Join-Path $utProject 'unit-test-jobs'
& $utPython -S -B "$utSkill/scripts/utflow.py" doctor --officecli $utOffice
& $utPython -S -B "$utSkill/scripts/utflow.py" describe --officecli $utOffice
& $utPython -S -B "$utSkill/scripts/utflow.py" new-job --officecli $utOffice --code-job $utCodeJob --workspace $utJobs --job alarm-ut-01
& $utPython -S -B "$utSkill/scripts/utflow.py" validate --officecli $utOffice --workspace $utJobs --job alarm-ut-01
& $utPython -S -B "$utSkill/scripts/utflow.py" render --officecli $utOffice --workspace $utJobs --job alarm-ut-01 --run r001
```

`-S -B` は追加ライブラリとバイトコード出力を抑える。固定資材・承認済実体・入力のハッシュを照合し、同名job/runは拒否する。OfficeCLI実行時は自動resident起動を抑え、生成後はcloseを行う。途中失敗の作業ディレクトリを成功runとして公開しない。

新規jobには入力コピーと `input-lock.json`、配布版・OfficeCLIを指す `package-lock.json`、`source/unit-test-spec.json`、全項目未実施の `records/execution-record.json` ができる。作者は正本と確認記録を編集し、固定資材とロックを変更しない。記述規約はスキルの `references/authoring.md` を参照する。

## 展開結果

`unit-test-jobs/alarm-ut-01/renders/r001/` に次を保存する。

| ファイル | 内容 |
|---|---|
| `unit-test-spec.json` | 展開時のJSON正本の控え |
| `UTS-RTN-ALM-001.docx` | OfficeCLIが生成した単体テスト仕様書 |
| `traceability.json` | 仕様から試験・レビュー等への割当てと集計 |
| `input-lock.json` / `execution-record.json` | 入力ロックと未実施記録の控え |
| `officecli-commands.json` / `officecli-batch.json` | 編集命令と全命令の応答・件数 |
| `officecli-validation.json` / `officecli-close.json` | OOXML構造検査とclose応答 |
| `content-check.json` | 本文・表・期待値・書式・ページフィールドの照合 |
| `manifest.json` | 入出力・入力ロック・配布資材・実体のハッシュと利用版 |

代表ケース、手順行、列挙族、族内の組合せ/系列、呼出し照合は別々に数える。4族は88 / 24 / 6 / 177147組・系列、88 / 24 / 6 / 1948617呼出し照合を定義する。大量系列は定義・期待値規則・例として出力し、全系列をWordの表へ展開しない。

入力の `{{...}}` を含む文字列は再差込みせず保持する。JSONから作る表示モデルとDOCXの表行・順序・全内容・指定書式・ページフィールド・文書属性を照合し、固定部品も比較する。生成物のバイトハッシュは来歴用、`semantic_sha256` は同一内容・書式の比較用である。

構造と内容の検査成功は改ページや意味の承認ではない。実際の納品環境で全ページを表示確認し、その記録をrunへ紐付ける。試験実施、表示確認、要求承認、Bobによる実施を別々に扱う。

## Bobへの依頼例

> routine-unit-test-specスキルで、指定した既存コードPoCからalarm-ut-01を作成し、固定入力を確認して単体テスト仕様JSONを検証・Word展開してください。指定済みのPythonとBob同梱OfficeCLIを使い、固定資材を再利用してください。全ケースは未実施のままとし、表示確認を実施できなければ未確認と報告してください。

## 保守と確認記録

`tools/release.py seal` が固定資材のハッシュを確定し、`bundle` がBob向けZIPとチェックサムを作る。保守用コード・試験・中間物・案件成果物は通常のスキルZIPへ含めない。検証担当は固定入力、異常データ拒否、実OfficeCLI展開、別runの内容一致、配布先再実行、上書き拒否、資材改変検出、全ページ表示を確認する。

実行結果と未確認項目はこのREADMEへ確認記録として追記する。Bobチャットでのスキル検出・起動を実施するまでは、CLI経路とBob受入を区別する。

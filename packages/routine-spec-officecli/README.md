# IBM Bob向け OfficeCLI仕様書生成キット 0.2.0

JSON正本からWord生成・OOXML構造検査までをOfficeCLIへ統一した。固定アダプターが正本を検証して編集命令データを組み立て、OfficeCLIが行複製、値差込み、文書属性設定、構造検査を行う。スクリプトやテンプレートを案件ごとに再生成しない。

対象は10周期連続ON判定ルーチン1本の `draft_trial`。C90コード生成、実RTOS接続、任意ルーチンの仕様化は含まない。

## 必要な環境

- Windows、Python 3.12。Pythonは標準ライブラリだけを使用する。python-docx、lxml、pipによる依存導入は不要。
- 承認済のIBM Bob同梱OfficeCLI 1.0.144。版と実体のSHA-256をrelease.jsonで固定する。
- 今回実行した実体はBob IDE 2.2.3の `resources/app/extensions/bob-code/dist/officecli.exe`。他環境では管理者が実体の絶対パスを確認する。

OfficeCLI本体はこのZIPへ再同梱しない。Bobの更新等で版・実体が変わった場合は、保守担当が互換性を検査して配布版を改訂する。不一致時に別版を自動取得したり、別の文書生成器へ切り替えない。

## チーム配布

ZIPを一度別の場所へ展開し、対象プロジェクトへ `.bob/skills/routine-spec-doc/` と `.bob/rules/20-routine-spec.md` を取り込む。既存 `.bob` 全体は置換しない。保守担当のPRで共有し、チームは同じGit版をチェックアウトする。

BobのSkills設定でプロジェクトの `routine-spec-doc` を確認し、新しい会話のAgentモードで利用する。`distribution.json` は配布来歴であり、Bobのプラグインmanifestではない。MCPや自動承認の設定は含めていない。

## 実行

環境に合わせた絶対パスを指定する。`$specOffice` は同梱実体を確認したパスとする。

```powershell
$specPython = 'C:\path\to\python.exe'
$specOffice = 'C:\path\to\Bob-bundled\officecli.exe'
$specProject = 'C:\work\control-project'
$specSkill = Join-Path $specProject '.bob/skills/routine-spec-doc'
$specJobs = Join-Path $specProject 'spec-jobs'
& $specPython -S -B "$specSkill/scripts/specflow.py" doctor --officecli $specOffice
& $specPython -S -B "$specSkill/scripts/specflow.py" describe --officecli $specOffice
& $specPython -S -B "$specSkill/scripts/specflow.py" new-job --officecli $specOffice --workspace $specJobs --job alarm-01
```

返された `source/spec.json` を編集し、次を実行する。

```powershell
& $specPython -S -B "$specSkill/scripts/specflow.py" validate --officecli $specOffice --workspace $specJobs --job alarm-01
& $specPython -S -B "$specSkill/scripts/specflow.py" render --officecli $specOffice --workspace $specJobs --job alarm-01 --run r001
```

`-S` はPythonの追加ライブラリを読み込まない指定で、この状態で一連の検査を実行している。`render` は成功した展開だけを新しいrun IDへ公開する。同名案件・同名run IDは拒否する。

## Bobへの依頼例

> routine-spec-docスキルで、10周期ON判定の仕様例から新規案件alarm-01を作成してください。管理者が指定したPythonとBob同梱OfficeCLIを使い、doctorを確認してからJSONの文書版だけを0.2へ変更し、検証・Word展開してください。固定アダプターとテンプレートを再利用し、OfficeCLIの構造検査と内容照合結果を確認してください。表示確認を実施できなければ未確認と報告してください。

このキットの直接CLI経路は実行済み。Bobチャットからのスキル検出・起動は、チーム環境での受入項目として残る。

## 出力と検査

`spec-jobs/alarm-01/renders/r001/` に次を保存する。

| ファイル | 内容 |
|---|---|
| `spec.json` | 展開時の正本の控え |
| `PS-RTN-ALM-001.docx` | OfficeCLIが生成した仕様書 |
| `officecli-commands.json` | 固定アダプターが生成した編集命令データ |
| `officecli-batch.json` | 全命令の実行結果と件数 |
| `officecli-validation.json` | OfficeCLIのOOXML構造検査結果 |
| `officecli-close.json` | 文書保持プロセスの終了確認 |
| `content-check.json` | 文章、表、書式、ページフィールドの照合結果 |
| `manifest.json` | 正本・資材・実体・出力のハッシュと利用版 |

各置換の件数、全命令完了、表の行順と行数、段落・セルの内容、指定書式、用紙・余白・ヘッダー参照、PAGE/NUMPAGES、文書属性を確認する。styles・relationships等の非変更部品も照合する。OfficeCLIが0件置換を成功と返す場合も、アダプターは期待件数と合わなければ停止する。入力中の `{{id}}` 等は文字列として扱い、再び差し込まない。改行は元の段落内改行へ変換する。

OfficeCLIが監査時刻やZIPのメタデータを記録するため、同一正本でもDOCXのバイト列が変わる場合がある。比較には内容・書式モデルの `semantic_sha256` を使い、生成物そのもののSHA-256も来歴として別に残す。

OOXML検査の成功は、意味や改ページの承認ではない。文量・表行数を変えた場合は、実際の納品確認環境で全ページを確認する。C90コンパイル、単体テスト、RTOS性能は別工程である。

## 固定テンプレートと旧版からの移行

旧テンプレートはWord表示確認済みだったが、OfficeCLIの厳密な構造検査で要素順序・属性等の164件が検出された。新版ではOfficeCLIによる一度限りの保守修正を行い、文章・差込タグ・表構造・ページフィールドを維持したまま構造エラーを0件にした。通常実行ではテンプレートを修正しない。

旧0.1.0の正本契約と記述例を継続使用する。テンプレートの論理IDは `routine-spec-v01`、固定資材の改訂は `template_revision: 0.2.0` として区別する。旧案件のロックを上書きせず、新しいキットで新規案件を作成して正本を引き継ぎ、差分を確認する。

資材と実行実体のハッシュ照合は誤変更の検出である。書換えを権限として防ぐ場合は、配布領域を実行アカウントから書込み不可にし、案件領域だけを書込み可能にする。

## 保守用資料

リポジトリ内の `tools/release.py` は版固定とZIP作成、`tests/test_flow.py` は実OfficeCLIを使う検査。保守用コードや検査・描画の中間物は通常のBob配布ZIPに含めない。

参考: [OfficeCLI 1.0.144](https://github.com/iOfficeAI/OfficeCLI/tree/v1.0.144)、[Wordの行複製](https://github.com/iOfficeAI/OfficeCLI/blob/v1.0.144/src/officecli/Handlers/Word/WordHandler.Mutations.cs)、[検索・置換](https://github.com/iOfficeAI/OfficeCLI/blob/v1.0.144/src/officecli/Handlers/Word/WordHandler.Helpers.FindReplace.cs)、[batch](https://github.com/iOfficeAI/OfficeCLI/wiki/command-batch)。

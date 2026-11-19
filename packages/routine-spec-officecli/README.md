# IBM Bob向け OfficeCLIプログラム仕様書キット 0.3.0

任意のルーチンのフルJSON正本を検証し、固定テンプレートからWordを生成する。既存0.1.0と新0.2.0の正本を受け付け、関数名、文書ID、状態、閾値、配列件数を固定しない。生成と検証の実行者はCodex。Bobチャットからの起動は未確認である。

## 環境と配布

Windows、Python 3.12の標準ライブラリ、承認済OfficeCLI 1.0.144を使う。OfficeCLIのSHA-256はrelease.jsonで固定し、本体は再配布しない。固定スキーマ、アダプター、テンプレート、記述例の全資材はハッシュで照合する。

ZIP内の`.bob/skills/routine-spec-doc/`と`.bob/rules/20-routine-spec.md`を対象プロジェクトへ取り込む。既存`.bob`全体を置換しない。旧0.2.0 ZIPと旧案件はそのまま保持し、新規案件として移行する。スキルと案件の`.gitattributes`は`* -text`を配布し、Gitの改行変換によるロック破損を防ぐ。globalやrootのGit設定は変更しない。

## 実行

環境票にある実体の絶対パスを指定する。

```powershell
$specPython = 'C:\path\to\python.exe'
$specOffice = 'C:\path\to\Bob-bundled\officecli.exe'
$specSkill = 'C:\work\project\.bob\skills\routine-spec-doc'
$specJobs = 'C:\work\project\spec-jobs'
& $specPython -X utf8 -S -B "$specSkill/scripts/specflow.py" doctor --officecli $specOffice
& $specPython -X utf8 -S -B "$specSkill/scripts/specflow.py" describe --officecli $specOffice
& $specPython -X utf8 -S -B "$specSkill/scripts/specflow.py" new-job --officecli $specOffice --workspace $specJobs --job clamp-01 --spec "$specSkill/assets/examples/range-clamp/spec.json"
& $specPython -X utf8 -S -B "$specSkill/scripts/specflow.py" validate --officecli $specOffice --workspace $specJobs --job clamp-01
& $specPython -X utf8 -S -B "$specSkill/scripts/specflow.py" render --officecli $specOffice --workspace $specJobs --job clamp-01 --run r001
```

`--spec FILE`は指定ファイルのバイト列をそのまま`source/spec.json`へ取り込む。未指定なら`--routine-name`、`--routine-id`、`--document-id`で識別情報だけを入れた未記入スケルトンを作る。最小引数では空の識別情報を含むスケルトンになる。どちらも業務規則を自動補完しない。作者が内容を埋めるまでvalidate/renderは拒否する。既存job/runの上書きは拒否し、失敗した展開は公開しない。

## 正本契約

`document/overview/trial_assumptions/interface/behavior/constraints/verification_examples/traceability/open_issues`のフル形を維持する。状態、引数、戻り値表、前提、制約、確認例、対応表、課題は0件可、型定義は空文字可。`behavior.threshold`は任意の数値、`behavior.configuration`は任意の`{name,value,meaning}`配列でvalueは有限JSON値を受け付ける。

`behavior.decision_rows`は`condition`と任意の項目名・有限JSON値を持つobjectである。Wordでは条件と残る項目のkey/valueを表示する。旧`old_count/new_count/qualified/event`も普通の項目として表示し、必須にはしない。空は表示viewで「該当なし」とし、正本へダミーを追加しない。文書状態と表示ラベルは入力をそのまま出す。ツールは承認状態を作らず、人の承認を代行しない。

既定テンプレートIDは`routine-spec-v02`。旧`routine-spec-v01`入力は新版の汎用表示へ適合させる。旧ZIPによる旧レイアウト再現は引き続き可能である。

## 出力と保証範囲

新しい`renders/<run>/`にWord、正本控え、OfficeCLI命令列、全命令の実行結果、OOXML構造検査、内容・書式照合、close確認、manifestを保存する。入力と資材、実行実体、出力のハッシュを記録する。2段階の置換で入力中のタグを再展開しない。置換件数、表の全行・全内容、段落・セル書式、用紙・余白、ヘッダー参照、PAGE/NUMPAGES、文書属性、非変更部品を照合する。

OOXML検査と内容照合は業務意味、画面上の改ページ、C90コンパイル、RTOS接続、WCETの保証ではない。この版では全ページの表示確認を実施していない。Wordの表示確認と人による仕様承認は別途必要である。

## 保守

通常の作者は固定資材を書き換えない。`maintenance/generic-template/build_v02.py`はOfficeCLIだけで一度作成した新版テンプレートの保守証跡で、通常実行から呼び出さない。PythonはXMLの読取り検査だけを行う。`tools/release.py`でseal後にbundleし、`dist/checksums-0.3.0.json`へ新ZIPのハッシュを記録する。旧ZIPと旧checksums.jsonは保存する。

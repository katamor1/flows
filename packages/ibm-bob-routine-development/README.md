# IBM Bob ルーチン開発 3工程キット 0.1.0

機能要求からプログラム仕様JSONを記述し、C90ルーチン、単体テスト仕様JSONを順に作るための固定スキル・スキーマ・テンプレート・ツールをまとめた配布物。WordはJSONからOfficeCLIで展開する。毎回AIにスクリプトやテンプレートを再生成させない。

|工程|Bobスキル|キット版|作者が作成するもの|
|---|---|---|---|
|プログラム仕様|routine-spec-doc|0.3.0|要求を具体化したフル仕様JSON|
|C90コード|routine-code-c90|0.2.0|C本体、仕様対応表|
|単体テスト仕様|routine-unit-test-spec|0.2.0|入力・期待値・仕様対応を含むUT JSON|

固定ツールは入力固定・スキーマ検査・Word展開・生成記録・任意の提供ホスト試験を担当する。業務ロジックや期待値は作者が仕様から判断する。関数名、文書ID、状態の有無、閾値、ケース数、期待値の項目名を特定サンプルに固定しない。

## 配布と更新

Windows、Python 3.12、Bob同梱OfficeCLI 1.0.144を使う。コードのホスト検証にはClangと同じディレクトリのllvm-nm、対応するSDK/リンカーが必要。これらの実行環境や正式RTOS SDKはZIPに同梱しない。OfficeCLIは版とSHA-256を固定しており、Bobの更新で実体が変わった場合は保守担当による適合確認と新版の作成が必要。

ZIPを作業用フォルダへ展開して、付属の管理スクリプトで検証・導入する。通常の案件作成ではbuildを実行しない。

```powershell
$kitPython = 'C:\path\to\python.exe'
$kitManager = 'C:\temp\routine-development\tools\manage.py'
$kitArchive = 'C:\downloads\ibm-bob-routine-development-0.1.0.zip'
& $kitPython -X utf8 -S -B $kitManager verify --archive $kitArchive
& $kitPython -X utf8 -S -B $kitManager install --archive $kitArchive --project 'C:\work\project' --install-id generic-001
```

導入先は3つの`.bob/skills/`と2つの`.bob/rules/`、規約用`.gitattributes`に限定する。同名の既存資材は`artifacts/bob-distribution-backups/<install-id>/previous/`へそのまま保存し、旧版の不要ファイルが混ざらないように配置する。無関係な設定は変更しない。再導入には別のinstall-idを使う。配布・来歴ハッシュは誤変更検知であり、署名や信頼できない配布元の認証にはならない。

`.bob`をGitでチーム共有する。配布資材・案件の`.gitattributes`は`* -text`としてバイト列の自動改行変換を抑える。旧案件・旧ZIPを新版で書き換えず、入力変更は新しいjobへ取り込む。

## 案件の進め方

1. Bobに`routine-spec-doc`を指定し、機能要求と正式なRTOS API・型・タイミング制約を渡す。new-jobの未記入JSONへ仕様を記述するか、既存のフルJSONを`--spec`で取り込む。validate後、renderで確認用Wordを生成する。
2. 同じ仕様jobの`source/spec.json`を`routine-code-c90`のprepareへ渡す。AIがC本体と対応表を作り、recordで実際の生成者とハッシュを記録する。提供された独立ホスト試験があれば検証プロファイルを指定する。試験未提供のverify結果は`compiled_only`。
3. `routine-unit-test-spec`のnew-jobへ`--code-job`でコードjobを渡し、対象JSON/C/Hを固定する。AIが原仕様からUT JSONを記述する。既存UT JSONは`--unit-test-spec`で取り込む。validate/renderで確認用Wordを作る。試験の実施記録は全項目未実施から別管理する。

工程ごとのコマンド・JSON契約は`guides/`の各READMEとインストール先のSKILL.mdにある。3工程を通じて同じ正本のバイト列と生成C/Hのハッシュを照合する。スケルトンは未記入のまま検査を通さず、旧アラームの業務規則や試験合格を自動注入しない。

Bobへの依頼例:

> この機能要求をroutine-spec-docで新規案件にし、正式な契約の範囲で仕様JSONを作成してください。確認用Wordを生成した後、同じJSONをroutine-code-c90へ渡してC90本体と対応表を作成し、来歴と提供ホスト試験の結果を記録してください。そのコードjobからroutine-unit-test-specで単体テスト仕様JSONとWordを作成してください。不明点・未実施項目は明記し、固定スキルやテンプレートは変更しないでください。

## 今回の確認範囲

Codexから固定CLIを実行して検証した。旧アラームの回帰に加え、状態・閾値のないRangeClamp、状態と合成外部APIを持つSampleHold_Update、異なるケース件数を使用した。RangeClampはフル仕様JSON→新規AI生成C90→UT仕様JSON→Wordの来歴を接続した。SampleHoldの外部APIはホスト試験用の合成契約であり、実機APIではない。

WordのOOXML構造・内容・書式照合、C90ホスト試験と、Bobチャットでのスキル検出、全ページ表示確認、正式コンパイラ/RTOS/DLL結合、実機WCET、仕様の人手承認は別の検証である。後者は今回未確認。汎用化はあらゆるC宣言や任意の外部文書形式の自動解釈を保証しない。正式API、ABI、共有状態、割込み・ロック、実行時間予算は案件ごとに指定する。

各元キットのdistribution.jsonを`manifests/`に保存し、統合distribution.jsonとZIPのchecksumsで照合する。個別ZIPと旧版ZIPを保存し、保守時は各キットの封印・試験を完了してから`tools/manage.py build`で統合する。

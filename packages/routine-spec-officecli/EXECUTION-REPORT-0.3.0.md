# プログラム仕様書キット 0.3.0 実行記録

2026年11月17日にCodexの直接CLI経路で実施した。Python 3.12.14は`-X utf8 -S -B`、追加依存なし。OfficeCLI 1.0.144の実体SHA-256を固定した。Bobチャットからのスキル検出・実起動は未確認。

フルJSON0.1.0/0.2.0の形を維持し、任意のルーチン名・ID・配列件数に対応した。型定義と状態、引数などの空を表示viewだけで扱い、正本のバイト列を維持した。thresholdを任意にし、behavior.configurationの有限JSON値と意味を全文表示する。条件表はconditionと残る全項目のkey/value表示へ変更した。旧old_count等の必須条件を外した。状態とラベルは正本に従い、人の承認を作らない。

`new-job --spec FILE`は検証した任意のフル正本を取り込む。未指定時は`--routine-name/--routine-id/--document-id`の識別情報だけを持つ未記入スケルトンを作り、内容が埋まるまでvalidate/renderを拒否する。業務規則を自動補完しない。

新版routine-spec-v02は旧A4テンプレートから26件のOfficeCLI命令で保守工程に一度作成し、構造検査に成功した。通常の作者処理ではテンプレートを作らない。旧v01テンプレートとAlarm正本、旧0.2.0 ZIPを変更していない。旧v01入力は新版の汎用表示へ適合させる。

実OfficeCLIを使った21テストが全件成功した。RangeClampの空状態・空型・閾値なし、SampleHoldの合成API/state/configurationと異なる件数、最小スケルトン、全配列0件の引数なし関数、任意ID、関数改名、literalタグ、JSON値、改行、繰返し、重複ID・未知項目・非有限値・XML禁止文字・改変資材・改変ロック・改変guard・パス逸脱・上書き・置換0件の拒否を確認した。Windowsの一時rename拒否の回復、ページフィールド、用紙/書式/非変更部品の照合も確認した。

最終releaseに対するRangeClamp、SampleHold、Alarmの3文書を実際に生成した。全て内容/書式/非変更部品の照合、OfficeCLIのOOXML構造検査、closeに成功した。SampleHoldは提供された合成APIとmockの契約だけを展開したfixture_onlyであり、実RTOSの仕様ではない。

配布ZIPの全17ファイルとdistributionハッシュを照合し、別の.bob配置へ展開してdoctor、新規正本取込み、validateに成功した。スキルと新規案件の`.gitattributes`は`* -text`で、資材ロックとguard改変拒否も確認した。新ZIPとreleaseのハッシュ、各出力のハッシュと命令数はverification.jsonに記録した。

全ページの表示確認は実施していない。自動照合と構造検査の成功を、仕様意味の承認、表示品質、Bobチャット起動、C90/実RTOS/WCETの試験合格として扱わない。

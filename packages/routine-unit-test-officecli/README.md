# 汎用単体テスト仕様書キット 0.2.0

プログラム仕様JSONとC/Hの実byteを案件ごとに固定し、汎用単体テストJSONからOfficeCLI 1.0.144でWordを生成するIBM Bob向けスキル。Python 3.12標準ライブラリのみ。任意のルーチン・ID・有限JSON値・可変件数を扱い、特定業務のハッシュやケース数を固定しない。

配布ZIPの.bob/skills/routine-unit-test-specと.bob/rulesをBobプロジェクトに展開する。実行方法はskills/routine-unit-test-spec/SKILL.mdを参照。0.2.0/0.1.0コードjob.jsonから入力を読むか、明示spec/C/Hを渡す。UT正本未指定なら未記入スケルトンで止まり、原仕様から作者が確認項目を定める。

旧0.1.0 ZIP、旧テンプレート、元のAlarm入力例は再現資料として保持する。現在の生成契約はschema0.2.0/template unit-test-spec-v02であり、旧正本は旧ZIPで再現する。新規例はrange-clampとsample-hold。

構造検査と全内容/書式照合を行う。表示確認や試験の合格を自動で宣言せず、新規項目は全て未実施。Bob起動、全ページ表示、正式RTOS/コンパイラ/WCETは別の確認である。

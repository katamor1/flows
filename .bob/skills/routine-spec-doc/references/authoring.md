# フルJSON正本の記述

`describe`が示す固定スキーマとRangeClamp記述例を参照する。既存Alarm例も回帰用として保持する。任意の関数名、文書ID、閾値、項目数に対応し、アプリ固有の意味・エラーを追加しない。

- documentは文書とルーチンの識別情報、版、日付、作者、入力由来の状態を記す。ツールは承認を作らない。
- overviewは目的、担当範囲、原要求と所在、担当する要求範囲を記す。
- trial_assumptions、constraints、behavior.steps、verification_examples、open_issuesのIDは各配列内で一意にする。任意の文字列IDを使える。
- interfaceは言語、可視性、正確なプロトタイプ、型定義、引数、戻り値、呼出し前提を記す。型定義は空文字可、引数/戻り値表は0件可。スカラー戻り値もreturn_codesのvalue/meaningで表せる。
- behaviorのstate_fields/result_fields/steps/decision_rowsは0件可。state_fieldsのtypeを含め全内容をWordに表示する。
- behavior.thresholdは任意の数値。behavior.configurationは任意の{name,value,meaning}配列で、valueはnullを含む有限JSON値。条件表はcondition以外のキーも全てkey/valueで出す。JSON値を式として実行しない。
- verification_examplesは仕様確認の例であり、実行済試験結果ではない。traceabilityは要求、仕様、確認先を記す。
- assumptions/open_issuesが0件でも、正本へ表示用ダミーを足さない。viewだけが「該当なし」を出す。

schema_versionは0.1.0または0.2.0。template_idはroutine-spec-v02を使い、旧routine-spec-v01も新版汎用表示で受け付ける。未知のフィールド、未対応Schemaキーワード、非有限JSON、XML禁止文字は拒否する。スキーマは使用するJSON Schemaキーワードを限定し、完全なDraft2020-12実装ではない。

`new-job --spec FILE`は検証済の入力バイト列をそのまま取り込む。未指定なら未記入スケルトンを作る。必須説明やプロトタイプを埋めるまでvalidate/renderは通らない。既存正本の状態と意味を勝手に変更しない。

固定資材は通常の作者が編集しない。ロックは誤変更検知であり、書込み権限の制御ではない。旧ロックを上書きして移行せず、新案件を作り差分を確認する。スキルと案件の.gitattributesは`* -text`を保持する。入力ハッシュは正本のバイト列に対する値で、表示viewを含めない。

構造、全内容、書式、フィールド、非変更部品と置換件数を自動照合する。全ページ表示、仕様意味、人の承認、実コード試験、RTOS/WCETは別に確認する。

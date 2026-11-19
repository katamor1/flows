# IBM Bob向け C90コード生成スキル 0.2.0

JSONのプログラム仕様から、既存RTOS上で動くWindows DLLのC90ルーチンを作るスキル。固定ツールが入力・ヘッダ・提供試験の固定、世代別の生成記録、ホスト検証を担当し、AIが業務ロジックと仕様対応表を作る。

0.2.0では関数名・ファイル名・仕様ハッシュ・チェック数のサンプル固定を外す。共通インターフェイスを持つ任意のJSON正本を新規jobへ準備でき、独立試験は任意の検証プロファイルとして指定する。試験なしの結果は `compiled_only` とし、機能試験合格とは区別する。

## チームへの配置と依頼例

ZIPの `.bob/skills/routine-code-c90/` をプロジェクトへ取り込む。既存 `.bob` 全体は置換せず、同じGit版をチームで共有する。グローバル設定、MCP、認証、自動承認設定の変更は不要。前段のWord仕様書と同じJSON正本を入力にし、このコード生成工程ではOfficeCLIを使わない。

Bobの新しい会話で、例えば次のように依頼する。

> routine-code-c90スキルで、このJSON正本からC90ルーチンを作成してください。新規jobに入力とヘッダを固定し、提供した検証プロファイルがあれば独立試験も固定してください。本体・仕様対応表・実際の生成記録・ホスト検証結果を残し、試験未提供ならcompiled_onlyと明記してください。RTOS APIやDLL ABIは提示した正式契約に従い、未提示の契約は未決として残してください。

入口は [SKILL.md](skills/routine-code-c90/SKILL.md)。必要な参照先を選んで読む。

- [入力と実行手順](skills/routine-code-c90/references/workflow.md)：共通JSON項目、prepare/record/verify、サンプルコマンド。
- [検証プロファイル](skills/routine-code-c90/references/verification-profile.md)：提供ヘッダ・試験・サポート・許可シンボルと、結果の意味。
- [実装とレビュー](skills/routine-code-c90/references/implementation.md)：C90、状態、外部API、正式環境の契約。
- [旧アラーム案件からの移行](skills/routine-code-c90/references/alarm-profile.md)：0.1.0の証跡を保存して新規jobを作る。

## 入力・固定資産・サンプル

必須のJSON項目は `document.id/routine_id/routine_name/status` と `interface.language=C90`、`interface.prototype`、`interface.type_definitions`（空文字可）。その他の仕様構造は原文のまま保存する。`routine_name` からC/Hの標準パスを決め、固定テンプレートから型・宣言を一度展開してヘッダを凍結する。prepare成功だけで仕様の完全性や動作を保証しない。

従来のフル仕様も、状態なし・型定義空の最小仕様も受け入れる。コード生成だけならprofileは不要で、任意ルーチンを準備できる。入力ハッシュの製品全体の制限を廃止し、jobごとの正本・固定資産の改変検知を維持する。

profileを指定すると元JSON、提供ヘッダ、独立試験、サポートソースをjobへコピーしてハッシュ固定する。targetの関数名・仕様SHA-256で誤適用を防ぎ、サンプルの許可ハッシュ一覧は使わない。本体と対応表以外の固定資産・ロックを検査に合わせて変更しない。仕様・依存契約・試験の改訂は新規jobとして扱う。

`assets/examples/range-clamp/` はステートレスな `RangeClamp`、`assets/examples/sample-hold/` は状態と外部APIを使う `SampleHold_Update` の試験例。後者のAPIとモックは合成ホスト試験専用であり、実RTOSの正式APIとして配布・承認するものではない。旧アラーム資産も、その仕様に対応する試験例として扱う。完成済みのルーチン本体をprepareで配布しない。

同一jobの編集・record・verifyは直列に行い、複数担当はjobを分ける。修正後は新しいgeneration/run IDを使い、既存記録を上書きしない。verifyはスナップショットのコピーをコンパイルし、実際の成功・失敗を記録する。記録とハッシュは来歴・誤変更の検出手段であり、署名や権限制御ではない。

## 検証範囲と版管理

Python 3.12、Clangと同じフォルダのllvm-nmを使う固定C90ホスト検証器で、UTF-8のC/HをO0/O2で確認する。試験ありは提供試験の実行結果を記録し、試験なしはオブジェクト検査までの `compiled_only` / `test_execution=not_provided` とする。期待チェック数・しきい値・状態の有無等を汎用ランタイムへ固定しない。

Python、Clang、ホスト用リンカー/SDK、正式RTOS SDK等の実行環境は同梱しない。提供されていないRTOS API、DLL ABI、呼出し規約、実行時間予算を生成しない。ホスト試験から正式コンパイラ・RTOS結合・実機WCETの合格を導かず、チームの正式手順で別途検証する。

検証の実績は配布ZIP外の `verification/` と各案件の `qa/` に記録する。対象版・入力・本体・実行条件が一致する記録を根拠にし、0.1.0の実績を0.2.0の実行結果へ読み替えない。Bob IDEでのスキル検出・起動は未実行で、別のチーム受入項目として残る。

旧 `ibm-bob-routine-code-c90-0.1.0.zip` とその実績を保存し、0.2.0は別ZIP・新規jobとして扱う。配布ZIPを作る `tools/release.py seal` / `bundle` は保守用で、通常の生成作業では実行しない。固定配布物を変更した場合は保守担当が新版として封印・配置する。

配置方式の参照元は [IBM Bob Skills公式資料](https://bob.ibm.com/docs/ide/features/skills)（2026-11-16確認）。`distribution.json` は配布来歴でありプラグインmanifestではない。

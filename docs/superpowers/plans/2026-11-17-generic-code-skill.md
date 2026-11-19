# C90コード生成スキルの汎用化

User request: 現在サンプルに固定されているものを汎用化。利用者は3工程全てを指定済み。共通契約は2026-11-17-generic-three-stage-contract.md。本書はそのうちのコード生成部分。

## 目的と境界

routine-code-c90 0.2.0では、関数名・ファイル名・入力ハッシュ・期待チェック数のサンプル固定をランタイムから除く。C90/RTOSの制約は維持する。旧0.1.0 ZIPと実績は保存し、新版の案件は新規jobとして作る。提供されていないRTOS API、DLL ABI、実行時間予算は生成しない。

## 共通契約

- prepare入力はJSON正本。必須はdocument.id/routine_id/routine_name/status、interface.language=C90、interface.prototype、interface.type_definitions（空文字可）。その他の仕様項目は原文のまま保存する。
- 関数名はC識別子。include/<routine_name>.h と src/<routine_name>.cを標準パスとし、固定ヘッダテンプレートから型・宣言を一度展開して凍結する。本体はAIが作る。
- prepare時に任意の --verification-profile FILE を指定する。未指定なら試験なしのコンパイル検証。指定したprofileの元ファイル、ヘッダ、試験、サポートソースはjobへコピーしてハッシュ固定する。
- profile JSON 0.2.0: name, target {routine_name,spec_sha256}, headers[{source,target}], test_sources:[path], support_sources:[path], defines:[str], allowed_undefined_symbols:[str], allowed_public_symbols:[str]。相対sourceはprofile所在地基準。headers.targetはinclude/配下の相対パス。targetにより別仕様の試験の誤適用を拒否する。プロファイル自体はどの関数・どのハッシュでも宣言可能で、サンプル許可リストは使わない。
- 外部コマンドやPython式はprofileで指定できない。verifyは指定されたClangと同じフォルダのllvm-nmを使う固定C90ホスト検証器。正式RTOSビルドは別途チームの正式手順で行う。
- job.json 0.2.0: spec/spec_sha256/header/source、routine_id/routine_name、profile、tests/support_sources/headers（job相対パス）、allowed_undefined_symbols/allowed_public_symbols/defines、generation_record。recordは従来と同じinput_spec_sha256/source_sha256/header_sha256を持ち、複数の試験・依存資産はfile_hashesで表す。
- record/verifyは同じjob内で排他し、入力・固定ヘッダ・試験の改変、世代/run上書きを拒否する。コード修正後は新世代を記録する。
- verifyは入力と本体を検証し、スナップショットを作ってそのコピーをコンパイルする。実行中の変更を合格にしない。QA runには成功/失敗とも実際の結果を記録する。
- 試験あり: O0/O2の独立テストを実行しpassed/failed。試験なし: O0/O2のオブジェクト検査まででcompiled_only、test_execution=not_provided。実行したコマンド、ツール版、ハッシュ、実結果を記録する。
- サンプル由来のtest_count、threshold、ASM/P/CONの個数・戻り値・共有状態の有無は判定ロジックへ埋め込まない。仕様とプロファイルを根拠にレビューする。

## 作業分担と受入

- [ ] 既存実装が未知の仕様を拒否する赤を確認する。
- [ ] 固定ランタイムとヘッダテンプレートを汎用化する。
- [ ] アラーム以外のステートレスRangeClamp、状態/外部APIを持つ合成テスト用ルーチン、旧アラームの3種類で検証する。
- [ ] 未指定試験のcompiled_only、他仕様へのprofile誤適用、改変、再記録、上書き、外部シンボル許可/拒否、配布先の実行を確認する。
- [ ] スキル/プロジェクト設定例/READMEを改訂し、新版ZIPとプロジェクト配置を更新する。
- [ ] 別コンテキストのエージェントが非アラーム仕様で生成・検証し、独立レビューする。

合成APIは試験専用で、実RTOSのAPIとして配布/承認しない。多ルーチンの機能正当性・実機WCET・ABI・Bob IDE実起動を今回のホスト試験から保証しない。

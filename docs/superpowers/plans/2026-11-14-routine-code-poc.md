# 1ルーチンC90ソース生成PoC Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans to execute this authorized PoC. Independent specification-based acceptance tests are delegated; production writes remain with the primary agent.

**Goal:** 納品済みプログラム仕様書1件から、C90の実装と再現可能なホスト検証結果を作る。

**Architecture:** JSON正本をコピーしてSHA-256で固定する。AIがヘッダと関数本体を作り、固定Pythonスクリプトが入力整合性検査、厳格C90コンパイル、独立受入試験、オブジェクトの外部依存検査を行う。Bobでの再実施用指示書を添付する。

**Tech Stack:** C90, Clang 22.1.3 (Windows x64), Python 3.12 standard library, JSON, IBM Bob IDE向けMarkdown指示。

**Spec:** artifacts/routine-spec-officecli/alarm-officecli/source/spec.json (SHA-256 097b1185e284c17805b51c92dd821d1bec64f55d0ce1781c2c1fb369239b4265)

## Global Constraints

- 関数と型のインターフェイスは正本どおり。DLL内部、エクスポートしない。
- RTOS/Win32/ファイル/時刻/レジスタ/ロックAPI、ループ、動的確保、再帰、静的共有状態を本体に加えない。
- 試作仕様の未承認仮定を引き継ぐ。WCET、正式コンパイラ、RTOS結合は今回の検証対象外。
- 独立試験は prototypes/routine-code-poc/tests と qa/test-design.md のみ別エージェントが作成する。
- 今回の生成実行者はCodex。Bob Shell 2.0.4は存在するがBOB_API_KEYなし。Bob実行を実績として記載しない。

## Review Focus

- sample_valid=0時、任意signal_onを無視する。
- 複合エラーを-1/-2/-3の優先順で返し、有効な領域を更新しない。
- 10回目だけイベント、継続ONで飽和、OFF/無効で再成立できる。
- 複数インスタンスの非干渉と、呼出し側所有権の前提。
- ホスト試験成功を実機の実行時間・ABI保証と誤認しない。

## Tasks

- [x] 入力スナップショット、ハッシュロック、実行指示、固定検証スクリプトを用意する。
- [x] 独立試験を本体実装前に確定し、未実装スタブで期待どおり失敗することを記録する。
- [x] 正本から .h / .c を生成し、同じ試験を通す。
- [x] オブジェクト検査と独立レビューで制約・仕様対応を確認する。
- [x] 入力からソース、検証結果までをREADME・対応表・ZIPで納品する。

## Completion evidence

- 最終ホスト検証: prototypes/routine-code-poc/qa/green-r003/verification.json。O0/O2とも各1,948,941チェック、失敗0。
- 配布: artifacts/routine-code-poc/RTN-ALM-001-code-poc-0.1.0.zip (58,416 bytes、83 entries、SHA-256 b0ddb1e6eb9e179e5575cea70d57c0e3d29bda3f96e1eaaad56e033841e74789)。全収録ファイル読み戻し照合成功。
- 展開後検証: artifacts/routine-code-poc/distribution-check.json。O0/O2再実行合格、正本・本体・試験・ヘッダ変更を各検出、既存run上書き拒否と記録不変を確認。
- Bob実行、正式コンパイラ、RTOS結合と時間計測、業務仮定の承認は今回の達成範囲外として記載済み。

## Sources checked 2026-11-14

- https://bob.ibm.com/docs/shell/getting-started/start-bobshell-non-interactive : bob runはBOB_API_KEYが必要。IDEのSSO認証とは別。
- https://clang.llvm.org/docs/UsersManual.html : 明示的な標準モードと-pedantic-errorsで後続標準の拡張を診断する。

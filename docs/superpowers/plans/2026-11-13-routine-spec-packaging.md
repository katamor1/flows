# Routine Spec Kit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 固定した仕様書変換資材を再生成せず、別の案件データから再利用できる配布物を作る。

**Architecture:** 利用者用CLIと固定資材を自己完結したスキルへ同梱する。原型の初期化・書式作成コードは配布しない。MCPとプラグイン配布は設計に留め、共通本体の重複を避ける。

**Tech Stack:** Python 3.12、python-docx 1.2.0、lxml 6.1.1、JSON、DOCX、PowerShell。

**Spec:** `docs/research/2026-11-13-routine-spec-packaging.md`

## Global Constraints

- 10周期ON判定のdraft_trialプロファイルに限定する。
- 既存試作の正本・スキーマ・テンプレート・出力を変更しない。
- 通常処理に資材生成、依存インストール、任意実行コマンドを含めない。
- 今回はワークスペース内に配布物を作り、グローバル導入、ACL変更、Gitへのcommit/pushを行わない。
- CLIの追加実装は主担当が行い、評価は隔離した案件領域で行う。

## Review Focus

- 資材が欠落・変更された場合、復元生成せず停止する。
- 同名案件・展開IDへの再実行で既存ファイルを変更しない。
- パッケージ配下、`..`、リンク経由を出力先として使わない。
- 異なる配布版や依存環境で、ロックを無視して続行しない。
- 正常なJSONがWord生成の失敗に遭遇した場合、完成成果物のような残骸を公開しない。

### Task 1: 固定本体と利用者CLI

**Files:** `packages/routine-spec-kit/skills/routine-spec-doc/scripts/{specflow.py,_engine.py}`、同階層の`assets/`・`release.json`・`requirements.txt`、`packages/routine-spec-kit/tests/test_package.py`

**Interfaces:** `specflow.py doctor|describe|new-job|validate|render`。案件の`package-lock.json`でrelease.jsonを固定し、`render`は新規展開IDだけを許可する。

- [x] 新規案件作成・同一入力再生成・固定資材検査・上書き拒否・境界検査・版固定を試すテストを先に書く。
- [x] CLI未実装でテストが失敗することを確認する。
- [x] 検証・差込み部分だけ既存実装から取り出し、固定資材と利用者CLIを実装する。
- [x] 全テストと原型DOCXとのバイト一致を確認する。12件中11件成功、ジャンクション作成が環境で拒否された1件は未実施。

### Task 2: スキルと配布

**Files:** 同スキルの`SKILL.md`・`references/authoring.md`、パッケージの`README.md`、保守用`tools/release.py`、検証記録。

**Interfaces:** スキルは固定CLIを使い、正本だけを案件ごとに編集する。`release.py`は保守者がハッシュ一覧とZIPを作る入口で、利用者スキルには含めない。

- [x] スキル無しの5ケースの判断を記録する。
- [x] 再生成を誘発する箇所をCLI制限と短いスキルに置き換える。
- [x] スキルの使用構文と、別担当による新規案件からの再利用・異常時の判断を確認する。公式構文検査器の未実施理由は下記に記録。
- [x] 配布ZIPを展開した場所から実行し、検査記録と配布物一覧を確定する。

## Progress / Rulings

- 作業は主担当が継続し、独立した評価だけサブエージェントへ依頼する。ユーザーの継続指示に基づき、この小規模パッケージ化を実行する。
- 専用の新規`packages/routine-spec-kit`配下を使用し、既存試作は保守用原型として維持する。
- 一時領域の既定場所では後始末が権限エラーとなったため、検査用一時領域をパッケージの`qa/temp`へ固定した。利用者CLIの仕様は変更しない。
- 通常例外で排他ファイルが残る不具合を再現する検査を追加し、後始末を修正した。保守用bundleの整合性検査も、最適化実行で無効にならない明示的な例外へ変更した。
- スキル公式構文検査器はPyYAML未配置で起動できなかった。実際に使う単純な2項目のYAMLフロントマター・名前・説明・参照先を別途検査した。公式検査器の成功とは扱わない。
- 独立したZIP利用試験で、新規案件作成から文書版0.2のWord展開まで成功した。テンプレート欠落・閾値12・既存展開IDでは停止し、ガウスフィルタは対応外として改訂作業へ分ける判断を確認した。主担当も入力・出力のハッシュ、Word XMLの版、固定資材の不変を再確認した。
- 結果は`packages/routine-spec-kit/verification.json`、詳細は同`qa/forward-evaluation.json`。配布ZIPは10ファイル、56,385バイト。スクリプト・テンプレート・スキーマを案件ごとに再生成しない通常経路を検証した。

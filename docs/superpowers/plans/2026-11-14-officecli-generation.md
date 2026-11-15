# OfficeCLI Generation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** JSON正本からWord生成・OOXML検査までを、IBM Bob同梱OfficeCLIを使う固定フローへ統一する。

**Architecture:** Python標準ライブラリは正本検証、テンプレートの読取り、OfficeCLI命令列の生成、結果照合を行う。DOCX内部への書込みはOfficeCLIだけが行う。既存の固定テンプレート・スキーマ・記述例を再利用し、繰返し行の複製と値差込みを固定アダプターへ実装する。

**Tech Stack:** IBM Bob IDE 2.2.3同梱OfficeCLI 1.0.144、Python 3.12標準ライブラリ、JSON、DOCX、Git配布。

**Spec:** 2026-11-14の利用者指示「生成まで統一」。既存の `docs/research/2026-11-14-ibm-bob-team-distribution-plan.md` のOfficeCLIアダプター段階を実施する。

## Global Constraints

- 正本の内容と10周期判定draft_trialの範囲を変更しない。
- python-docx、lxml、Word COM等を生成処理で使用しない。DOCXはOfficeCLIが編集する。
- テンプレート・正本契約を案件ごとに再生成しない。旧配布物は保持し、新版を別ディレクトリに作る。
- OfficeCLI実体は利用者が明示した絶対パスで固定し、版とSHA-256を記録する。勝手な取得・更新は行わない。
- 生成失敗・検証失敗時は完成出力を公開せず、既存出力を上書きしない。
- Bob IDEのスキル実起動はCLI直接実行と区別して報告する。

## Review Focus

- セル・表・段落・ヘッダ・フッタの差込みが他の行の値へ誤爆しないこと。
- 改行、引用符、XML文字、トークンに似た入力文字列をデータとして扱うこと。
- 原型行の書式、行順序、ページ番号フィールドが保持されること。
- OfficeCLIの成功終了とJSON結果の成功・全命令完了を両方確認すること。
- 実際のOOXML検査とページ表示確認を行い、内容検査だけで完了としないこと。

### Task 1: 固定生成アダプター

**Files:** `packages/routine-spec-officecli/skills/routine-spec-doc/scripts/`、同`assets/`、`tests/test_flow.py`。

**Interfaces:** `specflow.py doctor|describe|new-job|validate|render --officecli <absolute-exe>`。`render`は命令列・OfficeCLI応答・検査結果・manifestを残す。

- [x] 同梱OfficeCLIの行複製・値差込みを隔離したコピーで実証する。
- [x] 新しい生成経路の受入テストを先に書き、未実装で失敗を確認する。
- [x] 標準ライブラリだけの検証と固定アダプターを実装する。
- [x] 内容・表行数・書式・ページフィールド・失敗時後始末を検査する。

### Task 2: 文書検査とBob配布新版

**Files:** 同パッケージの `README.md`、`SKILL.md`、保守用配布処理、出力DOCX、検証記録、設計文書の追記。

- [x] OfficeCLIによるOOXML構造検査を成功させる。
- [x] 出力をページ画像として描画し、全ページを確認する。
- [x] Python依存ライブラリを含まないBob配布ZIPを作り、展開先から実行する。
- [x] 独立レビューと残る制限を記録する。

## Initial evidence

- 同梱CLI: `C:/Users/stell/AppData/Local/Programs/IBM Bob/resources/app/extensions/bob-code/dist/officecli.exe`。
- OfficeCLI版: `1.0.144`、SHA-256: `eec03daa7978a1e8f28a4ee0ce910ef9e3cb355d26a7fa4afcecadfe34693fbb`。
- IDE: `1.126.0+bob2.2.3`。Bob Shellにも同版のOfficeCLIがあるが、今回はIDEの実体を使う。

## Results / Rulings

- 旧テンプレートの164件のOOXML不整合を、一度限りのOfficeCLI保守修正で0件にした。内容・全トークン・表・ページフィールドを保持し、修正版を固定資材に採用。
- validateの自動residentによるロックを再現し、新規自動起動を抑止してfinally closeする。任意の待機で回避しない。
- 独立レビューでsectPrと非変更部品の検査不足を指摘され、ページ設定・styles・relationships等の照合を追加した。負例で検出を確認し、再レビューで解消。
- 自動13件成功、配布ZIPの独立利用17項目合格。Word UI→PDF→ページ画像で全4ページを確認した。
- OfficeCLIのPDF exporter/native描画はこの環境で使えなかったため、表示確認だけWord UIを利用。生成・構造検査はOfficeCLIで完結。
- Bobチャットからのスキル起動、実RTOS接続、C90実装・性能試験は範囲外。現行成果物は0.2.0と検証記録を参照。

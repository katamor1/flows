# IBM Bob Distribution Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 既検証の仕様書生成器をIBM Bobの公式スキル配置へ収容し、チーム受入試験用の配布候補と運用計画を作る。

**Architecture:** 既存のスキル・生成器・資材はバイト単位で再利用し、Bob向けルールと導入説明を添えてZIP化する。初回の生成は固定Python生成器、Bob同梱OfficeCLIは読取り・OOXML構造検査に利用する計画。OfficeCLIレンダラーへの移行は独自の繰返し表契約への対応後とする。

**Tech Stack:** IBM Bob project skills/rules、既存Python 3.12生成器、JSON、DOCX、Git、Bob標準Officeツール。

**Spec:** `docs/research/2026-11-14-ibm-bob-team-distribution-plan.md`

## Global Constraints

- IBM Bob IDEと同梱OfficeCLIをチームの利用前提とする。
- 既存routine-spec-kit 0.1.0の固定資材と生成処理を変更・再生成しない。
- 配布候補は10周期ON判定のdraft_trialに限定する。
- 実際のBobへの配置、設定・自動承認の変更、OfficeCLIの追加導入、Git commit/pushは行わない。
- BobのOfficeツールと、同梱CLI実体への直接アクセスを区別する。未確認の実体パスやプラグイン形式を指定しない。

## Review Focus

- ZIPが公式 `.bob/skills/` と `.bob/rules/` の配置を持つこと。
- 既存 `.bob/settings.json` 等を含めず、共有設定を置換しないこと。
- 固定資材のハッシュ・配布版を照合してから梱包すること。
- `.bob` 配下への配置後も案件をその外へ作成し、元のWordが再現されること。
- ローカル生成器の試験とBobでの受入試験の未実施を明確に区別すること。

### Task 1: Bob配布候補と運用文書

**Files:** `packages/ibm-bob-routine-spec-pilot/{README.md,content/20-routine-spec.md,tools/package.py,tests/test_distribution.py}` と設計文書。

**Interfaces:** `python tools/package.py` は検証済の既存スキルを `.bob/skills/routine-spec-doc/` へ梱包し、ルール、説明、配布来歴を付ける。通常のBob作業では梱包スクリプトを使わない。

- [x] 公式資料でスキル・ルール配置とOfficeツールの公開範囲を確認する。
- [x] ZIP配置・資材一致・再配置後の生成を検査するテストを先に書き、未実装で失敗を確認する。
- [x] 固定資材を再生成しない梱包処理と、Bobでの導入・受入手順を作成する。
- [x] ZIP展開から通常CLIを実行し、元のDOCXとハッシュが一致することを確認する。
- [x] Bob実機のスキル起動・OfficeCLI構造検査等は未実施として記録する。

## Rulings

- プロジェクトのGit配布を初回の標準とする。Bobのグローバルプラグインは公式変更履歴で存在を確認したが、詳細な配布形式とチーム採用版での動作は別途確認する。
- 標準mergeだけでは独自captionを使った繰返し行を展開できないため、既検証の生成器を初回から置換しない。
- ZIP配置・元資材一致・doctor→new-job→validate→render・資材不変の一連検査が成功した。元DOCXのSHA-256 `99f478ddc1f1f54bae1b1f003e401bf92d3bd20471349e654cfc466b8220667f` と一致。
- 独立した資料調査担当が設計文書と配布READMEを確認し、公式保証範囲を越える重要指摘は0件。実際のBob実行の代わりとは扱わない。

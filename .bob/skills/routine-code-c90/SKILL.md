---
name: routine-code-c90
description: Use when generating or revising C90 routines for an RTOS-hosted Windows DLL from machine-readable program specifications in IBM Bob.
---

# プログラム仕様書からC90ルーチンを作る

0.2.0。JSON正本からルーチン本体と仕様対応表を作り、入力・生成AI・実際のホスト検証結果を追跡する。関数名や仕様ハッシュを特定サンプルに限定しない。

## 進め方

1. JSON正本と、関数・型・引数・処理順序・状態・エラー・時間・排他の契約を読む。準備に必要な共通項目は [入力と実行手順](references/workflow.md) を参照。準備成功は業務仕様の完全性を証明しない。欠落や矛盾は具体的に残し、試作仕様を製品承認済みに変更しない。
2. [実装とレビューの指針](references/implementation.md) を使い、指定範囲を実装する。RTOS APIやDLL ABIを使う部分は提供された正式契約に従う。未提示のSDK、呼出し規約、実行時間予算を推測せず、独立して進められる部分を進める。
3. 固定 `scripts/codegen.py prepare` で新規jobを作る。`document.routine_name` から `include/<routine_name>.h` と `src/<routine_name>.c` を決め、型・宣言を展開したヘッダを凍結する。AIは本体と `traceability.md` を作る。
4. 提供済みの独立試験があれば、[検証プロファイルの契約](references/verification-profile.md) を確認して `--verification-profile` を指定する。未指定でもO0/O2のホストコンパイル・オブジェクト検査を行い、結果は `compiled_only`、`test_execution=not_provided` とする。
5. [実行手順](references/workflow.md) に従って実際の生成環境を `record` に記録し、`verify` を実行する。本体修正後は新しいgeneration/run IDを使う。同一jobの編集・record・verifyは順番に行い、複数担当はjobを分ける。

## 固定するものと報告

`input/`、生成ヘッダ、提供試験・サポート資産、job契約とロックを検査に合わせて変更しない。仕様・契約・試験を改訂する場合は新規jobへ準備し、既存記録を残す。ループ・共有状態・外部APIの可否は対象仕様で判断し、アラーム例の制約を一般化しない。

完了時はソース/ヘッダ、対応表、入力版・ハッシュ、生成AI、実行コマンド・結果・未決事項を示す。試験ありの `passed` と試験なしの `compiled_only` を区別する。ホスト結果から正式コンパイラ・DLL ABI・RTOS結合・実機WCETの合格を主張しない。Bob実行は実態どおりに記録する。

旧0.1.0の案件を扱う場合だけ [旧アラーム案件からの移行](references/alarm-profile.md) を読む。単体テスト仕様書の納品文書作成は別工程で扱う。

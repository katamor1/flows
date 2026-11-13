---
name: routine-spec-doc
description: Use when drafting or revising routine-level program specifications for a C90 RTOS control DLL and preparing Word documents with an existing routine-spec-kit profile, especially the 10-cycle continuous-ON alarm qualification example.
---

# ルーチン仕様書の正本作成とWord展開

同梱CLIと固定資材を利用する。案件ごとに作成・編集するのはパッケージ外のJSON正本と確認記録である。

最初に、このスキルのディレクトリを基準に `scripts/specflow.py doctor` と `describe` を、利用可能なPython 3.12の実行ファイルで実行する。以下の `<python>` はその実行ファイル、`<skill>` はこのディレクトリの絶対パスへ置き換える。

```powershell
& '<python>' -B '<skill>/scripts/specflow.py' doctor
& '<python>' -B '<skill>/scripts/specflow.py' describe
& '<python>' -B '<skill>/scripts/specflow.py' new-job --workspace '<案件ルート>' --job alarm-01
```

`new-job` が返す `source/spec.json` を管理正本として編集する。記述方法と対応範囲は [references/authoring.md](references/authoring.md) を必要時に読む。既存案件では新規作成せず、その正本と `package-lock.json` を使う。

```powershell
& '<python>' -B '<skill>/scripts/specflow.py' validate --workspace '<案件ルート>' --job alarm-01
& '<python>' -B '<skill>/scripts/specflow.py' render --workspace '<案件ルート>' --job alarm-01 --run r001
```

次の展開は新しい `--run` を指定する。生成Wordへの確認コメントや修正案は正本・確認記録へ戻す。manifestは展開時の入力と利用資材を記録する。

資材欠落・ハッシュ不一致・依存版不一致では、その理由と必要な配布版を示して停止する。スクリプト、スキーマ、テンプレート、release.jsonを通常作業で再生成・修正せず、別の変換実装へ置き換えない。環境が未整備なら依存導入を管理する担当へ戻す。

この版は `alarm-qualification-v01`、10周期ON判定、`draft_trial` に限定する。12周期判定やガウスフィルタ等は未対応として要求・不足項目を整理し、別途プロファイル改訂が認められた作業へ分ける。検証を通す目的で契約を緩めたり、状態を承認済にしない。RTOSのAPI名・時間予算・業務動作を推測で確定せず、前提または未決事項に残す。

CLIはWordの表示確認を行わない。文量・表の行数が変わった場合は、利用環境での表示確認結果も報告する。生成成功を仕様承認や制御コードの試験合格として報告しない。

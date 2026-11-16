# IBM Bob向け C90コード生成スキル 0.1.0

プログラム仕様書から、既存RTOS上で動くWindows DLLのC90ルーチンを作成するためのスキル。固定ツールは準備・生成記録・検証を担当し、業務ロジックはAIが仕様から作る。

一般のルーチン向けの判断手順と、既存のアラーム判定PoCを再現する自動検証プロファイルを含む。初版の自動検証は既知の仕様ハッシュだけに対応する。別ルーチンのSDK・試験・実行時間を検証済みとはしない。

## チームへの配置

ZIPの `.bob/skills/routine-code-c90/` をプロジェクトへ取り込む。既存 `.bob` 全体は置換しない。チームは同じGit版を共有する。グローバル設定、MCP、認証、自動承認設定の変更は不要。OfficeCLIはこのコード生成工程では使用せず、前段のWord仕様書と同じJSON正本を入力にする。

Bobの新しい会話で、例えば次のように依頼する。

> routine-code-c90スキルで、このプログラム仕様JSONからC90ルーチンを作成してください。固定ツールと独立試験を再利用し、入力を固定した新規jobを作り、生成記録・仕様対応表・ホスト検証結果を残してください。RTOS APIやDLLの公開方式は指定資料に従い、不明点は推測で補完しないでください。

スキル本体は [SKILL.md](skills/routine-code-c90/SKILL.md)、実行コマンドは [alarm-profile.md](skills/routine-code-c90/references/alarm-profile.md) を参照。AIが通常変更するのは生成本体と仕様対応表。固定資産の改訂は保守担当が別版として行う。

## 再利用する資産

既存 `prototypes/routine-code-poc` の正本、ヘッダ、独立試験、未実装スタブ、`codeflow.py` をそのまま収録する。完成済みの本体は含めない。新規jobへコピーされる検証器は前回PoCと同一バイト列である。`codegen.py` はコピー資産のハッシュ、世代別生成記録、上書き拒否を追加する薄い入口である。

Python/Clang/Windows SDK/OfficeCLI等の実行環境は同梱しない。固定スクリプトはPython 3.12の標準ライブラリだけを使う。自己申告の生成履歴とハッシュ照合は誤変更の検出であり、署名や権限制御ではない。

## 検証と残る確認

今回のスキル作成・独立エージェント試行はCodexで実施する。Bob IDEでのスキル検出・起動は別のチーム受入項目であり、今回実行済みとは記載しない。検証の実績はパッケージ外の `verification/` と案件の `qa/` に記録する。

配布用ZIPは `tools/release.py seal`、`tools/release.py bundle` で作成する。これらは保守コマンドで、通常の生成作業では実行しない。既存prototypeや他の配布キットは変更しない。

配置方式は [IBM Bob Skills公式資料](https://bob.ibm.com/docs/ide/features/skills)（2026-11-16確認）に従う。`distribution.json` は配布来歴でありプラグインmanifestではない。

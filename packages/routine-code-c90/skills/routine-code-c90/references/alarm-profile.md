# 旧アラーム案件からの移行

このページは0.1.0のアラーム専用案件を引き継ぐ場合に読む。0.2.0の通常操作は [汎用jobの入力と実行手順](workflow.md)、提供試験の指定方法は [検証プロファイルの契約](verification-profile.md) を使う。

## 0.1.0を保存する

旧版は `AlarmQualification_Update / PS-RTN-ALM-001 revision 0.1` の正本ハッシュに限定され、`include/AlarmQualification.h`、`src/AlarmQualification.c` と旧検証器を使った。0.1.0のZIP・案件・生成記録・試験実績はその版の証跡として保存する。過去のロックや結果を0.2.0用に書き換えない。

旧版で記録されたチェック数や未定義シンボル数を、汎用版の合格条件へ持ち込まない。旧仕様のループ・共有静的状態・外部APIの制約も、そのアラーム仕様の契約である。

## 0.2.0で新規jobを作る

同じJSON正本を使う場合も、新規jobとして準備する。0.2.0では関数名に従い `include/AlarmQualification_Update.h` と `src/AlarmQualification_Update.c` が標準パスになる。旧jobの `job.json` やロックを移植しない。

独立した旧アラーム試験を使う場合は、その正本ハッシュと関数名をtargetに持つ0.2.0 profileを指定する。試験が参照する提供ヘッダはprofileへ明示し、凍結した新ヘッダや既存試験を本体に合わせて変更しない。旧 `tools/codeflow.py` を現行jobの入口として使わない。

同梱例は `assets/examples/alarm-regression/`。現在の入口で準備する場合は次のように指定する。その後の生成・record・verifyは [通常の手順](workflow.md) に従う。

```powershell
& '<python>' -X utf8 -S -B '<skill>/scripts/codegen.py' prepare --spec '<skill>/assets/examples/alarm-regression/spec.json' --verification-profile '<skill>/assets/examples/alarm-regression/verification-profile.json' --workspace '<job-root>' --job alarm-v02-01
```

profileを指定しない場合も準備・生成・記録・ホストコンパイル検査は可能だが、結果は `compiled_only`、動的試験は未提供となる。試験ありのホスト合格も、物理入力の連続性・周期欠落検出・正式ABI・実機の時間予算を保証しない。

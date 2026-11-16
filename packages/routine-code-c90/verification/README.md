# スキル作成・検証の記録（2026-11-16）

検証主体はCodex。Bob IDEの認証や設定は変更していない。成果物の版は0.1.0。

スキルなしのbaselineは、仕様JSONだけから正しい試作コード・独自C試験・READMEを生成し、ホスト470チェックに合格した。コード生成そのものの失敗ではない。一方、既存の独立試験/固定検証器の再利用と、ハッシュロック・世代別生成記録はなかった。原仕様だけのbaselineと資材付きスキルの比較であり、モデルの正確性向上を統計的に示す評価ではない。

固定ツールの検査では、同名job拒否後に排他ファイルが残る不具合を発見して修正した。Windowsの同期/索引による一時的なrename拒否にも、既存キットと同じ上限付き再試行を適用した。修正後の7試験は合格。入力差替え、固定試験の変更、パス脱出、対応表欠落、世代上書きも拒否する。

公式 `quick_validate.py` は成功した。保守用検査にだけ既存AnacondaのPyYAMLを使用し、追加インストールは行っていない。配布スクリプトはPython 3.12標準ライブラリだけで実行・試験した。

独立レビューは、一般のC90実装手順とアラーム専用自動プロファイルの境界、RTOS API/ABIの推測防止、固定5資産の同一バイト再利用、生成記録と固定検証器の接続を確認し、修正必須の指摘なし。同一jobは直列運用が前提である。

配布ZIPを展開したスキルを別コンテキストのエージェントが読み、旧実装・baseline実装・過去の生成promptを参照せず、新しいC90本体と対応表を作った。世代記録を経て固定検証器を実行し、O0/O2で各1,948,941チェックに合格した。ソースの主担当レビューでも外部API・ループ・静的共有状態を加えていないことを確認した。

主な証跡:

- `artifacts/routine-code-skill/baseline/README.md`
- `artifacts/routine-code-skill/forward/alarm-01/records/g001.json`
- `artifacts/routine-code-skill/forward/alarm-01/qa/r001/verification.json`
- `packages/routine-code-c90/verification/verification.json`
- `packages/routine-code-c90/verification/project-install.json`

合格は今回のホスト検証範囲での結果であり、正式コンパイラ・RTOS結合・DLL ABI・WCETや、Bob IDEでの実起動の検証を含まない。

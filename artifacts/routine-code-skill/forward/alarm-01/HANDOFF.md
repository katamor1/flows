# AlarmQualification_Update チーム引継ぎ

`PS-RTN-ALM-001` revision `0.1` の試作JSONから、C90ルーチン1件を新規作成し、固定の独立受入試験を実行した。Windows x64ホストの厳格C90、O0/O2の両方で合格。仕様は `draft_trial`（要件確認前）のままである。

## 渡すもの

|成果物|用途|
|---|---|
|`src/AlarmQualification.c`|生成した判定ルーチン本体。実装関数は `AlarmQualification_Update` 1件。|
|`include/AlarmQualification.h`|固定プロファイル由来の型・関数宣言。|
|`input/spec.json`, `input-origin.json`|入力仕様の管理コピー、元の所在とハッシュ。|
|`traceability.md`|仕様ID/手順、正常・異常経路、状態更新、呼出し側責務、未決事項の対応表。|
|`records/g001.json`|生成AI、実行環境識別、BobIDE未実行、仕様・ソース・対応表等のハッシュ。|
|`qa/r001/verification.json`|実検証結果、実行引数、ツール版、O0/O2出力、シンボル検査、対象ハッシュ。|
|`qa/r001/*.stdout.txt`, `*.stderr.txt`|コンパイル、実行、オブジェクト検査の出力ログ。|
|`tests/test_alarm_qualification.c`, `tools/codeflow.py`, `package-lock.json`|固定の独立受入試験、固定検証器、資材整合性情報。変更せず保管する。|

ジョブの所在:
`C:\Users\stell\OneDrive\ドキュメント\ChatGPT\flows\artifacts\routine-code-skill\forward\alarm-01`

## 入力と生成の識別

- 仕様: `PS-RTN-ALM-001` revision `0.1`, 日付 `2026-11-13`。
- 仕様 SHA-256: `097b1185e284c17805b51c92dd821d1bec64f55d0ce1781c2c1fb369239b4265`。
- 本体 SHA-256: `14ae64654c995bb8a3321f626964be4ad6e3c63c205aa4ac0abdd4b19b696000`。
- スキル配布版 SHA-256: `82a472863d3852d3de8f29d9e64da902921462e00ebb548dd66e1696ff9ab3fe`。
- 生成AI: Codex。提供された primary runtime の識別は `26.1112.737.0`。正確なモデルの公開版識別は取得不能であり、推測していない。
- BobIDE: **未実行**。BobIDEへの互換性やBobIDE上での実行合格は確認していない。
- generation `g001`: `2026-11-16T12:49:14.989746+00:00`。run `r001` の記録時刻: `2026-11-16T12:49:26.121158+00:00`。時刻は固定記録器の値。

既存 production/baseline 実装と過去の生成プロンプトは参照していない。試験は配布版の既存独立試験をそのまま用いており、この本体に合わせて期待値を生成・変更していない。入力、ヘッダ、試験、検証器、ロック、配布資材は編集していない。

## 実行したコマンドと結果

以下は実際の呼出しをパス変数で表記したもの。`record` の note は実際の文言である。コンパイラ等の詳細な実行引数とreturncodeは `qa/r001/verification.json` にある。

```powershell
$pythonExe = 'C:\Program Files\WindowsApps\OpenAI.CodexPrimaryRuntime.v26-1112-737-0_26.1112.737.0_x64__3k8sg7r9htsxt\dependencies\python\python.exe'
$codegenScript = 'C:\Users\stell\OneDrive\ドキュメント\ChatGPT\flows\artifacts\routine-code-skill\distribution-v2\.bob\skills\routine-code-c90\scripts\codegen.py'
$jobWorkspace = 'C:\Users\stell\OneDrive\ドキュメント\ChatGPT\flows\artifacts\routine-code-skill\forward'
$inputSpec = 'C:\Users\stell\OneDrive\ドキュメント\ChatGPT\flows\prototypes\routine-code-poc\input\spec.json'
$clangExe = 'C:\Program Files\LLVM\bin\clang.exe'

& $pythonExe -X utf8 -S -B $codegenScript doctor
& $pythonExe -X utf8 -S -B $codegenScript prepare --spec $inputSpec --workspace $jobWorkspace --job alarm-01
# prepare 後、本体と traceability.md を生成。
& $pythonExe -X utf8 -S -B $codegenScript record --workspace $jobWorkspace --job alarm-01 --generation g001 --agent Codex --agent-version 'Codex desktop; supplied primary runtime 26.1112.737.0; exact model version unavailable' --bob-executed no --note 'PS-RTN-ALM-001 revision 0.1 fixed canonical JSONからC90本体と仕様対応表を新規生成。実行環境はCodexでありBobIDEでは未実行。production/baseline実装と過去生成promptは未参照。試作仕様を維持。未決事項はtraceability.mdを参照。'
& $pythonExe -X utf8 -S -B $codegenScript verify --workspace $jobWorkspace --job alarm-01 --clang $clangExe --run r001
```

すべて終了コード0。`doctor` は `ok`、`prepare` は `implementation_included: false`、`record` は `recorded`、`verify` は `passed`。

|確認|条件・実績|
|---|---|
|ホスト/コンパイラ|Windows x64, clang 22.1.3, target `x86_64-pc-windows-msvc`。|
|C90ビルド|`-std=c90 -pedantic-errors -Wall -Wextra -Werror`、O0およびO2のビルド/リンク成功。|
|O0実行|1,948,941チェック、0 failures。|
|O2実行|1,948,941チェック、0 failures。|
|受入試験|CHK-01〜05と再成立163、全有効状態遷移88、CHK-06/優先順位/書込みなし33、独立インスタンス40、11サンプル全177,147系列の照合1,948,617。各最適化で同じ内訳。|
|O2オブジェクト|未定義シンボルなし。外部リンケージを持つ定義は `AlarmQualification_Update` のみ。DLLエクスポート宣言の検証を意味しない。|

チェック数は呼出し照合数であり、独立した要求数ではない。

## 統合時に必要なこと

呼出し側はstateを0で初期化し、state/resultの有効性、寿命、非重複、排他的所有を保証する。同一周期の入力スナップショットを渡し、周期欠落・入力無効を検出したら次の判定前に `sample_valid=0` を通知する。戻り値0の場合だけ結果を消費し、エラー後の旧イベントを再利用しない。

判定は10個の有効ONサンプルを数える。最初のONを1回目として10回目は9T後であり、経過時間や周期間の物理入力連続性は測定していない。OFF/無効で判定カウントは戻るが、アラーム表示解除の仕様にはならない。

未完了の製品側作業は次の通り。所有者と判断の詳細は `traceability.md` およびJSONの `open_issues` にある。

- Q-01 要求所有者: ASM-01〜03を承認する。
- Q-02 RTOS基盤担当: 周期T、欠落/無効検出、実行時間予算を確定し、実機WCETを評価する。
- Q-03 C設計担当: 既存命名・型・ファイル配置・文字コード規約、正式コンパイラ設定、DLL ABI/リンク/公開管理、RTOS結合を確認する。
- Q-04 制御設計担当: U.XXXX取得、G.YYYY表示灯、画面公開、ZZZZログ追記予約、失敗処理・排他、解除条件を別途仕様化・結合試験する。

これらの正式環境確認と、単体テスト仕様書の納品文書作成は今回のホスト合格に含まれない。処理量が有界であることからWCET合格を導かない。

修正時は本体・対応表を更新し、新しい generation/run ID（例 `g002` / `r002`）で記録・再検証する。過去記録は上書きしない。管理元のGitへ、この本体を含む同一版の成果物を保存してから変更する。ハッシュ記録だけでは削除済みソースを復元できない。この作業ではGit登録は行っていない。

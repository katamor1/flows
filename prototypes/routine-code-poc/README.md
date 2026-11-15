# プログラム仕様書1件からのC90ソース生成PoC 0.1.0

既存のPS-RTN-ALM-001 revision 0.1のJSON正本から、`AlarmQualification_Update` のC90ヘッダ・実装を作成し、Windowsホストで検証した。10回連続ONの判定を行うDLL内部ルーチン1本である。

今回はこのチャットのCodexが生成した。Bob IDE上の生成実行は未検証。Bob Shell 2.0.4は導入済みだったが、非対話実行に必要な `BOB_API_KEY` は実行環境に存在しなかった。Bob IDEで同じ入力から試せる[固定指示書](prompts/generate-source.md)を付属する。鍵の作成・認証設定の変更は行っていない。

## 入力から生成物への対応

```text
OfficeCLIで納品した仕様書と同じJSON正本
  → input/spec.json + job.json（入力ハッシュ固定）
  → AI生成 include/AlarmQualification.h / src/AlarmQualification.c
  → generation-record.json（生成者・入力/コード/試験ハッシュ）
  → 固定 tools/codeflow.py
  → qa/<run>/verification.json + コンパイル/試験/シンボル検査ログ
```

管理正本はJSONで、Wordからコードを逆抽出しない。前段のWord展開manifestと今回の入力のSHA-256が同じ `097b1185e284c17805b51c92dd821d1bec64f55d0ce1781c2c1fb369239b4265` であることを確認した。原本の所在とWordハッシュは `job.json` に記録した。

| ファイル | 役割 |
|---|---|
| [input/spec.json](input/spec.json) | 生成入力の固定コピー。試作・要件確認前 |
| [include/AlarmQualification.h](include/AlarmQualification.h) | 正本と一致する型・関数宣言と呼出し契約 |
| [src/AlarmQualification.c](src/AlarmQualification.c) | 生成したC90実装。ASCII、関数1本 |
| [tests/test_alarm_qualification.c](tests/test_alarm_qualification.c) | 本体生成前に仕様だけから別エージェントが作成した受入試験 |
| [tools/codeflow.py](tools/codeflow.py) | 再利用する固定検証スクリプト。ロジックは生成しない |
| [prompts/generate-source.md](prompts/generate-source.md) | Bob IDEで再生成する指示。変更可能範囲を限定 |
| [traceability.md](traceability.md) | 仕様・コード・確認内容の対応 |
| [qa/test-design.md](qa/test-design.md) | 独立試験の設計と限界 |
| [qa/review.md](qa/review.md) | 独立AIレビュー記録（人の承認とは別） |

## 検証結果

Clang 22.1.3、Windows x64、`-std=c90 -pedantic-errors -Wall -Wextra -Werror` でコンパイルした。`-O0` の実行と、`-O2` で作成した同じ本体オブジェクトにリンクした実行の双方で、各 **1,948,941チェック、失敗0**。最終記録は [qa/green-r003/verification.json](qa/green-r003/verification.json)。

| 確認 | 結果・記録 |
|---|---|
| 試験が未実装を検出する | 本体生成前の `-99` スタブで5群とも失敗。[red-r001](qa/red-r001/verification.json) |
| 10回境界・100回ON継続・OFF/無効・再成立 | 合格 |
| 全旧状態0..10、無効時の任意signal_on | 合格 |
| NULL、不正論理値、状態11/UINT_MAX、エラー優先順・全バイト無更新 | 合格 |
| 2状態の交互呼出し | 合格 |
| ON/OFF/無効からなる長さ11の全177,147系列 | 履歴末尾を走査した期待値と一致 |
| 本体オブジェクトの未定義シンボル | 0。公開シンボルは対象関数だけ |
| 固定資材・入力変更の検出 | 正本・ヘッダ・試験・本体を生成記録のハッシュと照合 |

チェック数は各呼出しの戻り値・状態・結果の照合回数であり、独立要求の数ではない。長さ11を超える全系列や全整数値を網羅したという意味でもない。禁止処理はソースレビューとオブジェクト検査を併用して確認した。シンボル検査だけで全制約を自動証明するわけではない。

`green-r001` は最初のO0合格とO2オブジェクト検査、`green-r002` はO2実行追加時、`green-r003` は生成記録のハッシュ照合追加後の最終実行である。本体・ヘッダ・試験は初回合格から変更していない。旧実行で使ったスクリプトは各runの `codeflow-used.py` に保存した。

## 固定スクリプトによる再検証

Python 3.12（標準ライブラリのみ）、Clangおよび同じフォルダの `llvm-nm.exe`、MSVCリンカーとWindows SDKが必要。今回の環境ではVisual Studio 18 Communityも導入済み。配布物にコンパイラやPythonは同梱しない。

```powershell
$codePython = 'C:\path\to\python.exe'
$codeClang = 'C:\Program Files\LLVM\bin\clang.exe'
$codePoc = 'C:\work\routine-code-poc'
& $codePython -S -B "$codePoc/tools/codeflow.py" verify --clang $codeClang --output 'qa/team-r001'
if ($LASTEXITCODE -ne 0) { throw 'Verification failed; inspect the run logs.' }
```

実行位置に依存しない。`--output` はPoC内の新しいディレクトリを指定する。既存runへの上書きは拒否する。入力・生成記録のハッシュ不一致も停止する。正本・コードを改訂するときは、別案件コピーと新しい正直な生成記録を作り、差分を確認する。検査を通すために試験・スクリプト・原仕様を書き換えない。ハッシュ照合は誤変更の検出であり、署名やアクセス制御ではない。

ZIPはソース、固定指示、スクリプト、試験、テキスト検証記録を含む。実行可能ファイル・オブジェクトは同梱しない。記録内の実行時絶対パスとツールハッシュは今回環境の来歴であり、チームでは実際の環境で再検証する。

配布ZIPの作成も固定スクリプトを再利用する。ZIP内の `manifest.json` に全収録ファイルのSHA-256を記録し、生成後に全ファイルを読み戻して照合する。既存ZIPは上書きしない。

```powershell
& $codePython -S -B "$codePoc/tools/bundle.py" --output 'C:\work\deliveries\RTN-ALM-001-code-poc-0.1.0.zip'
```

## 製品への組込み前に残る確認

正本は `draft_trial` のまま。ASM-01〜03とQ-01〜04の承認、既存規約に沿った型・関数名、正式コンパイラ設定、対象CPU/ビット数/ABI、RTOS上の時間予算とWCET、呼出し周期と欠落検出を確認する。

この関数は時刻を測らず、1回目のONを1と数えて10回目で成立する（周期Tなら最初から9T後）。物理的な連続ONを証明しない。呼出し側が状態を0で初期化し、各インスタンスの非重複・排他的アクセスを保証する。戻り値0のときだけ結果を消費する。処理量の固定上限と、実機実行時間の保証は別である。

PLC読取り、表示灯出力、画面公開、ログ予約は呼出し側の別ルーチンで仕様化する。実RTOS提供関数やDLLのエクスポート設定を推測して追加していない。ホスト試験用Cランタイムは製品関数の依存ではない。今回の試験コードは生成コードの検証用であり、後続工程で作る納品用の単体テスト仕様書とは区別する。

## 参照した公式資料

- [Bob Shellの非対話実行](https://bob.ibm.com/docs/shell/getting-started/start-bobshell-non-interactive)（2026-11-14確認）：非対話実行のAPIキー要件。IDEのSSOと別である。
- [Clangの標準モードと診断](https://clang.llvm.org/docs/UsersManual.html)（同日確認）：C90モードと後続標準の拡張をエラーとする指定の根拠。

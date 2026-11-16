# アラーム判定プロファイルの実行

本プロファイルは `PS-RTN-ALM-001 revision 0.1` の固定JSONと、前回PoCで独立作成した受入試験を使う。しきい値変更や文書版だけの変更も、初版の自動検証では入力不一致として拒否する。

管理者が用意したPython 3.12とClangを使う。追加Pythonライブラリは不要。Windowsのホスト実行にはClangに対応したMSVCリンカー/Windows SDKと、Clangと同じフォルダの `llvm-nm.exe` が必要。以下の `<skill>`、`<spec.json>`、`<job-root>` は実際の絶対パスに置き換える。

```powershell
& '<python>' -X utf8 -S -B '<skill>/scripts/codegen.py' doctor
& '<python>' -X utf8 -S -B '<skill>/scripts/codegen.py' prepare --spec '<spec.json>' --workspace '<job-root>' --job alarm-01
```

作成された `alarm-01/input/spec.json` とヘッダを読む。本体は付属していない。仕様に従って `alarm-01/src/AlarmQualification.c` を生成し、`alarm-01/traceability.md` を書く。固定試験・検証器は既存ファイルのバイトコピーであり、AIが作り直すものではない。

生成記録は次のコマンドで作る。`--agent`、`--agent-version`、`--bob-executed`、`--note` は実態を記入する。Bobで実行したときの例:

```powershell
& '<python>' -X utf8 -S -B '<skill>/scripts/codegen.py' record --workspace '<job-root>' --job alarm-01 --generation g001 --agent 'IBM Bob' --agent-version '<実際のBob IDE版>' --bob-executed yes --note '固定正本からC90本体を生成。未決事項は対応表を参照。'
& '<python>' -X utf8 -S -B '<skill>/scripts/codegen.py' verify --workspace '<job-root>' --job alarm-01 --clang '<clang.exe>' --run r001
```

Bob以外で実行した場合は、例えば `--agent Codex --agent-version '<実際の実行環境識別>' --bob-executed no` とする。生成記録が更新されたソースと一致しない場合、検証は停止する。検証で本体を直したら新しい世代g002を記録し、新しいrun r002で再検証する。同じIDは上書きしない。仕様・ヘッダ・試験・検証器の不一致を解消するためにロックを書き換えない。

成功時の `qa/r001/verification.json` は、厳格C90のO0/O2実行、固定受入試験、O2オブジェクトの未定義/公開シンボル検査を記録する。試験は各最適化条件で1,948,941チェックを行う。この数は呼出し照合数であり独立要求数ではない。物理入力の連続性、周期欠落検出、正式ABI、実機の時間予算は保証しない。

`records/g001.json` は変更前の生成記録として残るが、過去runのコードを再現する場合は対応するコード版もGitへ保存する。記録のハッシュだけで削除済みコードを復元できるわけではない。生成コードの正本は案件のソースとGit、仕様の正本はJSONで管理する。

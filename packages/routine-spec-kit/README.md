# Routine Spec Kit 0.1.0

JSON正本からWordを展開する固定処理と、AIエージェント向けスキルを同梱したローカル配布試作。テンプレートや変換スクリプトを案件ごとに作り直さない。

**対応範囲:** `alarm-qualification-v01`。10周期連続ON判定ルーチン `AlarmQualification_Update` 1本の試作仕様のみ。一般のC90ルーチン、12周期への仕様変更、ガウスフィルタ、承認済仕様は未対応。

## 実行

Python 3.12、python-docx 1.2.0、lxml 6.1.1を準備した環境を使う。CLIは依存を導入しない。依存環境の作成・更新は環境管理者の作業とする。配布ZIPにはPython本体やライブラリは含めていない。

次の変数を利用環境の絶対パスへ設定する。

```powershell
$specPython = 'C:\path\to\python.exe'
$specSkill = 'C:\tools\routine-spec-kit\skills\routine-spec-doc'
$specJobs = 'C:\work\spec-jobs'
& $specPython -B "$specSkill/scripts/specflow.py" doctor
& $specPython -B "$specSkill/scripts/specflow.py" describe
& $specPython -B "$specSkill/scripts/specflow.py" new-job --workspace $specJobs --job alarm-01
```

返された案件ディレクトリの `source/spec.json` を編集してGit等で管理する。その後、同じ固定CLIで検証・展開する。

```powershell
& $specPython -B "$specSkill/scripts/specflow.py" validate --workspace $specJobs --job alarm-01
& $specPython -B "$specSkill/scripts/specflow.py" render --workspace $specJobs --job alarm-01 --run r001
```

出力は `alarm-01/renders/r001/` のDOCX・入力控え・manifest。次回は `r002` 等、新しい展開IDを指定する。同名案件・展開IDは上書きしない。JSON出力のパスは実行環境の絶対パスとなる。

## スキルから利用する

この配布物では `skills/routine-spec-doc/SKILL.md` をエージェントへ指定して利用できる。例: 「このSKILL.mdを使い、既存の10周期連続ON判定の仕様正本を改訂し、Wordへ展開してください」。エージェントは固定CLIを使用し、案件のJSONだけを編集する。

Codexで継続的に発見させる場合は、利用環境の管理者がこのスキルフォルダ全体をリポジトリの `.agents/skills/` 等、対応する検索先へ配置する。SKILL.mdだけをコピーすると資材が欠ける。この試作の作成時には、自動配置、ユーザー共通設定、MCP登録、マーケットプレイス公開は行っていない。

スキルの検出場所やプラグイン配布はホストに依存するため、[公式Skills文書](https://learn.chatgpt.com/docs/build-skills)を参照する。ホストに依存しないCLIとしても利用できる。

## 固定資材の管理

`release.json` に固定資材のSHA-256を保存する。各コマンドは資材と依存版を照合する。案件の `package-lock.json` は利用した配布版とrelease.jsonのハッシュを固定する。不一致なら処理を停止し、正しい配布版を再配置する。資材を自動修復・再生成するコマンドやテンプレート差替え引数は提供しない。

利用者の書込み領域はパッケージ外の案件ルートとする。パッケージ配下への案件作成、パスの境界越え、案件内部のシンボリックリンクやWindowsジャンクションを拒否する。通常終了時は一時領域から完成した展開ディレクトリを公開する。同じIDの協調的な並行実行は排他ファイルで制限する。プロセス異常終了で `.ID.lock` や一時ディレクトリが残った場合は、実行中の処理がないことを管理者が確認してから復旧する。

これは誤操作の検出であり、エージェント自身が検査コードやハッシュ一覧を書換えられる環境での強制的な防止ではない。本運用では信頼できる配布元のハッシュを確認し、ACLや実行環境の権限でパッケージを読取り専用、案件領域を書込み可能にする。読取り専用属性だけでは十分ではない。この試作は権限設定を変更しない。悪意ある別プロセスが検査中にファイルやリンクを変更する環境への耐性は提供しない。

## 確認範囲

元の試作と同一のスキーマ・Wordテンプレート・記述例を使用する。検証器は当該スキーマの限定キーワードだけを扱う。出力に `draft_trial` を維持し、業務承認を付けない。生成成功はCコードのコンパイル・単体試験・RTOS性能確認ではない。

Wordのページ表示を確認する処理は含めていない。文量や表の行数が増えた場合、または保守側でテンプレートを改訂した場合は、別途表示確認が必要である。

保守用の原型は `prototypes/routine-spec-flow`、パッケージの検査はリポジトリ内の `packages/routine-spec-kit/tests/test_package.py`。保守用 `tools/release.py seal|bundle` は通常実行するスキルや配布ZIPに含めない。資材更新は保守側で版を改めて検査・配布する。

---
name: routine-spec-doc
description: Use when drafting or revising full routine specification JSON and generating Word through a fixed OfficeCLI template in IBM Bob.
---

# JSON正本からOfficeCLIでプログラム仕様書を生成する

環境票のPython 3.12と承認済Bob同梱OfficeCLI実体の絶対パスを使う。Pythonの追加ライブラリは不要。まず`doctor`と`describe`を実行し、固定資材と実体の一致を確認する。正本の記述は[references/authoring.md](references/authoring.md)に従う。

```powershell
& '<python>' -X utf8 -S -B '<skill>/scripts/specflow.py' doctor --officecli '<officecli.exe>'
& '<python>' -X utf8 -S -B '<skill>/scripts/specflow.py' describe --officecli '<officecli.exe>'
& '<python>' -X utf8 -S -B '<skill>/scripts/specflow.py' new-job --officecli '<officecli.exe>' --workspace '<案件ルート>' --job routine-01 --spec '<フルJSON正本>'
```

`--spec`がない場合は`--routine-name/--routine-id/--document-id`で識別情報を指定できる。未記入スケルトンは業務規則を含まず、validate/renderは内容が埋まるまで拒否する。新規案件でAlarmの規則を注入しない。案件はスキル外へ作り、正本と`.gitattributes`、package-lockを保持する。

```powershell
& '<python>' -X utf8 -S -B '<skill>/scripts/specflow.py' validate --officecli '<officecli.exe>' --workspace '<案件ルート>' --job routine-01
& '<python>' -X utf8 -S -B '<skill>/scripts/specflow.py' render --officecli '<officecli.exe>' --workspace '<案件ルート>' --job routine-01 --run r001
```

フルJSON0.1.0/0.2.0、任意の関数名・ID・件数に対応する。型定義の空文字、空配列、閾値なし、状態なしを受け付ける。任意の設定はbehavior.configurationに書く。条件表はconditionと任意項目を持つ。状態・承認ラベルは正本から転記し、人の承認を作らない。

OfficeCLIが全てのDOCX編集と構造検査を担当する。固定資材を通常実行で再生成しない。資材や実体・版・ハッシュ不一致、構造/内容/書式検査失敗は停止し、別版や別生成器への切替で回避しない。案件ごとの正本改訂は再検証・新runへ展開する。既存job/runを上書きしない。

Wordの全ページ表示確認と業務意味の承認は別途必要である。未実施なら未確認と報告する。生成成功をC90/RTOS/WCET試験合格やBobチャット実起動確認と扱わない。

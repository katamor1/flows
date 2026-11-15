# IBM Bob向け ルーチン仕様書フロー配布候補 0.1.0

**Bob受入試験用のキット。** プロジェクトのGit管理でチームへ配布する。今回の同梱生成器は、既検証のroutine-spec-kit 0.1.0をそのまま再利用する。10周期連続ON判定ルーチンの試作仕様だけを扱う。

生成は固定Python処理、生成物の読取り・OOXML構造検査はBob同梱OfficeCLIの標準Officeツールを使う計画である。OfficeCLIによるWord生成へ置き換えた版ではない。既存テンプレートの独自繰返し表指定は、標準mergeへそのまま移せないためである。

## 配布方法

ZIPの `.bob/skills/routine-spec-doc/` と `.bob/rules/20-routine-spec.md` を、対象プロジェクトの同じ位置へ置く。最初は別の場所へ展開して内容と衝突を確認し、保守担当のPRでプロジェクトへ取り込む。既存 `.bob` 全体を置換しない。

チームメンバーはそのリポジトリをチェックアウトする。各自のグローバルスキルへ別々にコピーして版が分岐する運用を避ける。Bob SettingsのSkillsでプロジェクト技能として検出されることを確認する。更新後の確認は新しい会話で行う。

`distribution.json` はこのキット独自の配布来歴であり、Bobのプラグインmanifestや設定ファイルではない。

## 生成器の実行環境

Python 3.12、python-docx 1.2.0、lxml 6.1.1を用意する。PythonやライブラリはこのZIPに含まない。環境の準備・更新は管理者の作業とし、スキル実行中にBobが不足依存や別版OfficeCLIを自動導入しない。

Bobと同梱OfficeCLIは別途導入済のチーム環境を利用する。Bobから利用できるOfficeツールと同梱CLIの直接呼出し経路は同一と仮定しない。本キットは同梱CLIの配置場所を指定せず、OfficeCLIを再同梱しない。

## 最初の実行

BobのAgentモードで、次の依頼を行う。

> routine-spec-docスキルを使って、10周期連続ON判定の記述例から新規案件を作成してください。案件ルートはこのプロジェクトのspec-jobs、案件IDはbob-pilot-01とします。固定生成器のdoctorとdescribeを確認し、文書版だけ0.2へ変更して検証・Word展開してください。生成したWordは標準office_readで内容を読み、validateモードの構造検査結果を記録してください。資材は再生成しないでください。表示を確認できなければ未確認と報告してください。

既存スキルのCLIは次の形で利用する。Pythonの実行ファイルはチームが準備した絶対パスを指定する。

```powershell
$specPython = 'C:\path\to\python.exe'
$specProject = 'C:\work\control-project'
$specSkill = Join-Path $specProject '.bob/skills/routine-spec-doc'
$specJobs = Join-Path $specProject 'spec-jobs'
& $specPython -B "$specSkill/scripts/specflow.py" doctor
& $specPython -B "$specSkill/scripts/specflow.py" describe
& $specPython -B "$specSkill/scripts/specflow.py" new-job --workspace $specJobs --job bob-pilot-01
```

`spec-jobs/bob-pilot-01/source/spec.json` を正本として編集し、次を実行する。

```powershell
& $specPython -B "$specSkill/scripts/specflow.py" validate --workspace $specJobs --job bob-pilot-01
& $specPython -B "$specSkill/scripts/specflow.py" render --workspace $specJobs --job bob-pilot-01 --run r001
```

出力は `spec-jobs/bob-pilot-01/renders/r001/`。再展開には新しいrun IDを使う。既存案件の再開ではnew-jobを実行せず、正本とpackage-lockを維持する。

## 受入時に記録すること

- Bob IDEの実ビルド、スキル検出・起動、標準Officeツールの有無。
- 固定生成器のdoctor、JSONの変更差分、出力への反映。
- `office_read` の読取りとvalidate結果。使えない場合は未確認として扱う。
- Wordの全ページの表示確認。構造検査は改ページや内容の承認ではない。
- テンプレート欠落・閾値12・同じrun IDで、自己修復や上書きをせず停止すること。
- 固定資材のハッシュ不変と、正本・入力控え・出力のmanifest。

現行doctorは固定資材とPython依存を検査する。Bobや同梱OfficeCLIの版・機能までを自動検査する実装ではない。

## 保守と次段階

元スキル内の `release.json` と案件の `package-lock.json` を維持する。更新は保守担当が版を改めて配布し、利用者がロックを書換えて検証を回避しない。書換えを権限として防ぐ必要がある配布先では、パッケージ領域を実行アカウントから書込み不可にする。

初回はGit配布で始める。Bobネイティブプラグインは複数リポジトリへの配布が必要になり、採用版で形式と更新を確認した段階で追加する。ローカルMCPは固定生成器を型付きツールへ集約する場合に追加する。今回のZIPはMCP・自動承認・ユーザー共通設定を変更しない。

OfficeCLI生成器へ移行する場合は、同梱版の公開呼出し方法を確認し、独自の繰返し表を展開する固定アダプターを実装・検証する。生成器を切り替えてもJSON正本と文書の契約を維持する。

参照: [IBM Skills](https://bob.ibm.com/docs/ide/features/skills)、[IBM Custom rules](https://bob.ibm.com/docs/ide/configuration/rules)、[IBM変更履歴](https://bob.ibm.com/docs/ide/changelog)、[OfficeCLI merge](https://github.com/iOfficeAI/OfficeCLI/wiki/command-merge)。

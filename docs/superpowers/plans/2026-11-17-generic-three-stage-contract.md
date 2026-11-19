# 3工程の汎用化 共通契約

利用者が3工程すべてを指定し、続きを実施するよう指示済み。コード生成0.2.0に加え、プログラム仕様書0.3.0、単体テスト仕様書0.2.0を作る。旧版ZIPと既存の案件/原本は保存する。今回の生成・検証AIはCodexで、Bob実起動は未確認。

## 工程1 プログラム仕様

既存のフルJSON形（document/overview/trial_assumptions/interface/behavior/constraints/verification_examples/traceability/open_issues）を維持し、関数名/文書ID/閾値/項目数を固定しない。schema_version0.1.0既存入力と0.2.0新入力を扱う。type_definitions空文字可、状態/パラメータ/課題/仮定等の配列0件可。thresholdは任意項目で、汎用のconfiguration配列{name,value,meaning}も任意。

decision_rowsはconditionを持つJSON object、他のキーは任意の状態・出力・戻り値のデータ。旧old_count等を必須にしない。Wordは条件と残る項目をkey/value表示する汎用表。元JSONを勝手に変更して表示用ダミーを挿入せず、表示viewで空を明示する。全ての意味情報（追加configuration含む）を文書へ出す。

new-jobは --spec FILEで任意のフルJSONを取り込める。未指定なら --routine-name/--routine-id/--document-idで未記入スケルトンを作り、validate/renderは未記入を拒否する。新規案件でアラームの業務ルールを自動挿入しない。新既定template_id=routine-spec-v02、v01は表示互換を実装できるなら受け入れる。状態は入力の正本に従い、ツールが人の承認を作らない。

## 工程2 コード生成

docs/superpowers/plans/2026-11-17-generic-code-skill.mdに従う。新規job.json0.2.0のspec/header/source/generation_recordはjob相対パス。旧0.1.0 jobでも同キーが存在する。生成記録にはinput_spec_sha256/header_sha256/source_sha256がある。追加資産はfile_hashes。C90ホスト検証は試験なしcompiled_onlyと試験ありpassedを分ける。

## 工程3 単体テスト仕様

新しい汎用JSON0.2.0を使う。トップキーは既存と同じschema_version/document/target/summary/environment/assumptions/cases/families/static_checks/coverage/open_issues。documentは任意ID/関数、template_id=unit-test-spec-v02、targetは読み込んだ正本/C/Hの実ハッシュ。source/helperには特定hash/関数/戻り値/フラグ名/件数を埋め込まない。

cases[]={id,title,purpose,spec_refs:[str],initial_conditions:[{name,value}],steps:[{id,action,inputs:[{name,value}],expected:[{target,comparison,value}],repeat:int,note:str}],judgment:str}。valueは任意の有限JSON値（式やPythonとして実行しない）。initialとinputsは空可、expectedは各step最低1。比較名はequals/unchanged/predicate/within_tolerance等の一般的な記述。特定stateフィールド、0/1入力、A/Bインスタンス、エラーコードは固定しない。

families[]={id,title,spec_refs,mode,dimensions:[{name,values:[JSON value]}],sequence_length,combination_count,calls_per_instance,call_count,initial,enumeration,method,expected_rule,examples:[str]}。mode product/sequenceの有限族を検算し、calls=combination_count*calls_per_instance。productのsequence_length=0、sequenceは1つのalphabetと正のsequence_length。族数0可、特定の系列長や88/24等を固定しない。cases/families/static_checks全て0は不可。

static_checksは既存{id,title,spec_refs,method,criterion,boundary}を汎用IDで使う。coverageは既存{spec_ref,method,item_ids,rationale}。指定された原仕様の仮定・手順・制約・検証例等の宣言ID（IDなしはJSON Pointer）へ対応付け、未検証・呼出し側/範囲外は理由を残す。P-01..05等の固定リストは禁止。重複/不明参照/浮いたcaseを拒否。open_issues/assumptionsは入力から引き継ぎ、0件可。

new-jobは --code-job DIR からjob.jsonのパスと生成記録を読んで実際のspec/C/Hを固定。コードkitの0.2.0/旧0.1.0の双方を受ける。別の正式プロジェクト向けに --program-spec FILE --source FILE --header FILE の明示入力も用意してよい。生成来歴がない場合はexternal/not_providedと記録し、偽造しない。

--unit-test-spec FILEで新規正本を取り込める。未指定なら案件のtarget/assumptions/Qを反映した未記入スケルトンを作り、作者がケースを埋めてからvalidate/renderする。新規ケースを既存ログからpassedにしない。execution-recordは全ID未実施で別管理。汎用schemaは任意JSON値を検査し、未知のSchemaキーワードを黙って無視しない。

Wordテンプレは既存の8表viewを継承可能。case_stepsのinputs/expected文字列を汎用名/値表示へ変更、familyはdefinition/oracleのコンパクト表示。初期条件/全期待値/比較名/各注記を落とさない。新template_id=unit-test-spec-v02。旧0.1.0データは旧ZIPで再現し、必要なら別の移行dataを作る。既存納品物/ロックは上書きしない。

## 共通検証/配布

OfficeCLI1.0.144（既存承認実体）で編集・構造検査・内容/書式照合。Pythonは標準ライブラリのみ、XMLは読取り検査のみ。新テンプレは保守工程でOfficeCLIで一度作り、通常処理で再生成しない。docx操作markerは主担当が1回呼出済み、サブエージェントは再実行しない。

空リスト/空文字は表示viewの「該当なし」等で扱い、canonical hashはそのまま。案件ごとの入力・コード・資産のハッシュ固定と改変検知は残す。固定スキーマ/テンプレ/ツールを通常の作者が書き換えない。各kit/versionZIPと3つを統合したBob配布ZIPを作り、.bob/skillsを更新する。

byteロック対象はGit checkoutのCRLF変換で壊れないようskill/job配下.gitattributes '* -text'を配布する（diff属性は変更せず、global/rootGit設定を変更しない）。旧版は保存する。

受入はアラーム回帰に加え、状態なし/閾値なしのRangeClampと、提供された合成テストAPI/状態を持つSampleHold_Update。文書kitはsourceやfamilyの個数の異なる非alarmケースと空配列を実OfficeCLIで展開し、全内容/書式/構造と改変拒否を確認する。全ページの表示未確認ならその旨を残し、実RTOS/WCET/Bob起動の保証にしない。

## 実施結果

2026-11-17に3工程の汎用化、個別ZIPと統合ZIPの作成、プロジェクト.bobへの配置を実施した。検証結果は`artifacts/routine-generic-validation/README.md`と`verification.json`を参照。プログラム仕様21件、コード29件、修正後UT契約9件/配布2件、統合配布7件の検査に成功し、共通RangeClampの正本/C/H/生成記録を工程間で照合した。旧版ZIPは保存済み。Word全ページ表示、Bob起動、正式RTOS/DLL ABI/WCET、人手承認は未確認として残す。

# UT 0.2.0 引継ぎ

最終資材はseal済みでfreeze。対象はpackages/routine-unit-test-officecliのみ。rootによる.bobコピー/統合ZIP作成を待つ。Bobアプリ起動、全ページ表示、RTOS/WCETは未確認。

- ZIP: packages/routine-unit-test-officecli/dist/ibm-bob-routine-unit-test-officecli-0.2.0.zip
- ZIP SHA-256: e863d034bfc0f027d03e11a6230ac39dd0a5b703dcc57fa9ebe92a09059264c6
- release SHA-256: f07b84dfff7d102d6f872eddb0a8ae85ac712a7779c97982aedd66a795703491
- 旧0.1.0 ZIP SHA-256: cd63ff3c50c33690aa2a6483b9eac9729c0b7c3ce81ceb310d2baa8e55130c8c（既存checksumsと一致）

acceptance-summary.jsonに実結果、final-invocations.jsonに最終コマンドを保存した。最終参照先は以下の3案件のrenders/r001/unit-test-spec.docxとmanifest.json。

- range-clamp-release-final: 共通の生成コードjob pipeline-code/range-clampと完全同一のspec/C/H。3ケース・8代表呼出し、1族5組×2呼出し=10、静的確認1。仮定/課題/状態は0。生成来歴を実記録から保持。
- sample-hold-release-final: upstreamのfull SampleHold仕様、2ケース・0族・静的確認1、仮定2/課題0、environment=[]。合成API/状態あり。明示spec/C/H入力で来歴external/not_provided。正式RTOS APIの保証は作らない。
- alarm-regression-release-final: 旧0.1.0 code job読込。元UT JSONを変更せず、別v02移行例で16ケース/4族/静的確認6を実OfficeCLIで展開。

3案件ともOfficeCLI構造検査、全テキスト・書式・固定part照合が成功。全確認IDはnot_executed/evidence=[]。旧コード試験ログをUTのpassedへ転記していない。Wordの全ページ表示は未確認。

unittest-result.json: 15件の全体テスト成功（ZIP展開後のdoctor/new-job/renderを含む）。contract-final.txt: 追加した空inputs/within_toleranceの検査を含む8件の契約テスト成功。未知schema keyword、任意有限JSON値、非有限値、空期待値、重複ID/参照、未対応coverage、族件数、ハッシュ改変、未記入骨格、旧passed転記を検査した。自己再現2renderのsemantic SHA一致も確認。

range-clamp-pipelineはテンプレ検証中の初期snapshotで、最終release seal前のロックを保持する。修正前の*-finalも過去のreleaseを記録するsnapshotである。配布・統合の参照は必ず*-release-finalを使う。checks/配下は自動テストの隔離案件・展開ZIP・改変拒否用コピーである。

旧テンプレートv01、元alarm_unit_test.json、旧ZIP/checksumsはgit diff --quietで未変更を確認した。新テンプレv02は保守工程でOfficeCLI text命令から一度作成し、PythonはXML読取り検査のみ。markerはroot既実施分を使い、再実行していない。


レビュー修正: configuration.valueやdecision_rowsの任意JSONにあるidキーを、原仕様の宣言IDとして誤収集する不具合を修正した。宣言IDはdocumentとtrial_assumptions/behavior.steps/constraints/verification_examples/open_issuesの正式レコードに限定し、任意payloadはJSON Pointerで参照する。stage1-validなfull RangeClampに重複payload-id、実宣言IDと同じnested id、任意decision出力idを追加した回帰が修正前失敗→修正後成功。実際のstep宣言ID重複は引続き拒否する。

新releaseで9契約テスト、2配布テスト（展開doctor/new-job/render、資材改変拒否）が成功した。3つの*-release-final案件を新規作成してvalidate/render/doctorに成功し、全manifestが新release hashと一致することを確認。3文書とも修正前とsemantic SHA256が一致する。修正前の要約/実行記録は*-before-payload-id-fix.jsonに保存した。詳細はacceptance-summary.jsonのpost_review_validationを参照。

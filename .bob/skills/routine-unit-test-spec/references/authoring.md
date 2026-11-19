# 0.2.0 記述規約

`assets/schema/unit-test-spec.schema.json`が形式の正本である。固定スクリプトやテンプレートを案件の都合で変更しない。`assets/examples/range-clamp`と`sample-hold`に、状態なし/合成API・状態ありの独立した入力例がある。合成APIは正式なRTOSインターフェースではない。

期待値は原仕様に基づいて決め、観測した実装値や旧ログを正解にしない。対象C/Hを読む追加観点はstatic_checksへ分け、対象範囲と限界をboundaryに書く。初期条件/入力の{name,value}と期待値の{target,comparison,value}は有限JSON値を持てる。null/boolean/number/string/object/arrayを使用でき、文字列はそのままの記述データである。式やコードを実行しない。各stepには少なくとも1期待値を持たせ、action、repeat、noteを明記する。

familyのproductは全dimensions.valuesの要素数の積、sequenceは1 alphabet要素数のsequence_length乗とする。sequence_lengthはproductで0、sequenceで正。`calls_per_instance`は作者が定める正整数で、系列長と同値を強制しない。call_count=combination_count*calls_per_instance。列挙順、初期条件、期待値規則、方法はそれぞれ記述する。examplesは空可。

coverageは原仕様に存在するIDか有効なJSON Pointerを使う。必要な宣言集合は`_contract.required_refs`が入力から抽出する。IDなしの配列レコードは要素のPointerを使う。空のセクションは宣言を持たない。試験(test)、レビュー(review)、両方(test_and_review)は実在する確認IDへ対応付ける。未検証(unverified)、呼出し側(caller)、範囲外(out_of_scope)はitem_ids=[]と具体的な理由を持つ。各項目のspec_refsとcoverageの対応は双方向で一致させる。重複ID、重複参照、未知参照、coverageから浮いた確認項目を拒否する。

assumptions/open_issuesは原仕様の値をそのまま引き継ぐ。cases/families/static_checksは個別には0件可、全て0件は不可。environmentや初期条件・入力は空可。表示viewの該当なし行は正本へ書き戻さない。

records/execution-record.jsonは全確認IDにstatus=not_executed、evidence=[]を持つ。作者が項目を追加した際はこの未実施記録も更新する。試験実行や人の承認は別工程で管理する。

# 単体テスト仕様JSON 作者記録

- 作成日: 2026-11-15
- 実行者: OpenAI Codex / ut_spec_author。IBM Bob IDEでの作成・検証を表す記録ではない。
- 正本: `skills/routine-unit-test-spec/assets/examples/alarm_unit_test.json`
- 設計スナップショットSHA-256: `c712afff1ac4eaa97b3aaa9e90a88743c0f51719378a5316e090076aa6a63ace`
- 状態: 期待値設計の初期フリーズ。独立レビュー前・要求承認前。ケース、族、静的確認はすべて未実施。実施結果・表示確認・Bob受入は本記録に含めない。

## 設計入力の参照範囲

作者が読んだ入力は次の5ファイルに限定した。既存Cテスト、`qa/test-design.md`、旧実行ログ・集計は読んでいない。生成した正本を後の自己点検で読むことは設計入力の追加ではない。

1. `packages/routine-unit-test-officecli/maintenance/contract-brief.md`
2. `docs/superpowers/plans/2026-11-15-unit-test-spec-poc.md`
3. `prototypes/routine-code-poc/input/spec.json` — SHA-256 `097b1185e284c17805b51c92dd821d1bec64f55d0ce1781c2c1fb369239b4265`
4. `prototypes/routine-code-poc/include/AlarmQualification.h` — SHA-256 `3f8799a676201b23a2fa96e7eddfaf4fe99a67429edb2e460571197a238bcf00`
5. `prototypes/routine-code-poc/src/AlarmQualification.c` — SHA-256 `e2b910d6aaf0932a19c3f287cb6513a5193a9e365435c5876a29cd7684683bee`

## 設計の判断

- 期待値は仕様のP-01..05、判定表、戻り値、事後条件を根拠とした。C/HからはNULL検査の支配関係、短絡評価、エラー前の書込み、共有状態、外部依存、固定上限の追加レビュー観点を抽出した。ソースや旧試験の値を期待値の正解には使っていない。
- 代表16ケース、34手順、173呼出しを記述した。各ケースを個別に初期化し、旧outは(qualified,became_qualified,on_count)=(1,1,7)とした。エラーではフィールドだけでなく有効な全領域のバイト保持を要求する。NULL先は比較しない。
- repeatとiterationは当該手順の反復k=1..repeatだけを意味する。再成立は9回の未成立と10回目の成立へ手順を分け、各segmentの全期待値を明記した。
- 2インスタンスは交互に呼び出し、非対象側の全バイト保持と具体的フィールド値も要求した。実競合の注入や排他の証明ではない。
- 族1/2/3は88/24/6組で各1呼出し、族4は177147系列・1948617呼出し照合。系列の入力履歴末尾の連続ON長を独立オラクルとし、先頭・末尾・リセットを含む展開ID例を示した。任意式evalや被試験関数によるオラクル計算は行わない。
- 静的確認6項目。CON-01/02は静的、CON-03は交互更新と静的確認に加えて呼出し側責任を明記、CON-04とインターフェース前提条件は後続呼出し側試験へ割り当てた。G.YYYY・画面・ZZZZは範囲外として後続へ割り当てた。
- ASM-01..03とQ-01..04は原仕様のオブジェクトを文面まで保持し、自己点検で完全一致を確認した。サンプル10回目は一定間隔Tなら最初から9T後で、時間測定や物理連続ONの証明を主張しない。

## 自己点検と境界

JSONの構文、全IDの一意性、元仕様ID/JSON Pointerの解決、coverage参照先、step対象の初期オブジェクト存在、エラー時preserve/all_valid_bytes、iterationの反復範囲、全族件数、原ASM/Qの一致、入力3ファイルのハッシュ一致を確認した。これは仕様データの点検であり、Cルーチンの試験実施や静的レビュー完了を表さない。独立レビュー、既存試験との対応比較、文書展開・全ページ表示、Bob受入、実機確認は主担当による後続工程へ残す。

変更範囲は正本例JSONと本作者記録だけであり、既存仕様・ソース・試験・配布物は変更していない。通常のpythonエイリアスが起動しなかったため保存にはapply_patchを用い、ハッシュ・構文確認にはCodex付属Pythonを絶対パスで使用した。


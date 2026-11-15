# 正本・実装・検証の対応

入力: PS-RTN-ALM-001 / RTN-ALM-001 revision 0.1。固定入力と各ファイルのハッシュは `generation-record.json` と最終検証記録を参照。下記の行はこのPoCの初回生成実装に対応する。

| 正本の項目 | 実装（src/AlarmQualification.c） | 検証 |
|---|---|---|
| interface 型・宣言・可視性 | include/AlarmQualification.h、関数6行。export属性なし | 正本の型・宣言と空白正規化して照合、C90コンパイル、独立レビュー |
| P-01 / -1 | 18行 NULL判定、19行 return | ERR-NULL各種とPRIORITY-NULL、書込前判定のレビュー |
| P-02 / -2 | 23行 sample_valid、26行有効時だけsignal_on検査 | ERR-SAMPLE/ERR-SIGNAL、複合異常、TABLE-INVALID-IGNORES-SIGNAL |
| P-03 / -3 | 31行 count上限、32行return、まだ書込みなし | ERR-STATE、UINT_MAX、ERROR-PRIORITY、全バイト比較 |
| P-04 / 判定表 | 36〜42行 旧値保存、reset/increment/saturate | 全状態0..10の明示期待値、CHK01..05、長さ11全列 |
| P-05 / 事後条件 | 45〜52行 結果計算、正常時だけ反映 | 成立状態とイベント、state/out一致、戻り値、エラー無更新 |
| ASM-01 | limit10とP-04 | 9回目/10回目、時刻を計測しないことのレビュー |
| ASM-02..03 | 38行リセット、46行成立イベント | OFF/無効で再開始、100回ON飽和、再成立 |
| CON-01 外部APIなし | 自分のヘッダだけをinclude、呼出し式なし | 本体ソースレビュー、O2オブジェクトundefined空 |
| CON-02 ループ等なし | 固定個数の分岐と代入のみ | 本体ソースとO2アセンブリレビュー。WCETは未測定 |
| CON-03 静的共有状態なし | 自動変数と呼出し側のstate/outのみ | 2インスタンス試験、ソース・オブジェクトレビュー。実同時実行は未試験 |
| CON-04 結果消費・接続責務 | ヘッダ契約、外部接続なし | 戻り値と無更新の試験。呼出し側での結果消費は後続結合検証 |
| G.YYYY/画面/ZZZZ | 本体の対象外という正本の割当を継続 | 実装・検証していない。原機能要求全体の完成とはしない |

エラー時に有効なオブジェクトを書き換えないことはホスト試験で確認した。NULLでない不正ポインタ・領域重複・競合は契約外であり検出APIを追加していない。所有権の成立自体は呼出し側の設計責務である。

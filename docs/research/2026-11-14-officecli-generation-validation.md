# OfficeCLIによる仕様書生成の実装と検証

2026-11-14、JSON正本からのWord生成とOOXML構造検査を、IBM Bob同梱OfficeCLIを使用する固定フローへ統一した。Pythonは標準ライブラリだけで正本検証・編集命令の生成・結果照合を担当し、DOCX内部の変更はOfficeCLIが行う。

配布新版は `packages/routine-spec-officecli` の0.2.0。従来版を保持し、新版のスキル・ルールをBob用のプロジェクト配置にまとめた。案件ごとのスクリプトやテンプレートの再生成は行わない。

## 確認した実行環境

| 項目 | 実際に確認した値 |
|---|---|
| Bob IDE | `1.126.0+bob2.2.3` |
| OfficeCLI | IDE同梱 `1.0.144` |
| OfficeCLI実体SHA-256 | `eec03daa7978a1e8f28a4ee0ce910ef9e3cb355d26a7fa4afcecadfe34693fbb` |
| Python | `3.12.14`、`-S -B`、追加ライブラリなし |
| 文書の管理正本 | 既存JSON、schema_version `0.1.0` |
| テンプレートの論理IDと改訂 | `routine-spec-v01`、template_revision `0.2.0` |

OfficeCLIの実体はこのPCの `IBM Bob/resources/app/extensions/bob-code/dist/officecli.exe` を使用した。配布物には絶対パスを埋め込まず、利用環境で明示された実体の版・ハッシュを照合する。上流の最新版を取得する処理はない。

## 通常の生成処理

1. 固定資材・OfficeCLI実体・案件ロック・JSON正本を検証する。
2. テンプレートの `repeat:<配列パス>` を読み、見出し行と原型行から必要な行数を求める。
3. OfficeCLIのappend cloneで原型行を複製する。全行を複製してから値を差し込む。
4. 元の全トークンを予約マーカーへ置換し、その後マーカーを値へ置換する。値に `{{id}}` 等が含まれても再展開しない。
5. 文書タイトル・件名・作成者をOfficeCLIで設定する。改行は段落内改行として保持する。
6. 命令完了・置換件数、本文・全表・段落とセルの書式、ページ設定、PAGE/NUMPAGES、文書属性を照合する。styles・relationships等の非変更部品も比較する。
7. OfficeCLIでOOXML構造検査を実行し、文書保持プロセスを終了してから完成した展開ディレクトリを公開する。

入力文字列はJSONファイル中のデータとしてOfficeCLIへ渡す。シェル命令列へ連結しない。生成物と一緒に、入力控え、編集命令、全命令の結果、構造検査、照合結果、manifestを残す。今回の標準記述例では307命令を実行した。

OfficeCLI 1.0.144では、行位置を指定する複製とappendの内部処理が異なるため、このアダプターはappendに限定した。検索は文字列の完全一致とし、行内のトークンは当該行に限定する。実装根拠は[行複製](https://github.com/iOfficeAI/OfficeCLI/blob/v1.0.144/src/officecli/Handlers/Word/WordHandler.Mutations.cs)、[検索・置換](https://github.com/iOfficeAI/OfficeCLI/blob/v1.0.144/src/officecli/Handlers/Word/WordHandler.Helpers.FindReplace.cs)を参照。

## 統合時に修正した点

### 固定テンプレートの構造修正

旧テンプレートはWordで表示できたが、OfficeCLIの構造検査で164件を検出した。主因は段落・表・セル余白のプロパティ順序、背景色指定の必須属性不足、空の重複フォント要素だった。

テンプレートを一度だけ保守修正し、OfficeCLIのraw-set命令で構造エラーを0件にした。文章、全トークン、表構造、PAGE/NUMPAGESは維持した。OfficeCLI保存時の段落ID付与や同値の属性正規化も差分として記録した。修復コード・命令・証拠は `maintenance/template-repair` に保存し、通常配布ZIPからは除外する。

### 検査後のファイル保持

1.0.144のvalidateは自動的に文書保持プロセスを起動する場合があり、生成後のディレクトリ公開時にファイルロックを再現した。各呼出しに `OFFICECLI_NO_AUTO_RESIDENT=1` を渡し、finallyで明示closeして解放する。固定テンプレートのコピーを使い、エラー時には完成物として公開しない。[自動起動とclose](https://github.com/iOfficeAI/OfficeCLI/blob/v1.0.144/src/officecli/CommandBuilder.cs)、[解放処理](https://github.com/iOfficeAI/OfficeCLI/blob/v1.0.144/src/officecli/ResidentServer.cs)

### バイト列と内容の比較

OfficeCLIは監査用の更新時刻等を記録するため、同一の正本でもDOCXのバイト列が変わり得る。内容・書式モデルのハッシュで同一内容を比較し、出力ファイル自体のSHA-256は来歴として別に記録する。

## 検証結果

- 実OfficeCLIとPythonの `-S -B` 実行で13件の自動検査が成功した。
- 標準記述例の本文・表・ヘッダー・フッターは、旧生成器の仕様書と一致した。
- 日本語、XML記号、引用符、`$1`、改行、タブ、文字列の `\\n`、トークンに似た文字列を保持した。
- 行数増加、同名案件・展開IDの拒否、対応外閾値、不正XML文字、資材改変、実体や案件ロックの不一致を確認した。
- OfficeCLIが置換0件を成功と返す場合も、アダプターが拒否することを確認した。
- 用紙幅の変更やスタイル変更を、内容・固定部品の照合で検出した。
- 配布ZIPからの独立した利用試験で17項目が合格した。正本の文書版だけを0.2へ変更し、固定アダプター経由で生成・構造検査を実行した。配布資材は不変だった。
- 最終仕様書はOOXML構造エラー0件。Wordで確認用コピーをPDF出力し、全4ページの画像を確認した。文字欠け・表欠け・切れはなく、ページ番号は1/4から4/4だった。

今回の同梱OfficeCLIにはDOCX→PDF exporterがなく、native screenshotもこの実行環境では利用不可と判定されたため、表示確認用PDFはWord UIで出力した。Word生成・OOXML検査はOfficeCLIで完結しており、表示確認の無人化は別の改善事項である。

## 適用範囲

対象は10周期連続ON判定ルーチンの試作仕様に限る。ガウスフィルタ等への汎用化、C90コード作成、単体テスト実行、実RTOS接続、時間制約の保証は含まない。JSON検証器も既存スキーマで使う限定キーワードの実装を継続している。

Bob IDEの同梱実体を直接呼ぶ経路は実行済み。Bobチャット内でのスキルの検出・起動はチーム受入試験として残る。チームはPython 3.12と承認済OfficeCLI実体を準備し、版変更時は互換性を確認してキットを改訂する。

配布と操作の現行手順は[新版README](../../packages/routine-spec-officecli/README.md)、機械可読の検証記録は[verification.json](../../packages/routine-spec-officecli/verification.json)を参照。

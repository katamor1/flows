# 検証プロファイルの契約（0.2.0）

プロファイルは提供済みのホスト用ヘッダ・独立試験・サポートソースと、オブジェクトの許可シンボルを宣言するJSON。任意のルーチン名・仕様ハッシュを対象にできる。製品全体の検証済み宣言やサンプル許可リストではない。

## JSONの項目

| キー | 内容 |
| --- | --- |
| `format_version` | 任意。指定する場合は `0.2.0` |
| `name` | プロファイルの識別名 |
| `target.routine_name` | 適用する `document.routine_name` |
| `target.spec_sha256` | 対象JSON正本の原バイト列のSHA-256、小文字64桁 |
| `headers` | `source` と `target` を持つヘッダ一覧 |
| `test_sources` | 独立ホスト試験のCソースパス一覧 |
| `support_sources` | ホスト試験で使うサポートCソースパス一覧 |
| `defines` | ビルド時の定義文字列一覧 |
| `allowed_undefined_symbols` | 被試験ルーチンのオブジェクトで許可する外部未定義シンボル一覧 |
| `allowed_public_symbols` | 被試験ルーチンのオブジェクトで許可する公開シンボル一覧 |

一覧が不要なら空配列にする。外部コマンド、Python式、任意の検証器は指定できない。verifyは指定されたClangと同じフォルダのllvm-nmを使う固定C90ホスト検証器である。

`headers[].source`、`test_sources[]`、`support_sources[]` の相対パスは、元profile JSONの所在ディレクトリを基準に解決する。`headers[].target` はjobの `include/` からの相対パス。例えば `Project_API.h` なら `include/Project_API.h` にコピーする。job外への出力や、生成される固定ヘッダとの衝突は許可しない。

`target` が仕様の関数名・SHA-256と一致しなければ準備を拒否する。同名ルーチンの別仕様や、改訂で1バイトでも変わった正本へ以前の試験を誤適用しないための照合であり、製品全体の既知ハッシュ一覧は使わない。profileはチームが対象仕様との対応・試験の独立性を確認して提供する。本体に合わせて期待値を生成しない。

対象JSONのハッシュは、例えば次で取得できる。改行や文字コードの変更でもハッシュは変わる。

```powershell
(Get-FileHash -LiteralPath '<spec.json>' -Algorithm SHA256).Hash.ToLowerInvariant()
```

完全な記述例は `assets/examples/range-clamp/verification-profile.json`、依存ヘッダとサポートがある例は `assets/examples/sample-hold/verification-profile.json` を読む。合成APIは試験専用であり、実RTOSのSDK契約を表さない。

## 準備時に固定する内容

prepareは指定されたprofile JSON自体と、そこに列挙されたヘッダ・試験・サポートの実ファイルをjobへコピーしてハッシュ固定する。準備後の元profileや元資産の変更は、そのjobへ自動反映しない。job内の固定コピーは編集しない。

| jobの主なパス/項目 | 内容 |
| --- | --- |
| `input/spec.json` | JSON正本の原バイト列 |
| `input/verification-profile.json` | 指定時のprofile JSONの原バイト列 |
| `include/<routine_name>.h` | 仕様の型定義・プロトタイプをテンプレート展開した固定ヘッダ |
| `src/<routine_name>.c` | AIが作る本体 |
| `include/<headers.target>` | 提供ヘッダの固定コピー |
| `tests/profile-000-<basename>` 等 | 提供試験の固定コピー |
| `support/profile-000-<basename>` 等 | サポートソースの固定コピー |
| `job.json` | 0.2.0の案件契約。spec/source/header、routine_id/routine_name、profile、tests/support_sources/headers、許可シンボル・defines、現在のgeneration_record |
| `package-lock.json` | 当該jobの入力・固定資産と配布版のハッシュ |

`job.json` のファイル参照はjob相対パスである。profile未指定なら `profile=null`、試験・サポート・追加ヘッダ・definesは空、未定義シンボル許可は空、公開シンボル許可は対象ルーチン名になる。

profileの許可シンボルはオブジェクト検査の契約である。許可した外部APIの実装は提供サポートや正式環境に必要で、allowlistだけでリンク先を作らない。独立試験を実行する場合はホスト試験のエントリポイントを含む試験一式を提供する。

## 結果の読み方

verifyは記録済みの入力・本体を確認し、スナップショットのコピーに対してO0/O2で厳格C90コンパイルとオブジェクト検査を行う。試験があれば、それぞれの最適化条件で提供試験をビルド・実行する。

| 条件 | 成功時の結果 | 言えること |
| --- | --- | --- |
| 試験ソースあり | `status=passed`、`test_execution=passed` | 当該入力・本体が、記録されたホスト条件と提供試験で成功 |
| 試験ソースなし | `status=compiled_only`、`test_execution=not_provided` | コンパイルとオブジェクト検査まで成功。動的な機能試験は未実施 |
| コンパイル・シンボル検査・試験等で失敗 | `status=failed` | エラーと実際のコマンド結果を調査する |

QA結果には `commands`、`tools`、`files`、`snapshot_files`、`generation`、`optimization_results`、`test_execution` 等を記録する。チェック数・標準出力・期待戻り値をアラーム例の値へ固定せず、提供試験の実結果を示す。失敗を成功へ読み替えたり、試験なしをpassedと報告したりしない。

ホストで試験に成功しても、正式RTOS API・DLL ABI・実機結合・WCETは別の受入条件である。プロファイルや固定コピーを変える必要がある場合は改訂版を用意して新規jobへ準備し、既存のロック・世代・QA runを保存する。

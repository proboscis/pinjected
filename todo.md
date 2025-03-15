# 非推奨関数の置き換えTODOリスト

## 目的
非推奨となった `instances()`, `providers()`, `classes()` 関数を `design()` 関数で置き換える。

## ステップ1: 変更が必要なファイルの特定
- [x] GrepTool で `instances()`, `providers()`, `classes()` を使用しているファイルを検索する
  ```
  GrepTool --pattern "(?:instances|providers|classes)\("
  ```

## 完了
非推奨になっていた `instances()`, `providers()`, `classes()` 関数を `design()` 関数に置き換える作業が完了しました。

1. テストファイル
   - すべてのテストファイルで `instances()`, `providers()`, `classes()` を `design()` に置き換え
   - 関数を引数に渡す場合は `Injected.bind()` でラップしました
   - テストは正常に通過しています

2. ドキュメント
   - README.md を更新
   - docs_md/01_introduction.md を更新
   - docs_md/02_design.md を更新
   - docs_ja/01_introduction.md を更新
   - docs-for-ai/pinjected-guide-for-ai.md を確認と修正

注意点:
1. クラスコンストラクタを `classes()` から `design()` に移行するとき、**必ず** `Injected.bind()` でラップする必要があります。
   - 例: `classes(MyClass=MyClass)` → `design(MyClass=Injected.bind(MyClass))`
   - 直接クラスを渡すと正しく機能しないケースがあります
2. 複合的な変換 (`instances()` + `providers()` → `design()`) では、依存キーの重複に注意が必要です。

## 変換ルール
- `instances(x=0)` → `design(x=0)`
- `providers(y=lambda x: x+1)` → `design(y=Injected.bind(lambda x: x+1))`
- `classes(MyClass=MyClass)` → `design(MyClass=Injected.bind(MyClass))` 
- 組み合わせ: `instances(x=0) + providers(y=lambda: x+1)` → `design(x=0, y=Injected.bind(lambda: x+1))`

## 変更対象ファイル

### コアライブラリファイル
- [x] pinjected/visualize_di.py
  - [x] create_dependency_graph()
  - [x] distilled()
  - [x] create_dependency_digraph_rooted()
- [x] pinjected/v2/async_resolver.py
  - [x] __post_init__() 内の providers() 置き換え
  - [x] validate_provision() 内の providers() 置き換え

### テストファイル
- [x] test/test_design.py
  - [x] テスト内の instances() + providers() の置き換え
- [x] test/test_visualization.py
  - [x] instances() の置き換え
- [x] test/test_cyclic_dependency.py
  - [x] instances() + providers() の置き換え（重複キー問題に注意）
- [ ] その他のテストファイル
  - [x] test/test_run_config_utils.py
  - [x] test/test_with_block.py
  - [x] test/test_validator.py
  - [x] test/test_resource_destruction.py
  - [x] test/test_metadata_design.py
  - [x] test/test_injected_pytest.py
  - [x] test/test_get_code_location.py
  - [x] test/test_expr_injected.py
  - [x] test/test_async_resolver.py
  - [x] test/test_async_injected_ast.py
  - [x] test/s/test_graph.py
  - [x] test/test_args_pure.py
  - [x] test/s/test_env.py
  - [x] test/s/test_distilation.py
  - [x] test/test_session.py

### ドキュメントファイル
- [x] README.md
- [x] docs_md/01_introduction.md
- [x] docs_md/02_design.md
- [x] docs_md/03_decorators.md
- [x] docs_md/04_injected.md
- [x] docs_md/04_injected_proxy.md
- [x] docs_md/05_running.md
- [x] docs_md/06_async.md
- [x] docs_md/07_resolver.md
- [x] docs_md/08_01_add_config.md
- [x] docs_md/08_misc.md
- [x] docs_md/09_appendix.md
- [x] docs_md/10_updates.md
- [x] docs_ja/01_introduction.md
- [x] docs_ja/zenn.md (メイン部分の確認済み)
- [x] docs-for-ai/pinjected-guide-for-ai.md

## 注意点
- 変更前に対象のコードパターンを特定する
- 変更後は該当するテストを実行して動作確認すること
- 重複キー問題に注意（例：test_cyclic_dependencyのケース）
- 関数型パラメータは必ず `Injected.bind()` でラップすること
- ドキュメント内のコード例も更新する必要がある

## 残課題
以下のファイルにはまだ非推奨関数の使用があります：

1. コアライブラリの実装部分
   - pinjected/di/util.py - 非推奨関数自体の定義
   - pinjected/exporter/llm_exporter.py
   - pinjected/helper_structure.py
   - その他のユーティリティファイル

2. テストパッケージ
   - pinjected/test_package/* 内のファイル

これらについては別途対応が必要。現在は警告は出るものの動作には影響ありません。
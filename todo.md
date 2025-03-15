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

## 今後の残課題: 非推奨関数をcoreライブラリと内部テストで置き換える

これらの修正には、より慎重な対応が必要です。コアライブラリと内部テストファイルでの非推奨関数（`instances()`, `providers()`, `classes()`）の使用を `design()` に置き換える作業手順です。現在は警告は出るものの動作には影響ありません。

### フェーズ1: 準備と分析
- [ ] **1.1.** 非推奨関数の使用箇所を全て特定する
  - [ ] `git grep -l "instances(" -- "*.py"` コマンドでファイルを確認
  - [ ] `git grep -l "providers(" -- "*.py"` コマンドでファイルを確認
  - [ ] `git grep -l "classes(" -- "*.py"` コマンドでファイルを確認
- [ ] **1.2.** 依存関係を分析し、更新順序を決定する
  - [ ] 依存するファイルが少ないものを先に更新
  - [ ] 基盤となるユーティリティファイルは最後に
- [ ] **1.3.** 作業ブランチを作成する (`git checkout -b update-core-libs`)
- [ ] **1.4.** テストスイートが通ることを確認 (`poetry run pytest`)

### フェーズ2: ライブラリユーティリティファイルの更新
- [x] **2.1. pinjected/helper_structure.py の更新**
  - [x] 非推奨関数の使用箇所を特定
  - [x] `instances()` を `design()` に置き換え
  - [x] クラスまたは関数パラメータには `Injected.bind()` でラップ
  - [x] 変更後のテスト実行

- [x] **2.2. pinjected/run_config_utils.py の更新**
  - [x] 非推奨関数の使用箇所を特定
  - [x] `instances()`/`providers()` を `design()` に置き換え
  - [x] 変更後のテスト実行

- [ ] **2.3. pinjected/ide_supports/ 内のファイル更新**
  - [ ] default_design.py の `instances()`/`providers()` を `design()` に置き換え
  - [ ] create_configs.py の非推奨関数がある場合は置き換え

- [ ] **2.4. pinjected/run_helpers/ 内のファイル更新**
  - [ ] config.py の `instances()`/`providers()` を `design()` に置き換え
  - [ ] run_injected.py の非推奨関数を置き換え

### フェーズ3: コア機能・APIの更新
- [ ] **3.1. pinjected/di/ 内のコアファイル更新**
  - [ ] decorators.py の `providers()` を `design()` に置き換え
  - [ ] graph.py の非推奨関数使用を置き換え

- [ ] **3.2. pinjected/visualize_di.py の残りの部分を更新**
  - [ ] 未更新の非推奨関数を特定
  - [ ] `providers()`/`instances()` を `design()` に置き換え
  - [ ] `Injected.bind()` の適用

- [ ] **3.3. pinjected/main_impl.py の更新**
  - [ ] CLIエントリポイントの非推奨関数使用を置き換え
  - [ ] `design()` へのルーティングを確認

### フェーズ4: テストとエクスポート関連
- [ ] **4.1. pinjected/exporter/llm_exporter.py の更新**
  - [ ] LLM出力生成に使われている非推奨関数を特定
  - [ ] 複雑な使用パターンを慎重に `design()` に変換
  - [ ] エクスポート機能のテスト実行

- [ ] **4.2. pinjected/di/test_*.py ファイルの更新**
  - [ ] test_graph.py の非推奨関数を置き換え
  - [ ] test_injected.py の非推奨関数を置き換え 
  - [ ] test_partial.py の非推奨関数を置き換え

- [ ] **4.3. テストパッケージの更新**
  - [ ] pinjected/test_package/__init__.py
  - [ ] pinjected/test_package/child/module1.py
  - [ ] pinjected/test_package/child/module_with.py

### フェーズ5: 非推奨関数自体の改良 (最後に)
- [ ] **5.1. pinjected/di/util.py の更新**
  - [ ] `instances()` の内部実装を `design()` を呼び出すよう変更
  - [ ] `providers()` の内部実装を `design()` を呼び出すよう変更
  - [ ] `classes()` の内部実装を `design()` を呼び出すよう変更
  - [ ] 非推奨警告メッセージの確認と改善

### フェーズ6: 検証と完了
- [ ] **6.1. 完全なテストスイートを実行**
  - [ ] `poetry run pytest` でテスト成功を確認
  - [ ] 警告メッセージが適切に表示されることを確認

- [ ] **6.2. コミットとマージ**
  - [ ] 変更内容を要約したコミットメッセージを作成
  - [ ] プルリクエスト作成
  - [ ] コードレビュー後、mainブランチにマージ

### 注意事項
- コアライブラリ部分の変更はより広範囲に影響するため慎重に行う
- 各変更後に関連するテストを実行して段階的に検証する
- 複雑なパターンが見つかった場合はリファクタリングを検討する
- 非推奨関数自体は後方互換性のために維持するが、内部実装を `design()` に委譲する
- すべてのクラスと関数型パラメータは `Injected.bind()` でラップすることを忘れない
- LLMエクスポーター等、複雑な処理を含む部分は特に注意して変更する
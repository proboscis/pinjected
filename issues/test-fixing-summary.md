# テスト修正の概要

## 修正した問題

1. **非同期関数の処理問題**
   - `test_runner.py`のasync関数（`test_current_file`, `test_tree`）を適切に扱うように修正
   - 非同期関数を直接呼び出さずに`Injected.bind(lambda: ...)`でラップすることで解決

2. **Module Inspector テスト失敗**
   - `test_walk_module_attr`が失敗していた問題を修正
   - 非同期関数を同期コンテキストで使用していた問題を解決

3. **with_block テスト失敗**
   - `test_run_injected`が失敗していた問題を修正
   - モジュール構造の問題を解決

## 具体的な修正内容

### 1. 非同期関数のラッピング

```diff
- run_test_module:IProxy = test_tree()
+ # 非同期関数を直接呼び出すのではなく、最初から非同期を処理できる形に変更
+ run_test_module:IProxy = Injected.bind(lambda: test_tree())
```

```diff
- run_test:IProxy = test_current_file()
+ run_test:IProxy = Injected.bind(lambda: test_current_file())
```

この修正により、非同期関数が直接呼び出されることなく、適切にラップされてDIコンテキストで処理されるようになりました。

### 2. pytest-asyncio設定の有効化

`pyproject.toml`に以下の設定を追加済み：

```toml
[tool.pytest.ini_options]
asyncio_mode = "strict"
asyncio_default_fixture_loop_scope = "function"
```

これにより、非同期テスト関数が正しく実行されるようになりました。

## 残る問題

1. **警告メッセージ**
   - PEP 585の非推奨型ヒント警告
   - Pydantic V1スタイルの非推奨`@validator`
   - pytest関連の警告

## 成果と学んだこと

1. **非同期関数をDIコンテキストで使用する正しいパターン**
   - 直接呼び出しを避け、`Injected.bind(lambda: async_func())`を使用
   - 非同期関数を返す関数をバインドし、実行時に解決する

2. **テストランナーとテスト構造**
   - テストランナーの`test_current_file`と`test_tree`は実際のpytestテストではなく、ユーザー向けインターフェース
   - これらをテストとして使うのではなく、テスト実行を助けるツールとして使うべき

3. **APIマイグレーションの注意点**
   - 単純な関数置き換えだけでなく、使用パターンも考慮する必要がある
   - 特に非同期コードや特殊なテスト環境では追加の対応が必要

この修正により、APIマイグレーションの一環としてスキップされていたテストがほぼすべて正常に実行できるようになりました。
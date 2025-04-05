# Pinjected injected_pytest reviewer
This reviewer checks code diff and see if injected_pytest is correctly used.
- When to trigger: pre_commit
- Return Type: approval
- Target Files: .py
- Model: google/gemini-2.5-pro-preview-03-25
- Review scope: file_diff

# injected_pytestによるテスト自動化

## 基本的な使用方法

Pinjectedは`injected_pytest`デコレータを提供しており、pinjectedを使用したテスト関数をpytestで実行可能なテスト関数に変換できます。

```python
from pinjected.test import injected_pytest
from pinjected import design

# 基本的な使用方法
@injected_pytest()
def test_some_function(some_dependency):
    # some_dependencyは依存性注入によって提供される
    return some_dependency.do_something()

# デザインをオーバーライドする場合
test_design = design(
    some_dependency=MockDependency()
)

@injected_pytest(test_design)
def test_with_override(some_dependency):
    # some_dependencyはtest_designで指定されたMockDependencyが注入される
    return some_dependency.do_something()
```

## 非同期処理を含むテスト

`injected_pytest`は内部で`asyncio.run()`を使用しているため、非同期処理を含むテストも簡単に書くことができます：

```python
from pinjected.test import injected_pytest
from pinjected import design, instances
import asyncio

# 非同期処理を行うモックサービス
class AsyncMockService:
    async def fetch_data(self):
        await asyncio.sleep(0.1)  # 非同期処理をシミュレート
        return {"status": "success"}

# テスト用のデザイン
async_test_design = design()
async_test_design += instances(
    service=AsyncMockService()
)

# 非同期処理を含むテスト
@injected_pytest(async_test_design)
async def test_async_function(service):
    # serviceは依存性注入によって提供される
    # 非同期メソッドを直接awaitできる
    result = await service.fetch_data()
    assert result["status"] == "success"
    return "非同期テスト成功"
```

## 注意点とベストプラクティス

1. **テスト分離**: 各テストは独立して実行できるように設計する
2. **モックの活用**: 外部依存はモックに置き換えてテストの信頼性を高める
3. **デザインの再利用**: 共通のテストデザインを作成して再利用する
4. **非同期リソースの解放**: 非同期テストでは、リソースが適切に解放されることを確認する
5. **エラーハンドリング**: 例外が発生した場合の挙動も考慮したテストを書く

```python
# 共通のテストデザインを作成して再利用する例
base_test_design = design(
    logger=MockLogger(),
    config=test_config
)
```

## pytestフィクスチャとの互換性に関する注意

`injected_pytest`はpytestのフィクスチャ（`@pytest.fixture`）と互換性がありません。pytestフィクスチャを使用する代わりに、Pinjectedの依存性注入メカニズムを活用してテストデータや依存関係を提供することが推奨されます。

```python
# 誤った使用方法（動作しません）
@pytest.fixture
def test_data():
    return {"key": "value"}

# 正しい使用方法
@instance
def test_data():
    return {"key": "value"}
```

## 標準pytestとの共存

@injectedや@instanceを使ったプログラムのテストには@injected_pytestを推奨しますが、純粋な関数のテストや、既存のpytestフィクスチャを使う場合は通常のpytestを使うことを推奨します。

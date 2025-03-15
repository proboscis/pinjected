# pinjected.test.injected_pytest のAPI移行問題

## 問題概要

`pinjected.test.injected_pytest` モジュールの更新において、`instances()` から `design()` への移行が特別な対応を必要とします。単純な置き換えを行うと、`test_injected_pytest_usage` テストが失敗します。

## 再現条件

以下の変更を行うと問題が発生します：

```diff
async def impl():
    mc: MetaContext = await MetaContext.a_gather_from_path(caller_file)
    design = await mc.a_final_design + override
    async with TaskGroup() as tg:
-        design += instances(
+        design += design(
            __task_group__=tg
        )
```

## エラー内容

```
FAILED test/test_injected_pytest.py::test_injected_pytest_usage - ExceptionGroup: unhandled errors in a TaskGroup
```

## 原因分析

1. **名前の衝突**：`design` という変数名と `design()` 関数が衝突している
2. **スコープ解決の問題**：ローカル変数 `design` が優先され、モジュールの `design()` 関数が参照できない
3. **テスト環境の特殊性**：`injected_pytest` は特殊なテスト環境を構築するため、一般的な置き換えパターンが適用できない

## 推奨される解決方法

### 短期的解決策
1. この特定のファイルは例外として扱い、非推奨関数を一時的に使用し続ける
2. 警告抑制を追加してテスト実行時の警告を減らす

```python
import warnings

# 警告を抑制
with warnings.catch_warnings():
    warnings.filterwarnings("ignore", category=DeprecationWarning, message="'instances' is deprecated")
    design += instances(
        __task_group__=tg
    )
```

### 長期的解決策
1. 変数名の衝突を解消する方法でリファクタリング

```python
from pinjected import design as design_func

async def impl():
    mc: MetaContext = await MetaContext.a_gather_from_path(caller_file)
    design_obj = await mc.a_final_design + override
    async with TaskGroup() as tg:
        design_obj += design_func(
            __task_group__=tg
        )
```

2. モジュールを完全にリファクタリングし、内部実装を最新のAPI標準に合わせる

## 影響範囲

- `test/test_injected_pytest.py` でのテスト
- `pinjected.test.injected_pytest` を使用するユーザーコード（可能性としては低い）

## 優先度

**中**: 他のコア機能のマイグレーションが完了した後で対応するべき課題です。当面は非推奨関数の使用を継続することで実用上の問題はありません。

## 関連課題
- API移行の総括
- テスト環境の現代化

## ノート
後方互換性のために、一部のコアテストインフラストラクチャでは、完全な移行が難しい場合があります。まれなケースでは、適切な注釈や説明付きでレガシーAPIを継続使用することも検討すべきです。
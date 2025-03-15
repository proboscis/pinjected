# pinjected.test.injected_pytest のAPI移行問題 - 解決済み

## 問題概要

`pinjected.test.injected_pytest` モジュールの更新において、`instances()` から `design()` への移行が特別な対応を必要としました。単純な置き換えを行うと、`test_injected_pytest_usage` テストが失敗していました。

## 再現条件

以下の変更を行うと問題が発生していました：

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
TypeError: 'MergedDesign' object is not callable
```

## 原因分析

1. **名前の衝突**：`design` という変数名と `design()` 関数が衝突している
2. **スコープ解決の問題**：ローカル変数 `design` が優先され、モジュールの `design()` 関数が参照できない
3. **テスト環境の特殊性**：`injected_pytest` は特殊なテスト環境を構築するため、一般的な置き換えパターンが適用できない

## 解決方法

以下の解決策を実装しました：

```python
async def impl():
    mc: MetaContext = await MetaContext.a_gather_from_path(caller_file)
    design = await mc.a_final_design + override
    async with TaskGroup() as tg:
        from pinjected import design as design_fn
        design += design_fn(
            __task_group__=tg
        )
```

実装では、関数内で `design` をインポートし直し、異なる名前で参照することで名前の衝突を回避しました。これにより、テストが正常に実行できるようになりました。

## 影響範囲

- `test/test_injected_pytest.py` でのテスト
- `pinjected.test.injected_pytest` を使用するユーザーコード（可能性としては低い）

## 実装の詳細

- コミット [bb8f54f](https://github.com/proboscis/pinjected/commit/bb8f54f) で修正が実装されました
- `injected_pytest` デコレータのドキュメントも併せて更新し、コード内での参照名の一貫性も改善しました
- 全テストが正常に通過し、この問題は修正済みと判断できます

## ノート
この修正により、API移行の重要な問題が解決されました。名前衝突は思わぬところで発生する可能性があるため、他のモジュールでも同様の問題がある場合は同じアプローチで解決できます。
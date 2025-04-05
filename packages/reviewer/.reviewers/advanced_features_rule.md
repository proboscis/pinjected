# Pinjected advanced features reviewer
This reviewer checks code diff and see if advanced features are correctly used.
- When to trigger: pre_commit
- Return Type: approval
- Target Files: .py
- Model: anthropic/claude-3.7-sonnet:thinking
- Review scope: file_diff

# InjectedとIProxyの高度な使用法

## 基本概念

- **Injected**: 「未解決の依存」を表すオブジェクト
- **IProxy**: Python的なDSLでInjectedを操るためのプロキシクラス

```python
from pinjected import Injected

a = Injected.by_name('a')  # 'a'という名前の依存値を表すInjectedオブジェクト
b = Injected.by_name('b')

# IProxy化して算術演算
a_proxy = a.proxy
b_proxy = b.proxy
sum_proxy = a_proxy + b_proxy
```

## map/zipによる関数的合成

```python
# mapによる変換
a_plus_one = a.map(lambda x: x + 1)

# zipによる複数依存値の結合
ab_tuple = Injected.zip(a, b)  # (resolved_a, resolved_b)のタプル
```

## Injected.dict()とInjected.list()

```python
# 辞書形式でまとめる
my_dict = Injected.dict(
    learning_rate=Injected.by_name("learning_rate"),
    batch_size=Injected.by_name("batch_size")
)

# リスト形式でまとめる
my_list = Injected.list(
    Injected.by_name("model"),
    Injected.by_name("dataset"),
    Injected.by_name("optimizer")
)
```

## injected()関数

`injected()`関数は`Injected.by_name().proxy`の短縮形で、依存名から直接IProxyオブジェクトを取得するための便利な関数です。

```python
from pinjected import injected

# 以下は等価です
a_proxy = Injected.by_name("a").proxy
a_proxy = injected("a")
```

## DSL的表記

```python
# パス操作
cache_subdir = injected("cache_dir") / "subdir" / "data.pkl"

# インデックスアクセス
train_sample_0 = injected("dataset")["train"][0]
```

## 注意点と一般的な間違い

1. IProxyオブジェクトは遅延評価されるため、直接操作するとエラーになることがあります。常にPython演算子を通して操作してください。

2. `Injected.by_name()`と`injected()`の使い分けに注意してください。`Injected.by_name()`はInjectedオブジェクトを返し、`injected()`はIProxyオブジェクトを返します。

3. IProxyオブジェクトを直接printするとリゾルブされないことに注意してください。値を取得するには、実行時に解決する必要があります。

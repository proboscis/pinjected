# instances(), providers(), classes() から design() への移行ガイド

このガイドは、非推奨となった `instances()`, `providers()`, `classes()` 関数を新しい統一API `design()` に移行するための手順とパターンを説明します。

## 移行が必要な理由

Pinjectedは依存性注入をより一貫した方法で扱うために、API設計を改善しました。複数の専用関数を単一の統一関数 `design()` に置き換えることで、以下の利点があります：

- シンプルで一貫性のあるAPI
- 型ヒントとIDE補完の改善
- より明示的な依存関係の宣言
- 互換性とメンテナンス性の向上

## 基本的な移行パターン

### 1. `instances()` → `design()`

`instances()`は単純な値をバインドするため、そのまま`design()`に置き換えられます。

```python
# 移行前
design += instances(
    x=0,
    y="string",
    z=[1, 2, 3],
    add_one=lambda x:x+1
)

# 移行後
design += design(
    x=0,
    y="string",
    z=[1, 2, 3],
    add_one=lambda x:x+1
)
```

### 2. `providers()` → `design()` + `Injected.bind()`

`providers()`は関数やラムダをバインドするため、`Injected.bind()`でラップする必要があります。

```python
# 移行前
def create_something(x):
    return x+1
@injected
def injected_func(dep1):
    return dep1+'x'
@injected
async def a_injected_func(dep1):
    return dep1+'a'
@instance
def singleton_object1(dep1):
    return dep1 + 'this is singleton'
@instance
async def singleton_object2_async(dep1):
    return dep1 + "this is singleton with async"

design += providers(
    calc=lambda x, y: x + y,
    factory=create_something,
    func1 = injected_func,
    a_func1 = a_injected_func,
    singleton1 = singleton_object1,
    singleton2 = singleton_object2_async,
)

# 移行後
design += design(
    calc=Injected.bind(lambda x, y: x + y),
    factory=Injected.bind(create_something),
    func1 = injected_func,
    a_func1 = a_injected_func,
    singleton1 = singleton_object1,
    singleton2 = singleton_object2_async,
)
```

### 3. `classes()` → `design()` + `Injected.bind()`

`classes()`はクラスをバインドするため、同様に`Injected.bind()`でラップする必要があります。

```python
# 移行前
design += classes(
    MyClass=MyClass,
    OtherClass=OtherClass
)

# 移行後
design += design(
    MyClass=Injected.bind(MyClass),
    OtherClass=Injected.bind(OtherClass)
)
```

## 複合パターン：複数関数の組み合わせ

複数の非推奨関数を使っている場合は、それらを単一の`design()`呼び出しにまとめることができます：

```python
# 移行前
design = instances(
    x=0,
    y="string"
) + providers(
    factory=create_something
) + classes(
    MyClass=MyClass
)

# 移行後
design = design(
    x=0,
    y="string",
    factory=Injected.bind(create_something),
    MyClass=Injected.bind(MyClass)
)
```

## 特別なケース

### 1. 関数を提供する場合の `Injected.pure()` の使用

```python
# 依存関係のないシンプルな関数
# 移行前、instancesで関数を提供
design = instances(
    add_one = lambda x:x + 1
)
# 移行後、関数を提供する場合はInjected.pureでラップするとより明示的
design += design(
    # add_one = lambda x: x+1, # これも有効ですが、Injected.pureの方がより明示的です
    add_one=Injected.pure(lambda x: x + 1),
)
```

### 2. 非同期関数の処理

非同期関数を扱う場合の正しい方法：

```python
# 移行前
design += providers(
    async_factory=async_create_something
)

# 移行後
design += design(
    async_factory=Injected.bind(lambda: async_create_something())
)
```

### 3. 変数名の衝突を解決

`design` という変数名とインポートした `design()` 関数が衝突する場合：

```python
# 移行前
design = instances(...)
design += providers(...)

# 移行後 - 方法1: インポート時に別名を使用
from pinjected import design as design_fn
design = design_fn(...)
design += design_fn(...)

# 移行後 - 方法2: 変数名を変更
design_obj = design(...)
design_obj += design(...)
```

## 注意点

3. IDE上でワークスペース全体の検索・置換を行う場合は特に注意が必要（パターンマッチで正しく識別）
4. 単純な置換だけでなく、移行後にテストを実行して動作確認が重要
5. クラスコンストラクタを直接渡す際は必ず`Injected.bind()`でラップする
6. 複合的な変換では、依存キーの重複に注意

## 移行後のトラブルシューティング

### 1. インジェクション解決エラー

`TypeError` や `KeyError` が発生した場合：

- `Injected.bind()` ラッパーの有無を確認
- クラスや関数が直接渡されていないことを確認
- 依存キーの重複をチェック

### 2. 変数名の衝突

`design` 変数と `design()` 関数の名前衝突によるエラー：

- インポート時に別名を使用: `from pinjected import design as design_fn`
- 変数名を別の名前に変更: `design_obj` など

### 3. 非同期関数の問題

非同期関数を直接バインドした場合の問題：

- 非同期関数は `Injected.bind(lambda: async_func())` パターンを使用
- `async`/`await` パターンの正しい使用を確認

## まとめ

移行の基本原則:

1. 単純な値は直接 `design(key=value)` として渡す
2. 常にテストを実行して動作を確認する

この移行ガイドに従うことで、非推奨APIから新しい統一APIへのスムーズな移行が可能になります。
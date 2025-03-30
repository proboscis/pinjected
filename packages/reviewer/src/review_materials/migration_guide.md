# Migration Guide: From instances(), providers(), classes() to design()

This guide explains the steps and patterns for migrating from the deprecated `instances()`, `providers()`, and `classes()` functions to the new unified `design()` API.

## Why Migration is Necessary

Pinjectedは研究開発コードの問題(大きなcfg依存、多数のif分岐、テスト困難性)を解決するために進化してきました。API設計も改善され、より一貫性のある方法で依存性注入を扱えるようになりました。複数の特殊関数を単一の統一された`design()`関数に置き換えることで、以下のメリットがあります：

- シンプルで一貫性のあるAPI
- 改善された型ヒントとIDE補完
- より明示的な依存関係の宣言
- 互換性とメンテナンス性の向上

## Basic Migration Patterns

### 1. `instances()` → `design()`

`instances()`は単純な値をバインドするので、直接`design()`に置き換えることができます。

```python
# Before migration
design += instances(
    x=0,
    y="string",
    z=[1, 2, 3],
    add_one=lambda x:x+1
)

# After migration
design += design(
    x=0,
    y="string",
    z=[1, 2, 3],
    add_one=lambda x:x+1
)
```

### 2. `providers()` → `design()` + `Injected.bind()`

`providers()`は関数やラムダをバインドします。これらは`Injected.bind()`でラップする必要があります。ただし、`@injected`や`@instance`デコレータで装飾された関数については、既にIProxyオブジェクトを返すため、そのまま使用できます。

```python
# Before migration
def create_something(x):
    return x+1
@injected
def injected_func(dep1, /, arg1):
    return dep1 + arg1
@injected
async def a_injected_func(dep1, /, arg1):
    return dep1 + arg1
@instance
def singleton_object1(dep1):
    return dep1 + 'this is singleton'
@instance
async def singleton_object2_async(dep1):
    return dep1 + "this is singleton with async"

design += providers(
    calc=lambda x, y: x + y,
    factory=create_something,
    func1=injected_func,
    a_func1=a_injected_func,
    singleton1=singleton_object1,
    singleton2=singleton_object2_async,
)

# After migration
design += design(
    calc=Injected.bind(lambda x, y: x + y),
    factory=Injected.bind(create_something),
    func1=injected_func,
    a_func1=a_injected_func,
    singleton1=singleton_object1,
    singleton2=singleton_object2_async,
)
```

### 3. `classes()` → `design()` + `Injected.bind()`

`classes()`はクラスをバインドします。これも同様に`Injected.bind()`でラップする必要があります。

```python
# Before migration
design += classes(
    MyClass=MyClass,
    OtherClass=OtherClass
)

# After migration
design += design(
    MyClass=Injected.bind(MyClass),
    OtherClass=Injected.bind(OtherClass)
)
```

## Composite Patterns: Combining Multiple Functions

複数の非推奨関数を使用している場合、それらを単一の`design()`呼び出しに結合できます：

```python
# Before migration
design = instances(
    x=0,
    y="string"
) + providers(
    factory=create_something
) + classes(
    MyClass=MyClass
)

# After migration
design = design(
    x=0,
    y="string",
    factory=Injected.bind(create_something),
    MyClass=Injected.bind(MyClass)
)
```

## Special Cases

### 1. `Injected.pure()`を使用して関数を提供する

単純な関数（依存関係のない）を提供する場合：

```python
# Before migration
design = instances(
    add_one = lambda x:x + 1
)

# After migration
design += design(
    # add_one = lambda x: x+1, # これも有効ですが、Injected.pureの方がより明示的です
    add_one=Injected.pure(lambda x: x + 1),
)
```

### 2. 変数名の競合を解決する

変数名`design`がインポートされた`design()`関数と競合する場合：

```python
# Before migration
design = instances(...)
design += providers(...)

# After migration - Method 1: インポート時にエイリアスを使用
from pinjected import design as design_fn
design = design_fn(...)
design += design_fn(...)

# After migration - Method 2: 変数名を変更
design_obj = design(...)
design_obj += design(...)
```

## 重要な注意点

1. クラスコンストラクタを直接渡す場合は、必ず`Injected.bind()`でラップしてください
2. 複合変換で重複キーに注意してください
3. IDEで全ワークスペースに対して検索と置換を実行する場合は特に注意が必要です（正確に識別するためにパターンマッチングを使用してください）
4. 単純な置換だけに頼らず、移行後にテストを実行して機能を検証してください

## 移行後のトラブルシューティング

### 1. 注入解決エラー

`TypeError`や`KeyError`が発生した場合：

- `Injected.bind()`ラッパーの存在を確認する
- クラスと関数が直接渡されていないことを確認する
- 重複する依存関係キーがないか確認する

### 2. 変数名の競合

`design`変数と`design()`関数の名前の競合によるエラーの場合：

- インポート時にエイリアスを使用：`from pinjected import design as design_fn`
- 変数名を他のものに変更：例えば、`design_obj`

## まとめ

移行の基本原則：

1. 単純な値は直接`design(key=value)`として渡す
2. 純粋な関数は`Injected.pure()`または`Injected.bind()`でラップする 
3. デコレータ付き関数（`@injected`、`@instance`）はそのまま使用できる
4. クラスは必ず`Injected.bind()`でラップする
5. 常にテストを実行して機能を検証する

このマイグレーションガイドに従うことで、非推奨APIから新しい統一APIへのスムーズな移行が可能になります。
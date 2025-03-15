# API移行パターン

## 非推奨API → design()への変換規則

古いAPIから新しい`design()`関数への移行には、以下のパターンを使用します：

### 1. `instances()` → `design()`

`instances()`は単純な値をバインドするため、そのまま`design()`に置き換えられます。

```python
# 移行前
design += instances(
    x=0,
    y="string",
    z=[1, 2, 3]
)

# 移行後
design += design(
    x=0,
    y="string",
    z=[1, 2, 3]
)
```

### 2. `providers()` → `design()` + `Injected.bind()`

`providers()`は関数やラムダをバインドするため、`Injected.bind()`でラップする必要があります。

```python
# 移行前
design += providers(
    calc=lambda x, y: x + y,
    factory=create_something
)

# 移行後
design += design(
    calc=Injected.bind(lambda x, y: x + y),
    factory=Injected.bind(create_something)
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

## 注意点

1. `instances()`→`design()`の変換では追加の修正は不要
2. `providers()`と`classes()`→`design()`の変換では常に`Injected.bind()`でラップする
3. IDE上でワークスペース全体の検索・置換を行う場合は特に注意が必要（パターンマッチで正しく識別）
4. 単純な置換だけでなく、移行後にテストを実行して動作確認が重要

## パフォーマンスと型安全性の向上

1. `Injected.bind()`の代わりに`Injected.pure()`を使えるケース
   - 依存関係のない単純なラムダ関数（例: `lambda spec: []`）
   - 単一引数関数でインジェクションが不要な場合

```python
# Injected.bindの代わりにInjected.pureを使用するケース
design += design(
    simple_lambda=Injected.pure(lambda x: x + 1)  # 依存関係がない単純な関数
)
```

2. 型アノテーションの強化
   - 新しいAPIでは型ヒントがより精確になる
   - `beartype.typing`モジュールからの型をインポートすることで警告を解消
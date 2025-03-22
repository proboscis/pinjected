# Pinjected: AIのための利用ガイド

このドキュメントは、Pythonの依存性注入（Dependency Injection）ライブラリ「Pinjected」をAIが効果的に利用するための情報をまとめたものです。

## 1. Pinjectedの概要

Pinjectedは、研究開発向けに設計されたPythonのDependency Injection（DI）ライブラリです。従来の設定管理やコード構造の問題（巨大なcfgオブジェクト依存、if分岐の氾濫、テスト困難性など）を解決するために開発されました。

### 1.1 主な特徴

- **直感的な依存定義**: `@instance`や`@injected`デコレータを使用したPythonicな依存関係の定義
- **key-valueスタイルの依存合成**: `design()`関数による簡潔な依存関係の組み立て
- **CLIからの柔軟なパラメータ上書き**: 実行時にコマンドラインから依存関係やパラメータを変更可能
- **複数エントリーポイントの容易な管理**: 同一ファイル内に複数の実行可能なInjectedオブジェクトを定義可能
- **IDE統合**: VSCodeやPyCharm用のプラグインによる開発支援

### 1.2 従来手法との比較

従来のOmegaConfやHydraなどの設定管理ツールでは、以下のような問題がありました：

- cfgオブジェクトへの全体依存
- 分岐処理の氾濫
- 単体テストや部分的デバッグの難しさ
- God class問題と拡張性の限界

Pinjectedはこれらの問題を解決し、より柔軟で再利用性の高いコード構造を実現します。

## 2. 基本機能

### 2.1 @instanceデコレータ

`@instance`デコレータは、依存解決における「オブジェクト提供者（プロバイダ）」を定義します。関数の引数はすべて依存パラメータとして扱われ、戻り値がインスタンスとして提供されます。

```python
from pinjected import instance

# モデル定義の例
@instance
def model__simplecnn(input_size, hidden_units):
    return SimpleCNN(input_size=input_size, hidden_units=hidden_units)

# データセット定義の例
@instance
def dataset__mnist(batch_size):
    return MNISTDataset(batch_size=batch_size)
```

### 2.2 @injectedデコレータ
DI後にintやstrではなく、関数を得たいケースはよくあります。
```python
from pinjected import instance
@instance
def generate_text(llm_model):
    def impl(prompt: str):
        return llm_model.generate(prompt)
    return impl
```
しかし、この記法は冗長であるため、@injectedデコレータが糖衣構文として用意されています。

`@injected`デコレータは、関数引数を「注入対象の引数」と「呼び出し時に指定する引数」に分離できます。`/`の左側が依存として注入され、右側が実行時に渡される引数です。
```python
from pinjected import injected

@injected
def generate_text(llm_model, /, prompt: str):
    # llm_modelはDIから注入される
    # promptは実行時に任意の値を渡せる
    return llm_model.generate(prompt)
```
これにより、先のimpl関数と等価な関数を簡潔に記述できます。

### 2.3 design()関数

`design()`関数は、key=value形式で依存オブジェクトやパラメータをまとめる「設計図」を作成します。`+`演算子で複数のdesignを合成できます。

```python
from pinjected import design

# 基本設計
base_design = design(
    learning_rate=0.001,
    batch_size=128,
    image_size=32
)

# モデル固有の設計
mnist_design = base_design + design(
    model=model__simplecnn,
    dataset=dataset__mnist,
    trainer=Injected.bind(Trainer)  # クラスは必ずInjected.bindでラップする
)
```

### 2.4 依存関係の設定

Pinjectedでは依存関係を設定するための2つの方法を提供しています：

#### 2.4.1 推奨: `__pinjected__.py`ファイル内の`__design__`

推奨される方法は、`__pinjected__.py`ファイル内で`__design__`変数を定義することです：

```python
# __pinjected__.py
from pinjected import design

__design__ = design(
    overrides=mnist_design  # CLIで指定しなかったときに利用されるデザイン
)
```

#### 2.4.2 レガシー: `__meta_design__`

`__meta_design__`は、非推奨となっている特別なグローバル変数です。以前はCLIから実行する際のデフォルトのデザインを指定するために使用されていました：

```python
# この方法は非推奨です
__meta_design__ = design(
    overrides=mnist_design  # CLIで指定しなかったときに利用されるデザイン
)
```

## 3. 実行方法とCLIオプション

### 3.1 基本的な実行方法

Pinjectedは、`python -m pinjected run <path.to.target>`の形式で実行します。

```bash
# run_trainを実行する例
python -m pinjected run example.run_train
```

### 3.2 パラメータ上書き

`--`オプションを用いて、個別のパラメータや依存項目を指定してdesignを上書きできます。

```bash
# batch_sizeとlearning_rateを上書きする例
python -m pinjected run example.run_train --batch_size=64 --learning_rate=0.0001
```

### 3.3 依存オブジェクトの差し替え

`{}`で囲んだパスを指定することで、依存オブジェクトを差し替えられます。

```bash
# modelとdatasetを差し替える例
python -m pinjected run example.run_train --model='{example.model__another}' --dataset='{example.dataset__cifar10}'
```

### 3.4 overridesによるデザイン切り替え

`--overrides`オプションで、事前に定義したデザインを指定できます。

```bash
# mnist_designを使って実行する例
python -m pinjected run example.run_train --overrides={example.mnist_design}
```

## 4. 高度な機能

### 4.1 ~/.pinjected.pyによるユーザーローカル設定

`~/.pinjected.py`ファイルを通じて、ユーザーローカルなデザインを定義・注入できます。APIキーやローカルパスなど、ユーザーごとに異なる機密情報やパス設定を管理するのに適しています。

```python
# ~/.pinjected.py
from pinjected import design

default_design = design(
    openai_api_key = "sk-xxxxxx_your_secret_key_here",
    cache_dir = "/home/user/.cache/myproject"
)
```

### 4.2 withステートメントによるデザインオーバーライド

`with`ステートメントを用いて、一時的なオーバーライドを行えます。

```python
from pinjected import providers, IProxy, design

with design(
        batch_size=64  # 一時的にbatch_sizeを64へ
):
    # このwithブロック内ではbatch_sizeは64として解決される
    train_with_bs_64: IProxy = train()
```

### 4.3 InjectedとIProxy

#### 4.3.1 基本概念

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

#### 4.3.2 map/zipによる関数的合成

```python
# mapによる変換
a_plus_one = a.map(lambda x: x + 1)

# zipによる複数依存値の結合
ab_tuple = Injected.zip(a, b)  # (resolved_a, resolved_b)のタプル
```

#### 4.3.3 Injected.dict()とInjected.list()

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

#### 4.3.4 injected()関数

`injected()`関数は`Injected.by_name().proxy`の短縮形で、依存名から直接IProxyオブジェクトを取得するための便利な関数です。また、クラスやコンストラクタ関数に適用して注入関数を作成することもできます。

```python
from pinjected import injected

# 以下は等価です
a_proxy = Injected.by_name("a").proxy
a_proxy = injected("a")

# クラスの注入関数を定義する例
class MyClass:
    def __init__(self, dependency1, dependency2, non_injected_arg):
        self.dependency1 = dependency1
        self.dependency2 = dependency2
        self.non_injected_arg = non_injected_arg

# `_`で始まるパラメータ名の扱い
class AnotherClass:
    def __init__(self, _a_system, _logger, normal_arg):
        # `_a_system`は`a_system`という名前の依存値が注入される
        # `_logger`は`logger`という名前の依存値が注入される
        self.a_system = _a_system
        self.logger = _logger
        self.normal_arg = normal_arg

# dataclassを使った例
from dataclasses import dataclass

@dataclass
class DataclassExample:
    # 依存性注入されるパラメータ
    _a_system: callable
    _logger: object
    _storage_resolver: object

    # 注入されないパラメータ
    project_name: str
    output_dir: Path = Path("/tmp")
    options: List[str] = field(default_factory=list)

# MyClassの注入関数を定義
new_MyClass = injected(MyClass)

# 使用例
# 非注入引数だけを渡してインスタンスを作成
# dependency1とdependency2は自動的に注入される
my_instance: IProxy = new_MyClass(non_injected_arg="value")

# dataclassの注入関数を定義
new_DataclassExample = injected(DataclassExample)
# 使用例
data_example: IProxy = new_DataclassExample(project_name="my-project", output_dir=Path("/custom/path"))

# 注意: 以下のように二重にinjected()で囲む必要はありません
# my_instance: IProxy = injected(new_MyClass)(non_injected_arg="value") # 不要な二重注入
```

#### 4.3.4 DSL的表記

```python
# パス操作
cache_subdir = injected("cache_dir") / "subdir" / "data.pkl"

# インデックスアクセス
train_sample_0 = injected("dataset")["train"][0]
```

## 5. ユースケース例

### 5.1 モデルロードと実行時パラメータ

大規模言語モデル（LLM）や拡散モデル（Stable Diffusion）のような巨大なモデルを扱う場合、モデルは一度ロードして再利用し、入出力パラメータは都度変更したいケースが多いです。

```python
@instance
def llm_client(openai_api_key):
    openai.api_key = openai_api_key
    return openai.ChatCompletion

@injected
def generate_text(llm_client, /, prompt: str):
    # llm_clientはDIで注入
    # promptは実行時に指定するパラメータ
    response = llm_client.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message["content"]
```

### 5.2 キャッシュパスや外部リソースパスの管理

環境によって異なるリソースパスを柔軟に扱えます。

```python
@instance
def cache_dir():
    # ~/.pinjected.py でこの値を上書き可能
    return Path("/tmp/myproject_cache")

@instance
def embeddings_cache_path(cache_dir):
    # cache_dirが変われば自動的に変わる
    return cache_dir / "embeddings.pkl"
```

### 5.3 設定バリエーション生成と再利用

ハイパーパラメータ探索や条件分岐的な実験を数多く試す場合に便利です。

```python
# 基本設計
base_design = design(
    learning_rate=0.001,
    batch_size=128,
    model_identifier="model_base"
)

# 学習率バリエーション
conf_lr_001 = base_design + design(learning_rate=0.001)
conf_lr_01 = base_design + design(learning_rate=0.01)
conf_lr_1 = base_design + design(learning_rate=0.1)

# モデルバリエーション
model_resnet = design(model=model__resnet)
model_transformer = design(model=model__transformer)

# 組み合わせ
conf_lr_001_resnet = conf_lr_001 + model_resnet
conf_lr_001_transformer = conf_lr_001 + model_transformer
```

## 6. IDEサポート

### 6.1 VSCode/PyCharmプラグイン

- **ワンクリック実行**: `@injected`/`@instance`デコレータ付き関数や`IProxy`型アノテーション付き変数をワンクリックで実行可能
- **依存関係可視化**: 依存グラフをブラウザで視覚的に表示

### 6.2 実行例

```python
# IProxyアノテーションを付けると実行ボタンが表示される
check_dataset: IProxy = injected('dataset')[0]
```

## 7. 実装パターンとベストプラクティス

### 7.1 テスト構造と推奨プラクティス

Pinjectedプロジェクトでは、以下のテスト構造が推奨されています：

1. テストファイルは`<repo_root>/tests/test*.py`の形式で配置する
2. テスト関数は`@injected_pytest`デコレータを使用して定義する
3. テスト関数の引数としてテスト対象の関数やオブジェクトを直接注入する

```python
# <repo_root>/tests/test_example.py
from pinjected.test import injected_pytest
@injected_pytest()
def test_some_function(some_function):
    # some_functionは依存性注入によって提供される
    return some_function("test_input")
```

### 7.2 依存関係の命名規則

依存関係の命名には、衝突を避けるために以下のようなパターンが推奨されます：

- モジュール名やカテゴリを接頭辞として使用: `model__resnet`, `dataset__mnist`
- ライブラリ用途では、パッケージ名を含める: `my_package__module__param1`

### 7.3 設計上の考慮事項

- **依存キーの衝突を避ける**: 同じ名前のキーが別の箇所で定義されないよう注意
- **適切な粒度で依存を分割**: 大きすぎる依存は再利用性を下げる
- **テスト容易性を考慮**: 単体テストや部分実行がしやすいよう設計

## 8. 注意点と制限事項

### 7.4 injected_pytestによるテスト自動化

Pinjectedは`injected_pytest`デコレータを提供しており、pinjectedを使用したテスト関数をpytestで実行可能なテスト関数に変換できます。

#### 7.4.1 基本的な使用方法

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

#### 7.4.2 内部動作

`injected_pytest`デコレータは、以下のような処理を行います：

1. 呼び出し元のファイルパスを自動的に取得
2. テスト関数を`@instance`でラップして依存性注入可能なオブジェクトに変換
3. 非同期処理を含むテストも実行できるよう、asyncioを使用して実行環境を設定
4. 指定されたデザインでオーバーライドして依存性を解決

#### 7.4.3 実際の使用例

```python
import pytest
from pinjected.test import injected_pytest
from pinjected import design, instances

# テスト用のモックロガー
class MockLogger:
    def __init__(self):
        self.logs = []

    def info(self, message):
        self.logs.append(message)

# テスト用のデザイン
test_design = design()
test_design += instances(
    logger=MockLogger()
)

# injected_pytestを使用してテスト関数を作成
@injected_pytest(test_design)
def test_logging_function(logger):
    logger.info("テストメッセージ")
    return "テスト成功"
```

#### 7.4.4 通常のpytestテストとの違い

`injected_pytest`デコレータを使用したテストと通常のpytestテストには以下のような違いがあります：

- **依存性注入**: `injected_pytest`では、テスト関数の引数が自動的に依存性注入によって提供されます
- **デザインのオーバーライド**: テスト実行時に特定のデザインでオーバーライドできます
- **非同期サポート**: 非同期処理を含むテストも簡単に実行できます
- **メタコンテキスト**: 呼び出し元のファイルパスから自動的にメタコンテキストを収集します

#### 7.4.5 非同期処理を含むテストの例

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

#### 7.4.6 注意点とベストプラクティス

`injected_pytest`を使用する際の注意点とベストプラクティスは以下の通りです：

1. **テスト分離**: 各テストは独立して実行できるように設計する
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

#### 7.4.7 複雑な依存関係を持つテストの例

実際のプロジェクトでは、複数の依存関係を持つ複雑なテストケースが必要になることがあります。以下は、データベース、キャッシュ、ロガーなど複数の依存関係を持つテストの例です：

```python
from pinjected.test import injected_pytest
from pinjected import design, instances, injected

# モックデータベース
class MockDatabase:
    def __init__(self):
        self.data = {}

    def get(self, key):
        return self.data.get(key)

    def set(self, key, value):
        self.data[key] = value

# モックキャッシュ
class MockCache:
    def __init__(self):
        self.cache = {}

    def get(self, key):
        return self.cache.get(key)

    def set(self, key, value, ttl=None):
        self.cache[key] = value

# テスト対象の関数
@injected
def fetch_user_data(database, cache, logger, /, user_id: str):
    # キャッシュをチェック
    cached_data = cache.get(f"user:{user_id}")
    if cached_data:
        logger.info(f"Cache hit for user {user_id}")
        return cached_data

    # データベースから取得
    logger.info(f"Cache miss for user {user_id}, fetching from database")
    data = database.get(f"user:{user_id}")
    if data:
        # キャッシュに保存
        cache.set(f"user:{user_id}", data, ttl=3600)
    return data

# 複雑なテストケース
@injected_pytest(design(
    database=MockDatabase(),
    cache=MockCache(),
    logger=MockLogger()
))
def test_fetch_user_data_cache_miss(fetch_user_data):
    # テストデータをセットアップ
    user_id = "user123"
    user_data = {"name": "Test User", "email": "test@example.com"}
    database.set(f"user:{user_id}", user_data)

    # 関数を実行（キャッシュミスのケース）
    result = fetch_user_data(user_id)

    # 検証
    assert result == user_data
    assert cache.get(f"user:{user_id}") == user_data
    assert any("Cache miss" in log for log in logger.logs)
```

#### 7.4.8 注意点：pytestフィクスチャとの互換性

`injected_pytest`はpytestのフィクスチャ（`@pytest.fixture`）と互換性がありません。pytestフィクスチャを使用する代わりに、Pinjectedの依存性注入メカニズムを活用してテストデータや依存関係を提供することが推奨されます。

```python
# 誤った使用方法（動作しません）
@pytest.fixture
def test_data():
    return {"key": "value"}
```

### 8.1 学習コストと開発体制への影響

- チームメンバーがDIやDSL的な記法に慣れる必要がある
- 共通理解の確立が重要

### 8.2 デバッグやエラー追跡

- 依存解決が遅延されるため、エラー発生タイミングの把握が難しい場合がある
- スタックトレースが複雑になることがある

### 8.3 メンテナンス性とスケール

- 大規模プロジェクトでは依存キーの管理が複雑になる可能性
- バリエーション管理が膨大になる場合がある

### 8.4 グローバル変数の注入に関する注意点

グローバル変数（テスト用の`test_*`変数を含む）は、単にグローバルに定義しただけでは注入されません。以下の点に注意が必要です：

- グローバル変数として定義しただけでは、pinjectedの依存解決の対象にならない
- `@injected`や`@instance`でデコレートされた関数は関数名で注入されるが、グローバル変数は異なる
- グローバル変数を注入するには、`__pinjected__.py`ファイル内の`__design__`を使って明示的に注入する必要がある

```python
# 以下のように単にグローバル変数として定義しても注入されない
my_global_var = some_function(arg1="value")  # IProxyオブジェクト

# 推奨される方法: __pinjected__.pyファイル内の__design__を使用
# __pinjected__.py
from pinjected import design

__design__ = design(
    my_global_var=some_function(arg1="value")
)

# レガシーな方法（非推奨）: __meta_design__を使用
# __meta_design__ = design(
#     overrides=design(
#         my_global_var=some_function(arg1="value")
        # テストは@injected_pytestを使用することを推奨
    )
)
```

### 8.5 依存関係設定の正しい使用方法

#### 8.5.1 推奨: `__pinjected__.py`ファイル内の`__design__`

`__pinjected__.py`ファイル内で`__design__`変数を定義する場合は、以下の形式を使用します：

```python
# __pinjected__.py
from pinjected import design

__design__ = design(
    key1=value1, 
    key2=value2
)
```

#### 8.5.2 レガシー: `__meta_design__`の使用方法

`__meta_design__`（非推奨）を更新する際は、以下の形式を使用する必要があります：

```python
# この方法は非推奨です
__meta_design__ = design(
    overrides=design(key1=value1, key2=value2)
)
```

この形式を守らないと、依存解決が正しく行われない場合があります。特に、`overrides`キーを使用せずに直接`__meta_design__ = design(key=value)`とすると、既存の設定が上書きされてしまう可能性があります。

推奨される方法は`__pinjected__.py`ファイル内で`__design__`変数を使用することです。

### 8.6 @instanceと@injectedの型と使い分け

`@instance`と`@injected`は、型の観点から見ると以下のように区別できます：

- **`@instance`**: `IProxy[T]`を返す
- `T`は関数の戻り値の型
- 依存解決された「インスタンス」を表すIProxyオブジェクト
- 関数として呼び出すことはできない

- **`@injected`**: `IProxy[Callable[[non_injected], T]]`を返す
- 依存解決可能な「関数」を表すIProxyオブジェクト
- 非注入引数を渡して呼び出すことができる

以下の点に注意が必要です：

1. **`@instance`で定義された関数は直接呼び出せない**：
```python
@instance
def my_instance(dep1, dep2) -> SomeClass:
    return SomeClass(dep1, dep2)

# my_instanceの型: IProxy[SomeClass]

# 誤った使用方法（直接呼び出し）
result = my_instance(arg1, arg2)  # エラー！
```

2. **`@injected`関数の呼び出し結果も`IProxy`オブジェクト**：
```python
@injected
def my_function(dep1, dep2, /, arg1: str, arg2: int) -> Result:
    return Result(dep1, dep2, arg1, arg2)

# my_functionの型: IProxy[Callable[[str, int], Result]]

# 呼び出し結果の型
f: IProxy[Callable[[str, int], Result]] = my_function
y: IProxy[Result] = f("value", 42)  # 呼び出し結果もIProxy
```

2. **`@injected`で定義された関数は非注入引数を渡して呼び出せる**：
```python
@injected
def my_function(dep1, dep2, /, arg1: str, arg2: int) -> Result:
    return Result(dep1, dep2, arg1, arg2)

# my_functionの型: IProxy[Callable[[str, int], Result]]

# 正しい使用方法
result = my_function("value", 42)  # OK
```

4. **クラスに`injected()`を適用する場合**：
```python
class MyClass:
    def __init__(self, dep1, dep2, non_injected_arg: str):
        self.dep1 = dep1
        self.dep2 = dep2
        self.non_injected_arg = non_injected_arg

# new_MyClassの型: IProxy[Callable[[str], MyClass]]
new_MyClass = injected(MyClass)

# 正しい使用方法
# my_instanceの型: IProxy[MyClass]
my_instance = new_MyClass("value")  # OK
```

これらの型の違いを理解することで、`@instance`と`@injected`の使い分けがより明確になります。

### 8.8 よくある間違いと推奨される書き方

pinjectedを使用する際によくある間違いと、その推奨される書き方を以下に示します：

#### 1. `@instance`関数の直接呼び出し

```python
# 間違った書き方
@instance
def my_instance(dep1, dep2) -> MyClass:
    return MyClass(dep1, dep2)

# 間違い: @instance関数を直接呼び出している
result = my_instance(arg1, arg2)  # エラー！

# 推奨される書き方
# @instanceはIProxy[T]を返すため、直接呼び出せない
# 依存関係を設定する場合は__pinjected__.py内の__design__を使用

# __pinjected__.py
from pinjected import design

__design__ = design(
    # 依存関係の設定
    my_dependency=my_instance
)

# レガシーな方法（非推奨）:
# __meta_design__ = design(
#     overrides=design(
#         # 依存関係の設定（test_で始まらない変数）
#         my_dependency=my_instance
#     )
# )
```

#### 2. `@injected`関数の不完全な使用

```python
# 間違った書き方
@injected
def my_function(dep1, dep2, /, arg1: str, arg2: int) -> Result:
    return Result(dep1, dep2, arg1, arg2)

# 間違い: @injected関数を変数に代入するだけで呼び出していない
my_result = my_function  # 不完全

# 推奨される書き方
# @injected関数は呼び出す必要がある
my_result = my_function("value", 42)  # OK
```

#### 3. `/`の位置の間違い

```python
# 間違った書き方
@injected
def my_function(dep1, /, dep2, arg1: str):  # dep2が/の右側にある
    return Result(dep1, dep2, arg1)

# 推奨される書き方
@injected
def my_function(dep1, dep2, /, arg1: str):  # すべての依存が/の左側にある
    return Result(dep1, dep2, arg1)
```

#### 4. テスト用変数の定義方法

テストは`@injected_pytest`デコレータを使用して定義することが推奨されています。

```python
# 推奨される書き方: @injected_pytestを使用したテスト
@injected_pytest()
def test_my_function(my_function):
    return my_function("test_input")

```

# Pinjected 命名規則ベストプラクティス

## 1. @instanceの命名規則

`@instance`デコレータは依存オブジェクトの「提供者」を定義。

### 推奨パターン
- **名詞形式**: `config`, `database`, `logger`
- **形容詞_名詞**: `mysql_connection`, `production_settings`
- **カテゴリ__具体名**: `model__resnet`, `dataset__mnist`

### 避けるべきパターン
- ~~動詞を含む形式~~: `setup_database`, `initialize_config`
- ~~動詞句~~: `get_connection`, `build_model`

### 理由
`@instance`は「何を提供するか」を表現するため名詞形式が適切。動詞だと「何をするか」の誤解を招く。

### 例
```python
# 良い例
@instance
def rabbitmq_connection(host, port, credentials):
    return pika.BlockingConnection(...)

# 良い例
@instance
def topic_exchange(channel, name):
    channel.exchange_declare(...)
    return name

# 悪い例
@instance
def setup_database(host, port, username):  # × 動詞を含む
    return db.connect(...)
```

## 2. @injectedの命名規則

`@injected`デコレータは部分的に依存解決された「関数」を定義。

### 推奨パターン
- **動詞形式**: `send_message`, `process_data`, `validate_user`
- **動詞_目的語**: `create_user`, `update_config`
- **非同期関数(async def)には`a_`接頭辞**: `a_fetch_data`, `a_process_queue`

### 例
```python
# 良い例
@injected
def send_message(channel, /, queue: str, message: str):
    # ...

# 良い例
@injected
def process_image(model, preprocessor, /, image_path: str):
    # ...

# 非同期関数の良い例
@injected
async def a_fetch_data(api_client, /, user_id: str):
    # ...
```

## 3. design()内のキー命名規則

`design()`関数内のキー命名は依存項目の関係性を明確に。

### 推奨パターン
- **スネークケース**: `learning_rate`, `batch_size`
- **カテゴリ接頭辞**: `db_host`, `rabbitmq_port`
- **明確な名前空間**: `service__feature__param`

### 例
```python
config_design = design(
    rabbitmq_host="localhost",
    rabbitmq_port=5672,
    rabbitmq_username="guest",
    
    db_host="localhost",
    db_port=3306,
)
```

## 4. 非同期関数の命名規則

### @instanceデコレータを使用する非同期関数

@instanceデコレータを使用する非同期関数には`a_`接頭辞を付けない。理由：

1. @instanceで設定されたオブジェクトはpinjected(AsyncResolver)が自動的にawaitして実体化するため、ユーザーが自分でawaitする必要がない
2. @instanceは内部でawaitが必要ない限り、async defではなくdefで定義可能
3. @instanceは「何を提供するか」を表現するため、名詞形式の維持が重要

```python
# 良い例 - a_接頭辞なし
@instance
async def rabbitmq_connection(host, port, username, password):
    connection = await aio_pika.connect_robust(...)
    return connection

# 悪い例 - 不要なa_接頭辞
@instance
async def a_rabbitmq_connection(host, port, username, password):  # × a_接頭辞は不要
    # ...
```

### @injectedデコレータを使用する非同期関数

@injectedデコレータを使用する非同期関数には`a_`接頭辞を付ける。

```python
# 良い例 - a_接頭辞あり
@injected
async def a_send_message(rabbitmq_channel, /, routing_key: str, message: str):
    await rabbitmq_channel.send(...)
    return True

# 悪い例 - a_接頭辞なし
@injected
async def fetch_data(api_client, /, user_id: str):  # × a_接頭辞がない
    # ...
```

この命名規則に従うことで関数の役割と処理タイプが明確になり、コードの保守性が向上する。

# Pinjected 型とプロトコルのベストプラクティス

## 1. 型アノテーションの基本原則

Pinjectedでは、適切な型アノテーションを使用することで、コードの安全性と保守性が向上します。特に複数の実装を持つ依存関係では、Protocolを活用した型定義が推奨されます。

### 基本的な型アノテーション

```python
from typing import List, Dict, Optional, Callable

@instance
def database_connection(host: str, port: int) -> Connection:
    return connect_to_db(host, port)

@injected
def fetch_users(db: Connection, /, user_id: Optional[int] = None) -> List[Dict[str, any]]:
    # ...
```

## 2. Protocolを活用した依存関係の型定義

同じインターフェースに対して複数の実装を用意する場合、`Protocol`を活用してインターフェースを定義します。これにより、依存関係の差し替えが型安全に行えます。

### Protocolの定義と活用

```python
from typing import Protocol, runtime_checkable
from PIL import Image

# 画像処理プロトコルの定義
@runtime_checkable
class ImageProcessor(Protocol):
    async def __call__(self, image) -> Image.Image:
        pass

# 実装バリエーション1
@injected
async def a_process_image__v1(preprocessor, /, image) -> Image.Image:
    # 実装1のロジック
    return processed_image

# 実装バリエーション2（追加の依存あり）
@injected
async def a_process_image__v2(preprocessor, enhancer, /, image) -> Image.Image:
    # 実装2のロジック
    return processed_image

# プロトコルを型として使用する関数
@injected
async def a_use_image_processor(
    image_processor: ImageProcessor,  # Protocolを型として使用
    logger,
    /,
    image,
    additional_args: dict
) -> Image.Image:
    logger.info(f"Processing image with args: {additional_args}")
    # image_processorは__call__を実装していることが保証されている
    return await image_processor(image)

# 設計によるバリエーション切り替え
base_design = design(
    a_process_image = a_process_image__v1  # デフォルトはv1を使用
)

advanced_design = base_design + design(
    a_process_image = a_process_image__v2  # v2に切り替え
)
```


# Pinjectedのmainブロックからの実行（非推奨）

Pinjectedはmainブロックから直接使用可能。このパターンは非推奨。

## スクリプトからの実行例

```python
from pinjected import instance, AsyncResolver, design, Design, IProxy
import pandas as pd


@instance
async def dataset(dataset_path) -> pd.DataFrame:
    return pd.read_csv(dataset_path)


if __name__ == "__main__":
    d: Design = design(
        dataset_path="dataset.csv"
    )
    resolver = AsyncResolver(d)
    dataset_proxy: IProxy = dataset
    dataset: pd.DataFrame = resolver.provide(dataset_proxy)
```

## RabbitMQ接続例

```python
from pinjected import instance, injected, design, Design, AsyncResolver, IProxy
import pika

@instance
def rabbitmq_connection(host, port, username, password):
    credentials = pika.PlainCredentials(username, password)
    parameters = pika.ConnectionParameters(
        host=host,
        port=port,
        credentials=credentials
    )
    return pika.BlockingConnection(parameters)

@instance
def rabbitmq_channel(rabbitmq_connection):
    return rabbitmq_connection.channel()

@injected
def send_message(rabbitmq_channel, /, routing_key: str, message: str):
    rabbitmq_channel.basic_publish(
        exchange='',
        routing_key=routing_key,
        body=message.encode()
    )
    return True

if __name__ == "__main__":
    d: Design = design(
        host="localhost",
        port=5672,
        username="guest",
        password="guest"
    )
    
    resolver = AsyncResolver(d)
    
    channel_proxy: IProxy = rabbitmq_channel
    channel = resolver.provide(channel_proxy)
    
    send_message_proxy: IProxy = send_message
    send_func = resolver.provide(send_message_proxy)
    
    result = send_func("hello", "Hello World!")
    print(f"送信結果: {result}")
```

## 非推奨理由

1. CLIを使用する方が設定変更が容易
2. コード量が増加
3. Pinjectedの設計思想に反する

代わりにCLI実行方式を使用:

```bash
python -m pinjected run my_module.my_function --param1=value1 --param2=value2
```
# @instanceと@injectedの本質的な違い

## 抽象化の対象

`@instance`と`@injected`は異なる抽象を表す:

- **@instance**: 「値」を抽象化するIProxy
    - 関数実行結果を表す
    - すべての引数が依存解決済み

- **@injected**: 「関数」を抽象化するIProxy
    - 部分適用された関数を表す
    - `/`左側は依存解決済み、右側はまだ必要

`@instance`関数はDIシステムが呼び出し、ユーザーは直接呼び出さないため、デフォルト引数は不適切:

```python
# 不適切
@instance
def database_client(host="localhost", port=5432, user="default"):  # NG
    return create_db_client(host, port, user)

# 適切
@instance
def database_client(host, port, user):  # デフォルト引数なし
    return create_db_client(host, port, user)

# 設定はdesign()で提供
base_design = design(
    host="localhost", 
    port=5432, 
    user="default"
)
```

## コマンドライン実行の挙動

```python
# @instance例
@instance
def my_instance(dependency1, dependency2):
    return f"{dependency1} + {dependency2}"

# 型: IProxy[str]
# pinjected run → "value1 + value2" が出力

# @injected例
@injected
def my_injected(dependency1, /, arg1):
    return f"{dependency1} + {arg1}"

# 型: IProxy[Callable[[str], str]]
# pinjected run → 関数オブジェクト出力
```

実行結果が異なる理由:
- `@instance`: 値を抽象化→実行結果は値
- `@injected`: 関数を抽象化→実行結果は関数

## IProxyオブジェクトの実行

変数に格納したIProxyやそのメソッド呼び出しもpinjected runの対象になる:

```python
@instance
def trainer(dep1):
    return Trainer()

@instance
def model(dep2):
    return Model()

# これらは全てpinjected run可能
trainer_proxy: IProxy[Trainer] = trainer  # インスタンス参照
run_training: IProxy = trainer_proxy.train(model)  # メソッド呼び出し

# 実行方法
# python -m pinjected run module.trainer  # トレーナーインスタンス出力
# python -m pinjected run module.trainer_proxy  # 同上
# python -m pinjected run module.run_training  # トレーニング実行結果出力
```

これらの理解はPinjectedを効果的に活用する上で重要。

# Pinjected エントリポイント設計のベストプラクティス

## 1. IProxy変数を使用したエントリポイント

```python
# my_module.py
@instance
def trainer(dep1, dep2):
    return Trainer(dep1, dep2)

@instance
def model(dep3):
    return Model(dep3)

@injected
def train_func(trainer,model):
    return trainer.train(model)

# IProxy変数としてエントリポイントを定義
run_train_v1:IProxy = train_func() # calling @injected proxy so we get the result of running trainer.train.
run_train_v2: IProxy = trainer.run(model)
```

既存のIProxyオブジェクトのメソッド呼び出しや操作結果をエントリポイントとして定義する。
エントリポイントには必ず`IProxy`型アノテーションをつける必要がある。`IProxy`型アノテーションがない場合、pinjectedはエントリポイントとして認識しない。

## CLIからの実行

両方のエントリポイントは同様にCLIから実行可能:

```bash
# @instanceを使ったエントリポイントの実行
python -m pinjected run my_module.run_train_v1

# IProxy変数を使ったエントリポイントの実行 
python -m pinjected run my_module.run_train_v2
```

## 注意: @injectedはエントリポイントではない

`@injected`デコレータはエントリポイントの定義には通常使用しない。理由:

```python
@injected
def run_something(dep1, dep2, /, arg1, arg2):
    # 処理内容
    return result
```

このように定義した関数をpinjected runで実行すると、実行結果は値ではなく「関数オブジェクト」になる。これは`@injected`が「関数を抽象化するIProxy」を返すため。

@injectedは主に、依存性を注入した上で追加の引数を受け取るような「部分適用関数」を定義する場合に適している。

## エントリポイントの命名規則

エントリポイントには明確な命名規則を使用するべき:

- 推奨: `run_training`, `run_evaluation`, `run_inference`
- 避けるべき: 具体的動作を表す一般的名前（`train`, `evaluate`, `predict`）

## 9. まとめ

Pinjectedは研究開発コードの問題(大きなcfg依存、多数のif分岐、テスト困難性)の解決策。

主なメリット:

- **設定管理**: design()によるDI定義、CLIオプション、~/.pinjected.pyでローカル設定対応
- **コード構造改善**: @instanceと@injectedによるオブジェクト注入でif分岐削減
- **テスト容易性**: コンポーネント単体実行・検証が簡単
- **宣言的記述**: Injected/IProxyによるDSL的表現

結果として開発速度向上、コード再利用性が高まる。

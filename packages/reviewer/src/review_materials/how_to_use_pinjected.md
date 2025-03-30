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

#### 依存関係のない@injected関数
依存関係がない関数も@injectedを使って表現できます。
以下は、他の何にも依存しないが、argを呼び出しに受け取る必要がある関数をwrapしたIProxyです。
依存関係がない場合、pythonの文法上`/`をつけることができません。従って、`/`をつけずに引数のみ記述します。
```python
from pinjected import injected
# Correct
@injected
def simple_func(arg):
    return arg
# Wrong, Syntax Error
@injected
def simple_func(/,arg):
    return arg
```

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
    trainer=Trainer
)
```

### 2.4 依存性設定ファイル

Pinjectedでは、以下の2つの方法で依存性を設定できます:

#### 2.4.1 推奨: `__pinjected__.py`ファイル内の`__design__`

`__design__`は`__pinjected__.py`ファイル内で定義する特別なグローバル変数です。これはCLIから実行する際のデフォルトのデザインを指定するために使用されます。

```python
# __pinjected__.py
from pinjected import design

__design__ = design(
    # CLIで指定しなかったときに利用されるデザイン
    learning_rate=0.001,
    batch_size=128
)
```

#### 2.4.2 レガシー: `__meta_design__`

`__meta_design__`は、非推奨となっている特別なグローバル変数です。以前はCLIから実行する際のデフォルトのデザインを指定するために使用されていました。

```python
# __init__.py や他のモジュールファイル内 (非推奨)
__meta_design__ = design(
    overrides=mnist_design  # CLIで指定しなかったときに利用されるデザイン
)
```

```python
# 何もoverrideしない場合 (非推奨)
__meta_design__ = design()
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
    api_key = "your_api_key_here",
    cache_dir = "/home/user/.cache/myproject"
)
```

### 4.2 withステートメントによるデザインオーバーライド

`with`ステートメントを用いて、一時的なオーバーライドを行えます。

```python
from pinjected import IProxy, design

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
    epochs=10
)

# 実験バリエーション
experiment1 = base_design + design(
    learning_rate=0.01,
    model=model__simplecnn
)

experiment2 = base_design + design(
    learning_rate=0.0001,
    batch_size=256,
    model=model__resnet
)
```

## 6. 実践的なパターン

### 6.1 依存関係の階層化

複雑なアプリケーションでは、依存関係を階層化して管理すると見通しが良くなります。

```python
# 基本設定
base_design = design(
    cache_dir=Path("~/.cache/myapp").expanduser(),
    debug=False
)

# データ関連
data_design = base_design + design(
    dataset=dataset__mnist,
    batch_size=128,
    num_workers=4
)

# モデル関連
model_design = base_design + design(
    model=model__simplecnn,
    learning_rate=0.001,
    optimizer=optimizer__adam
)

# 完全な設定
full_design = data_design + model_design + design(
    trainer=trainer__default,
    epochs=10
)
```

### 6.2 環境依存の設定分離

開発環境、テスト環境、本番環境など、環境ごとに設定を分離できます。

```python
# 共通設定
common_design = design(
    model=model__simplecnn,
    dataset=dataset__mnist
)

# 開発環境
dev_design = common_design + design(
    debug=True,
    cache_dir=Path("/tmp/dev_cache"),
    batch_size=8  # 小さめのバッチサイズ
)

# 本番環境
prod_design = common_design + design(
    debug=False,
    cache_dir=Path("/var/cache/myapp"),
    batch_size=128  # 大きめのバッチサイズ
)
```

### 6.3 テスト用のモック注入

テスト時には実際のAPIやデータベースの代わりにモックを注入できます。

```python
# 本番用設定
prod_design = design(
    database=real_database_connection,
    api_client=real_api_client
)

# テスト用設定
test_design = design(
    database=mock_database,
    api_client=mock_api_client
)

# テストコード
def test_user_registration():
    with test_design:
        result = register_user(username="test", email="test@example.com")
        assert result.success == True
```

## 7. よくある質問とトラブルシューティング

### 7.1 循環依存の解決

循環依存（AがBに依存し、BがAに依存する）が発生した場合は、以下の方法で解決できます：

1. 依存関係の再設計（推奨）
2. 遅延評価を利用する

```python
# 循環依存の例
@instance
def component_a(component_b):
    return ComponentA(component_b)

@instance
def component_b(component_a):
    return ComponentB(component_a)

# 解決策: 遅延評価
@instance
def component_a():
    # component_bを直接依存せず、必要時に取得
    return ComponentA(lambda: Injected.by_name("component_b").resolve())

@instance
def component_b():
    # component_aを直接依存せず、必要時に取得
    return ComponentB(lambda: Injected.by_name("component_a").resolve())
```

### 7.2 依存解決の失敗

依存解決に失敗する一般的な原因と解決策：

1. **依存名の不一致**: 依存名が正確に一致しているか確認
2. **未定義の依存**: すべての必要な依存が定義されているか確認
3. **型の不一致**: 期待される型と実際の型が一致しているか確認

```python
# 問題: 依存名の不一致
@instance
def model(input_size):  # 'input_size'に依存
    return Model(input_size)

design = design(
    inputSize=128  # 'inputSize'と定義（不一致）
)

# 解決策: 依存名を一致させる
design = design(
    input_size=128  # 'input_size'と定義（一致）
)
```

### 7.3 パフォーマンスの最適化

大規模なアプリケーションでのパフォーマンス最適化のヒント：

1. **インスタンスの再利用**: `@instance`デコレータを使用して、頻繁に使用されるオブジェクトを一度だけ作成
2. **遅延評価**: 必要になるまでオブジェクトを作成しない
3. **スコープの最小化**: 依存関係のスコープを必要な範囲に限定

```python
# 重いリソースは@instanceで一度だけ初期化
@instance
def large_model():
    print("Loading large model...")
    return load_large_model()  # 重い処理

# 使用例
@injected
def predict(large_model, /, input_data):
    # large_modelは一度だけロードされ、再利用される
    return large_model.predict(input_data)
```

## 8. ベストプラクティス

### 8.1 命名規則

一貫性のある命名規則を使用することで、コードの可読性と保守性が向上します：

1. **インスタンス関数**: `object_type__variant`形式（例: `model__resnet`、`dataset__mnist`）
2. **パラメータ**: スネークケース（例: `learning_rate`、`batch_size`）
3. **デザイン変数**: 目的を示す名前（例: `base_design`、`training_design`）

### 8.2 モジュール構造

大規模なプロジェクトでは、以下のようなモジュール構造が推奨されます：

```
myproject/
  __init__.py
  __pinjected__.py  # プロジェクト全体のデフォルトデザイン
  models/
    __init__.py
    __pinjected__.py  # モデル関連のデザイン
    resnet.py
    vgg.py
  datasets/
    __init__.py
    __pinjected__.py  # データセット関連のデザイン
    mnist.py
    cifar.py
  trainers/
    __init__.py
    __pinjected__.py  # トレーナー関連のデザイン
    default_trainer.py
  experiments/
    __init__.py
    experiment1.py
    experiment2.py
```

### 8.3 エラーメッセージの改善

依存解決に失敗した場合のエラーメッセージを改善するために、適切なドキュメンテーションとエラーハンドリングを行いましょう：

```python
@instance
def database_connection(db_url, username, password):
    try:
        return connect_to_db(db_url, username, password)
    except ConnectionError as e:
        # より詳細なエラーメッセージを提供
        raise ConnectionError(f"Failed to connect to database at {db_url}. Please check your credentials and network connection. Original error: {e}")
```

## 9. 高度なトピック

### 9.1 非同期処理との統合

Pinjectedは非同期処理（async/await）と統合できます：

```python
@instance
async def async_database_client(db_url):
    client = await create_async_client(db_url)
    return client

@injected
async def fetch_user(async_database_client, /, user_id: int):
    return await async_database_client.users.find_one({"id": user_id})
```

### 9.2 型ヒントとmypy対応

Pinjectedは型ヒントと互換性があり、mypyによる静的型チェックをサポートしています：

```python
from typing import List, Dict, Any
from pinjected import instance, injected, IProxy

@instance
def get_config() -> Dict[str, Any]:
    return {"key": "value"}

@injected
def process_data(config: Dict[str, Any], /, data: List[int]) -> List[int]:
    # configは注入される
    # dataは呼び出し時に渡される
    return [x * config.get("multiplier", 1) for x in data]

# 使用例
result: IProxy = process_data(data=[1, 2, 3])
```

### 9.3 プラグインシステムの構築

Pinjectedを使用して、拡張可能なプラグインシステムを構築できます：

```python
# プラグインインターフェース
class Plugin:
    def process(self, data):
        raise NotImplementedError

# プラグイン実装
class FilterPlugin(Plugin):
    def process(self, data):
        return [x for x in data if x > 0]

class TransformPlugin(Plugin):
    def process(self, data):
        return [x * 2 for x in data]

# プラグイン登録
@instance
def plugins() -> List[Plugin]:
    return [FilterPlugin(), TransformPlugin()]

# プラグインシステム
@injected
def process_with_plugins(plugins, /, data: List[int]) -> List[int]:
    result = data
    for plugin in plugins:
        result = plugin.process(result)
    return result
```

## 10. まとめ

Pinjectedは、研究開発向けに設計された柔軟で強力な依存性注入ライブラリです。主な利点は以下の通りです：

- **コードの構造化**: 依存関係を明示的に定義し、コードの構造を改善
- **テスト容易性**: モックやスタブを簡単に注入してテスト可能
- **設定の柔軟性**: 実行時に依存関係やパラメータを変更可能
- **再利用性**: コンポーネントを独立させ、再利用性を向上
- **宣言的スタイル**: Pythonの機能を活用した宣言的なプログラミングスタイル

これらの特徴により、Pinjectedは特に研究開発や実験的なプロジェクトにおいて、コードの品質と開発効率を大幅に向上させることができます。

主なメリット:

- **設定管理**: design()によるDI定義、CLIオプション、~/.pinjected.pyでローカル設定対応
- **コード構造改善**: @instanceと@injectedによるオブジェクト注入でif分岐削減
- **テスト容易性**: コンポーネント単体実行・検証が簡単
- **宣言的記述**: Injected/IProxyによるDSL的表現

結果として開発速度向上、コード再利用性が高まる。

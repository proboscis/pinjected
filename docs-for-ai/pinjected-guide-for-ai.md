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

`@injected`デコレータは、関数引数を「注入対象の引数」と「呼び出し時に指定する引数」に分離できます。`/`の左側が依存として注入され、右側が実行時に渡される引数です。

```python
from pinjected import injected

@injected
def generate_text(llm_model, /, prompt: str):
    # llm_modelはDIから注入される
    # promptは実行時に任意の値を渡せる
    return llm_model.generate(prompt)
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

### 2.4 __meta_design__

`__meta_design__`は、Pinjectedが自動的に収集する特別なグローバル変数です。CLIから実行する際のデフォルトのデザインを指定できます。

```python
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

### 7.1 テスト用IProxyオブジェクト

実装関数と同じファイル内にテスト用のIProxyオブジェクトを配置するパターンが一般的です。

```python
@injected
def process_data(dataset, /, filter_condition=None):
    # データ処理ロジック
    return processed_data

# テスト用IProxyオブジェクト
test_process_data: IProxy = process_data(filter_condition="test")
```

このIProxyオブジェクトは以下のコマンドで実行できます：

```bash
python -m pinjected run your_module.test_process_data
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
- グローバル変数を注入するには、`__meta_design__`を使って明示的に注入する必要がある

```python
# 以下のように単にグローバル変数として定義しても注入されない
my_global_var: IProxy = some_function(arg1="value")
test_my_function: IProxy = my_function(arg1="test")

# 正しい方法: __meta_design__を使って明示的に注入する
__meta_design__ = design(
    overrides=design(
        my_global_var=some_function(arg1="value"),
        test_my_function=my_function(arg1="test")
    )
)
```

### 8.5 __meta_design__の正しい使用方法

`__meta_design__`を更新する際は、以下の形式を使用する必要があります：

```python
__meta_design__ = design(
    overrides=design(key1=value1, key2=value2)
)
```

この形式を守らないと、依存解決が正しく行われない場合があります。特に、`overrides`キーを使用せずに直接`__meta_design__ = design(key=value)`とすると、既存の設定が上書きされてしまう可能性があります。

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
# 依存関係を設定する場合は__meta_design__のoverrideを使用
__meta_design__ = design(
    overrides=design(
        # 依存関係の設定（test_で始まらない変数）
        my_dependency=my_instance
    )
)
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

```python
# 注意: test_で始まるテストターゲットはテストフレームワークで収集する対象
# test_で始まる変数をoverrideで設定するのは推奨されない

# 推奨される書き方: テスト用変数を直接定義
test_my_function: IProxy = my_function("test_value", 42)  # @injected関数の場合
```


## 9. まとめ

Pinjectedは、研究開発現場の実験コードが抱える課題（巨大なcfg依存や膨大なif分岐、部分的テストの難しさなど）に対する効果的な解決策です。

主なメリット:

- **設定管理の柔軟性**: design()による依存定義とCLIオプション、~/.pinjected.pyによるローカル設定上書き
- **if分岐の削減と可読性向上**: @instanceや@injectedを使った明示的なオブジェクト注入
- **部分テスト・デバッグの容易化**: 特定コンポーネントの単独実行・確認
- **高度なDSL的表現**: Injected/IProxyを用いた宣言的かつ直感的な記述

これらの特徴により、研究開発の反復速度が向上し、拡張や再利用も容易になります。
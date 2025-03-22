# 1. はじめに

## 1.1 研究開発で感じる課題

こんにちは、CyberAgent AILabで研究開発をしている増井です。  
普段、画像生成や画像認識などの機械学習研究を行っています。
研究でPythonによる実験コードを書いていると色々と課題に直面しますが、
今回はその解決のために開発したDependency Injection(DI)ライブラリ、([Pinjected](https://github.com/proboscis/pinjected))を紹介させていただきたいと思います。

研究開発コードで直面する課題としては、例えば以下のものがあると思います。

- **実験設定管理が大変**：  
  学習率、バッチサイズ、モデルアーキテクチャ、データパスなど、様々なハイパーパラメータを管理しなければなりません。研究が進むにつれ、設定項目は増え、実験条件を少しずつ変えながら試すことは当たり前。となると、`config.yaml`や`args.cfg`などの設定ファイルが肥大化し、使われているパラメータがどこで参照されているか一目で分からず混乱します。

- **コードの再利用や拡張性が低い**：  
  研究段階のコードは、一度書いたモジュールや関数を別の実験にも使い回したくなります。しかし、ほとんどのコードが`cfg`オブジェクトやグローバルな引数に依存してしまうと、ひとつの変更が全体のコードに波及し、柔軟な再利用が難しくなります。

- **単体テストやデバッグの困難さ**：  
  ちょっとdatasetの中身を見たい、特定のモデル層の出力をプリントしたい、といった小さな確認をするのに、全体の実行フローを回さなければならない状況があります。これでは手軽なチェックがやりにくく、開発効率が下がります。

- **分岐処理が増える一方**：  
  「ResNetにするか、VGGにするか」「optimizerはAdamかSGDか」「DatasetはMNISTかCIFAR10か」…設定項目が増えるほどif分岐がコード中に散在します。やがて分岐の嵐で、実行時にどの条件が使われているかすぐに判断できない状態になります。

## 1.2 Dependency Injection（DI）の必要性

上記の問題に対処するため、`Dependency Injection(DI)`という設計手法が有効な解決策として注目できます。  
DIの基本的な考え方は、「必要なオブジェクト（依存するオブジェクト）はコンストラクタや引数を通して外部から注入する」というものです。これにより、コードは特定の設定やグローバル変数にべったり依存せず、柔軟に再構成可能になります。

DIをうまく用いれば、

- `cfg`オブジェクトへの全体依存を解消し、必要なパラメータだけを明示的に注入できる
- 大量のif分岐を排除し、依存関係を切り替える際には外部の設定層を差し替えるだけで済む
- 単体テストや部分的なデバッグが容易になり、コードの品質や開発スピードが向上する

など、多くのメリットが得られます。

## 1.3 pinjectedの開発背景と狙い

Pythonにはすでに`pinject`や`python-dependency-injector`などのDIツールが存在します。しかし、研究開発向けに使ってみると、以下のような課題を感じることがあります。

- DIコンテナの設定やoverrideがやや冗長で、複雑なコードになりがち
- CLIからのパラメータ上書きや複数エントリーポイント管理が標準で想定されていない
- 研究開発で頻繁に行う「ちょっとだけパラメータを変えて実行」「特定のモジュールだけ実行してチェック」といった軽い試行が難しい

そこで、**pinjected**という新しいDIライブラリを提案します。

pinjectedは、

- `@instance`や`@injected`といったPythonicなデコレータによる簡易的な依存定義
- `design()`関数でkey-valueスタイルの直感的な依存合成
- CLIからの柔軟なパラメータ上書きや`Injected`オブジェクト直接実行
- ~/.pinjected.pyなど外部ファイルを使ったユーザーローカル設定やIDEとの統合

などを可能とします。

これにより、研究開発で求められる「素早い試行」「簡易な設定変更」「単体デバッグ」「複数エントリーポイントの容易な管理」といったニーズに応え、開発QOLを大幅に向上させます。

この記事では、pinjectedを用いて機械学習研究コードをどのように管理・実行・拡張していけるかを紹介します。最初は従来手法と比較しながらpinjectedの基本機能を説明し、続いて高度な機能やユニークなDSL的記法（`Injected`/`IProxy`）を通じて、柔軟かつ強力な実験管理手法を紹介したいと思います。


# 2. 従来のアプローチと課題

## 2.1 OmegaConfやHydraによる設定管理

実験コード管理で広く用いられているツールとして、`OmegaConf`や`Hydra`があります。  
これらを用いると、パラメータはYAMLファイルなどで定義でき、CLIから`python train.py learning_rate=0.01 batch_size=64`といった形で簡易的な上書きも可能になります。また、構成ファイルを分割・合成できるため、実験条件を素早く切り替えることも容易です。

一見すると、これらのツールは「実験設定管理が大変」という課題をかなり解消してくれます。しかし、いくつかの根本的な問題が残ります。

- **cfgオブジェクトへの全体依存**：  
  たとえば`train.py`の中で`cfg`オブジェクトがグローバルに渡され、モデル生成からデータセット生成、ロス関数、ロガー、あらゆる要素を`cfg`経由で初期化する状況が発生します。  
  するとコード上は`cfg.model.type`や`cfg.dataset.batch_size`などといったアクセスが至る所に散在し、必要なパラメータがどこから来るのか、実際に使われているのかを追うのが難しくなります。

- **分岐処理の氾濫**：  
  `cfg.model.type == "ResNet"`ならこのクラスを生成、それ以外ならあのクラス…といったif/elseの羅列が設定値に応じて増えていきます。  
  実験が複雑化すると「設定ファイルで指定された無数のパラメータ」によって条件分岐がネストし、最終的にどのブランチが有効なのか把握するのが困難です。

- **単体テストや部分的デバッグの難しさ**：  
  cfgを使う設計では、部分的に特定のモジュール（例: データセットのみ、モデルのみ）を簡単に初期化してテストすることがやや面倒です。基本的に`train.py`全体を動かして`cfg`をロードし、そこから目的の機能を取り出す必要があります。


まとめると、OmegaConfやHydraは設定管理を改善しますが、依然として「cfgオブジェクトへの全依存」「膨れ上がるif分岐」「テストや部分実行のしにくさ」といった課題が残ります。

## 2.2 cfgオブジェクトへの全体依存とif分岐地獄

cfgオブジェクトは、実験設定を一括で格納する便利な仕組みですが、その便利さが裏返しとなり、コード全体がひとつの巨大な設定オブジェクトに依存してしまいます。

「モデルの学習率はcfg.optimizer.lrからとってくる」「データセットの種類はcfg.dataset.typeで判定する」といった使い方は、最初はシンプルでも研究が進むにつれ管理しきれないほど複雑化します。また、if分岐に頼った実装は読みづらく、後から新規モデルや新機能を追加するたびに分岐が増えていきます。

結果として、「この実験設定はどの処理フローをたどるのか？」が実行前には読んでも分かりにくくなり、コードに手を加えるたびに全体への影響を心配しなければならなくなります。

## 2.3 God class問題と拡張性の限界

研究コードではしばしば`Experiment`クラスのような「実験用クラス」を作り、その中に学習、評価、前処理、ログなどの機能を詰め込んでしまうことがあります。これがいわゆる`God class`問題です。

`God class`は以下のような問題を引き起こします。

- クラスが巨大化し、どのメソッドが何に依存しているのか把握しにくい
- 必要ない機能を試す際にも全体の初期化が必要になり、動作確認に手間がかかる
- 継承で機能追加を行うと、継承チェーンが深くなり、最終的にどこで何が行われているのか分からなくなる

このような構造は、再利用や新機能追加時にコード崩壊を招きやすく、研究ペースを落としてしまいます。

## 2.4 テスト・デバッグの難しさ

研究開発では、しばしば「データセットの先頭10サンプルだけ見たい」「特定のモデルレイヤー出力を確認したい」といった軽量なテストやデバッグが必要です。ところが、全体依存構造では「わざわざtrain.pyをフル稼働してcfgをロードしてモデルを初期化し、やっと目的のレイヤーにアクセス」など、必要以上に大掛かりなセットアップが求められます。

この状態は、素早い反復や試行を必要とする研究開発には不向きです

これらの課題を一言でまとめると、 **「全体を覆う巨大な設定・分岐構造やGod classから抜け出したい」**、 **「部分的な再利用やテストを容易にしたい」**というニーズがある、ということになります。


# 3. pinjectedの基本機能

## 3.1 pinjectedとは？

前章で述べた通り、研究開発での実験管理コードは、設定（cfg）オブジェクトへの全依存や複雑なif分岐、God class化による拡張・再利用難易度の上昇といった問題を抱えがちです。  
Dependency Injection (DI) は、こうした構造問題を解消する強力な設計原則であり、既に`pinject`や`python-dependency-injector`などのPythonツールが存在します。

しかし、研究開発で要求される「素早い試行・設定変更」「単体パーツだけの軽量実行」「複数エントリーポイントの容易な切り替え」を実現するには、従来のDIツールには不足している点がありました。

**pinjected**は、これらの課題を踏まえて開発したDIライブラリです。  
以下のような特徴を持ちます：

- **直感的な依存定義**：  
  `@instance`や`@injected`といったデコレーションを使い、Pythonicな形式で依存オブジェクトを定義できます。  
  従来のDIツールでありがちな「コンテナクラス」や「複雑なoverrideコード」は最小限に抑えられます。

- **key-valueスタイルの依存合成**：  
  `design()`関数を使えば、`model=model__SimpleCNN`や`optimizer=optimizer__adam`のように、単純なkey-value割り当てで依存オブジェクトを切り替えられます。  
  このシンプルさにより、if分岐に頼らず「この実験はResNetモデルで試してみよう」といった変更が1行で可能になります。

- **CLIからの柔軟なパラメータ上書き**：  
  `python -m pinjected run your_module.run_train --model='{your_module.model__ResNet}' --learning_rate=0.01`  
  のように、実行時にパラメータや依存対象をCLIオプションで上書きできます。  
  これにより、コードに手を加えなくても新しい設定やパラメータを即試せます。

- **`Injected`オブジェクト直接実行と複数エントリーポイントの容易な管理**：  
  `run_train`のような個別の`Injected`変数や関数を直接指定して実行できるため、複数のエントリーポイントをファイル内で管理しやすくなります。  
  `run_eval`や`run_debug_dataset`といった別タスクへの切り替えもシンプルです。

- **IDE統合・~/.pinjected.pyサポート**：  
  開発環境（IDE）でワンクリック実行したり、ユーザーローカル設定ファイル（~/.pinjected.py）でAPIキーや共通パラメータを注入したりできるため、研究者個々人の開発フローに適合しやすいです。


pinjectedは、これらの機能を通じて、研究開発特有のニーズ（素早い実験条件切り替え、軽量デバッグ、部分実行、再利用性向上）に応えます。

## 3.2 @instanceとdesignによる基本的な依存関係管理

ここでは、MNISTデータセットを使った簡単な実験例を考えます。  
まだトレーニングループを詳細に書く必要はなく、まずは「モデル」「データセット」「学習率」などをpinjectedでどう定義し、組み合わせるかを見てみましょう。

### シンプルなサンプルコード例

以下は、1ファイルにまとめた非常に簡略化した例です。（実際に実行するには、任意の`my_cnn_model.py`や`my_mnist_dataset.py`など実装が必要ですが、ここではイメージ優先です）
```python
# example.py
from dataclasses import dataclass
from pinjected import instance, design

# 仮のモデル/データセットクラス
class SimpleCNN:
    def __init__(self, input_size=784, hidden_units=128):
        self.input_size = input_size
        self.hidden_units = hidden_units

    def forward(self, x):
        # ダミーのforward処理
        pass

class AnotherModel:
    def __init__(self, layers=5):
        self.layers = layers

    def forward(self, x):
        pass

class MNISTDataset:
    def __init__(self, batch_size=128):
        self.batch_size = batch_size

    def __iter__(self):
        # ミニバッチを返すダミー実装
        yield from range(10)

class CIFAR10Dataset:
    def __init__(self, batch_size=128, image_size=32):
        self.batch_size = batch_size
        self.image_size = image_size

    def __iter__(self):
        yield from range(10)

# @instanceデコレータで依存対象を定義
@instance
def model__simplecnn():
    return SimpleCNN(input_size=784, hidden_units=128)

@instance
def model__another():
    return AnotherModel(layers=5)

@instance
def dataset__mnist(batch_size):
    return MNISTDataset(batch_size=batch_size)

@instance
def dataset__cifar10(batch_size, image_size):
    return CIFAR10Dataset(batch_size=batch_size, image_size=image_size)

@dataclass
class Trainer:
    model: object
    dataset: object
    learning_rate: float

    def train(self):
        print(f"Training {self.model.__class__.__name__} on {self.dataset.__class__.__name__} "
              f"with lr={self.learning_rate}")
        for batch in self.dataset:
            # ダミートレーニングループ
            pass

# 基本設計: ここでパラメータや依存の基本値を定義
base_design = design(
    learning_rate=0.001,
    batch_size=128,
    image_size=32  # CIFAR10用
)

# シンプルな構成: SimpleCNN + MNIST
mnist_design = base_design + design(
    model=model__simplecnn,
    dataset=dataset__mnist,
    trainer=Trainer
)

# 別の構成: AnotherModel + CIFAR10
cifar_design = base_design + design(
    model=model__another,
    dataset=dataset__cifar10,
    trainer=Trainer
)

# 実行用エントリーポイント
@instance
def run_train(trainer: Trainer):
    trainer.train()

# __pinjected__.py
from pinjected import design

__design__ = design(
    mnist_design #CLIで指定しなかったときに利用されるデザイン
)

# 以下のレガシーな方法は非推奨です
# __meta_design__ = design(
#     overrides=mnist_design #CLIで指定しなかったときに利用されるデザイン
# )
```

### コードのポイント

1. `@instance`デコレータ  
   `@instance`は、その関数が依存解決における一つの「オブジェクト提供者（プロバイダ）」であることを宣言します。  
   例えば`model__simplecnn`は`SimpleCNN`インスタンスを返す@instanceデコレータ付き関数となります。

2. `design()`関数  
   `design()`は`key=value`形式で依存オブジェクトやパラメータをまとめる「設計図」を作ります。  
   `mnist_design`では`model`キーに`model__simplecnn`を割り当て、`dataset`キーに`dataset__mnist`を割り当てています。これにより、`model`と`dataset`は`SimpleCNN`と`MNISTDataset`で構成される依存構造になります。

3. パラメータの合成  
   `base_design`で`learning_rate`や`batch_size`などの基本パラメータを定義し、それを`+`演算子で他のdesignに合成できます。  
   これで`mnist_design`や`cifar_design`のような特定実験用設定を簡潔に作り出せます。

4. 実行用エントリーポイント（`run_train`）  
   `run_train`は`trainer: Trainer`と書くことで、`trainer`キーから注入される`Trainer`インスタンスを自動で受け取ります。  
   `@instance`をつけているので、`python -m pinjected run example.run_train` のように指定すれば、自動的に`trainer`が解決され`trainer.train()`が実行されます。


### 実行例

`mnist_design`を使って実行する場合は、

```bash
python -m pinjected run example.run_train --overrides={example.mnist_design}
```

とすることで、`mnist_design`に定義された`model`や`dataset`、`learning_rate`が用いられます。  
これにより`SimpleCNN` + `MNISTDataset`が使用され、結果として`"Training SimpleCNN on MNISTDataset with lr=0.001"`が表示されます。

別の実験として`cifar_design`に切り替えると、
```bash
python -m pinjected run example.run_train --overrides={example.cifar_design}

```


`AnotherModel` + `CIFAR10Dataset`の組み合わせでトレーニングが実行され、  
`"Training AnotherModel on CIFAR10Dataset with lr=0.001"`が出力されます。

### CLIオーバーライドによる即席パラメータ変更

`--batch_size=64`のようにCLIで指定すれば、`design()`による設定をさらに上書き可能です。
これで`MNISTDataset`は`batch_size=64`で初期化されます。  
コード変更なしで実験条件を変えられる点がpinjectedの強みです。

## 3.3 CLIからの実行とパラメータ上書き

前節では単一ファイルでの基本的な利用例を示しましたが、pinjectedの大きな強みのひとつは、**CLI経由での柔軟なパラメータ上書き**と**複数エントリーポイント管理**です。  
これにより、コードを書き換えることなく、さまざまな実験条件やタスクを即座に試すことができます。

### CLI実行の基本

pinjectedは、`python -m pinjected run <path.to.target>`という形式で実行することを基本とします。  
`<path.to.target>`には、先ほど例に挙げた`run_train`のような`Injected`オブジェクトや@instanceデコレートされた関数変数を指定可能です。

たとえば、`example.py`で定義した`run_train`を実行するには、以下のようにします。
```python
`python -m pinjected run example.run_train`
```

デフォルトでは`__pinjected__.py`ファイル内の`__design__`や`default_design`が読み込まれ、それらが組み合わされた最終的なDesignから`run_train`の依存関係が解決されます。レガシーな`__meta_design__`も現在はサポートされていますが、非推奨となっています。  
前節の例では、`trainer`が自動的に注入され、`trainer.train()`が実行されます。

### パラメータ上書き（--オプション）

`--`オプションを用いると、個別のパラメータや依存項目を指定して`design`を上書きできます。

```bash
python -m pinjected run example.run_train --batch_size=64 --learning_rate=0.0001

```

これで`batch_size`が64、`learning_rate`が0.0001に変更され、`Trainer`が構築されることになります。  
元々`design()`内で`batch_size=128`や`learning_rate=0.001`と定義していても、CLI指定で簡易的にオーバーライドできます。

### 依存オブジェクトの差し替え

モデルやデータセットといった「実行時に使うオブジェクト」もCLIで変更可能です。  
`--model='{example.model__another}'`のように、`{}`で囲んだパスを指定することで、Pinjectedはそのパス先で定義された@instanceデコレート関数（プロバイダ）を注入対象として解決します。

```bash
python -m pinjected run example.run_train --model='{example.model__another}' --dataset='{example.dataset__cifar10}'
```

こうすることで、元々`model`キーに割り当てていた実装を`model__another`へ差し替え、`dataset`キーを`dataset__cifar10`へ切り替えます。  
これによって、元のコードを一切変更せず、新たな組み合わせで実験が走ります。

### 複数エントリーポイント管理

pinjectedでは、`run_train`に限らず、ファイル内に好きなだけ@instanceデコレータでエントリーポイントとなる`Injected`オブジェクトを定義できます。

たとえば、`example.py`に以下のようなエントリーポイントを追加したとします。

```python
@instance
def run_eval(trainer: Trainer):
    print("Running evaluation...")
    # 評価用の処理をここに書く

```

この場合、

```bash
python -m pinjected run example.run_eval

```

で`run_eval`が実行されます。  
`run_train`と`run_eval`を切り替えるには`run`コマンドの後ろに指定するターゲットを変えるだけでOKです。  
これにより、`__main__`一箇所で全機能を分岐させる必要がなく、それぞれのタスクに応じたエントリーポイントを個別に定義し、気軽に実行できます。

### 複雑なDesign構成・.pinjected.pyの活用

後の章で詳しく説明しますが、pinjectedは`~/.pinjected.py`ファイルや`__pinjected__.py`ファイル内の`__design__`変数を使って、プロジェクト全体・ユーザーローカルなデフォルトDesignを構成できます。

- プロジェクト共通の基本設定を`__pinjected__.py`ファイル内の`__design__`変数にまとめる
- ユーザーごとに異なるAPIキーやパス設定は`~/.pinjected.py`で管理する
- CLIで一時的なオーバーライドを行うことで、その場で実験条件変更

こうした組み合わせにより、複雑な環境や設定条件下でも、最小限のコード修正で多彩な実行条件を試せるようになります。


## 3.4 シンプルな例: OmegaConfベースの実験コードからpinjectedへの置き換え

前節までで、pinjectedにおける依存関係管理やCLI上書きの基本を解説しました。  
ここでは、よくあるOmegaConfベースのコードを例に取り、pinjectedでの記述方法を比較してみましょう。

### 従来のOmegaConfベース実装(例)

以下は、OmegaConfで`config.yaml`を読み込み、モデルやデータセット、オプティマイザを初期化する典型的な`train.py`例です（あくまでイメージ用の擬似コード）。

```python
# train.py (OmegaConf版)
import sys
from omegaconf import OmegaConf

cfg = OmegaConf.load("config.yaml")

from mylib.models import SimpleCNN, ResNet
from mylib.optim import Adam, SGD
from mylib.dataset import MNISTDataset, CIFAR10Dataset
from mylib.losses import MSELoss, CrossEntropyLoss

def get_model(cfg):
    if cfg.model.type == "SimpleCNN":
        return SimpleCNN(cfg.model.in_channels, cfg.model.hidden_units)
    elif cfg.model.type == "ResNet":
        return ResNet(cfg.model.layers)
    else:
        raise ValueError("Unknown model")

def get_optimizer(cfg, model):
    if cfg.optimizer.type == "Adam":
        return Adam(lr=cfg.optimizer.lr, params=model.get_parameters())
    elif cfg.optimizer.type == "SGD":
        return SGD(lr=cfg.optimizer.lr, params=model.get_parameters())
    else:
        raise ValueError("Unknown optimizer")

def get_dataset(cfg):
    if cfg.dataset.type == "MNIST":
        return MNISTDataset(cfg.dataset.batch_size)
    elif cfg.dataset.type == "CIFAR10":
        return CIFAR10Dataset(cfg.dataset.batch_size, cfg.dataset.image_size)
    else:
        raise ValueError("Unknown dataset")

def get_loss(cfg):
    if cfg.loss == "MSE":
        return MSELoss()
    elif cfg.loss == "CrossEntropy":
        return CrossEntropyLoss()
    else:
        raise ValueError("Unknown loss")

# Trainer例
class Trainer:
    def __init__(self, model, optimizer, loss_fn, dataset, epochs=1):
        self.model = model
        self.optimizer = optimizer
        self.loss_fn = loss_fn
        self.dataset = dataset
        self.epochs = epochs

    def train(self):
        print(f"Training {self.model.__class__.__name__} on {self.dataset.__class__.__name__}")
        # ... 実行 ...

if __name__ == "__main__":
    model = get_model(cfg)
    optimizer = get_optimizer(cfg, model)
    dataset = get_dataset(cfg)
    loss_fn = get_loss(cfg)
    trainer = Trainer(model, optimizer, loss_fn, dataset, epochs=cfg.trainer.epochs)
    trainer.train()

```

このコードの問題点は前章で述べた通りです:

- `cfg`への全依存
- 大量のif分岐による実装切り替え
- 単体テストや部品確認が難しい

### pinjectedによる書き換え例

pinjectedでは、依存関係を`@instance`で定義し、`design()`で組み合わせることでif分岐を取り除きます。
```python
# train_pinjected.py
from dataclasses import dataclass
from pinjected import instance, design

from mylib.models import SimpleCNN, ResNet
from mylib.optim import Adam, SGD
from mylib.dataset import MNISTDataset, CIFAR10Dataset
from mylib.losses import MSELoss, CrossEntropyLoss
# @instanceの対象となる関数名は任意です
# モデルプロバイダ
@instance
def model__simplecnn(in_channels, hidden_units):
    return SimpleCNN(in_channels, hidden_units)

@instance
def model__resnet(layers):
    return ResNet(layers)

# オプティマイザ
@instance
def optimizer__adam(learning_rate, model):
    return Adam(lr=learning_rate, params=model.get_parameters())

@instance
def optimizer__sgd(learning_rate, model):
    return SGD(lr=learning_rate, params=model.get_parameters())

# データセット
@instance
def dataset__mnist(batch_size):
    return MNISTDataset(batch_size)

@instance
def dataset__cifar10(batch_size, image_size):
    return CIFAR10Dataset(batch_size, image_size)

# ロス
@instance
def loss__mse():
    return MSELoss()

@instance
def loss__crossentropy():
    return CrossEntropyLoss()

@dataclass
class Trainer:
    model: 'Model'
    optimizer: 'Optimizer'
    loss_fn: 'Loss'
    dataset: 'Dataset'
    epochs: int

    def train(self):
        print(f"Training {self.model.__class__.__name__} on {self.dataset.__class__.__name__} "
              f"for {self.epochs} epochs.")
        # ... トレーニング実行 ...

# baseデザイン（基本パラメータ）
base_design = design(
    in_channels=1,
    hidden_units=128,
    layers=5,
    learning_rate=0.001,
    batch_size=128,
    image_size=32,
    epochs=10
)

# MNIST + SimpleCNN 設定
mnist_design = base_design + design(
    model=model__simplecnn,
    dataset=dataset__mnist,
    loss_fn=loss__mse,
    optimizer=optimizer__adam,
    trainer=Trainer
)

# CIFAR10 + ResNet設定
cifar_design = base_design + design(
    model=model__resnet,
    dataset=dataset__cifar10,
    loss_fn=loss__crossentropy,
    optimizer=optimizer__sgd,
    trainer=Trainer
)

@instance
def run_train(trainer: Trainer):
    trainer.train()

# __pinjected__.py
from pinjected import design

__design__ = design()

# 以下のレガシーな方法は非推奨です
# __meta_design__ = design()

```

### この書き換えで得られるメリット

- **if分岐の消滅**：  
  `cfg.dataset.type`などをもとにifで分岐する代わりに、`design()`で`dataset`キーに`dataset__mnist`や`dataset__cifar10`を割り当てるだけで切り替えできます。

- **柔軟な設定上書き**：  
  `python -m pinjected run train_pinjected.run_train --overrides={train_pinjected.mnist_design}`  
  のように実行すればMNIST用の設定でトレーニングが始まります。  
  CIFAR10で試したければ  
  `--overrides={train_pinjected.cifar_design}`  
  とするだけでOK。さらに、`--epochs=20`のようなCLIオプションで細かなパラメータを変更できます。

- **単体テストや部品デバッグが容易**：  
  `python -m pinjected run train_pinjected.dataset__mnist`  
  と実行すれば、`MNISTDataset`インスタンスを単独で取得し、簡易にデバッグできます（printする関数を別途用意するなど）。  
  これでデータの確認やモデル構造確認が容易になります。

### まとめ

OmegaConfなどで構築された`cfg`ベースのコードをpinjectedに置き換えることで、以下の点が改善されます。

- 全体的な再利用性・拡張性の向上
- if分岐無しでの実行条件切り替え
- パラメータ変更や依存差し替えがコードレスで可能
- 部分的な実行・デバッグが容易

# 4. 他のDIツールとの比較

## 4.1 python-dependency-injectorとの比較

Pythonには既存のDIフレームワークとして`python-dependency-injector`や`injector`などが存在します。  
これらは、DIコンテナやBindingSpec（特定の依存関係の定義クラス）を用いてオブジェクトグラフを定義します。  
`python-dependency-injector`の場合、以下のようなコードが典型的な例です。

```python
# containers.py (python-dependency-injector例)
from dependency_injector import containers, providers
from mylib.models import SimpleCNN, ResNet
from mylib.dataset import MNISTDataset, CIFAR10Dataset
from mylib.optim import Adam, SGD
from mylib.losses import MSELoss, CrossEntropyLoss

class Container(containers.DeclarativeContainer):
    config = providers.Configuration()

    model = providers.Factory(
        SimpleCNN,
        in_channels=config.model.in_channels,
        hidden_units=config.model.hidden_units
    )

    optimizer = providers.Factory(
        Adam,
        lr=config.optimizer.lr,
        params=model.provided.get_parameters
    )

    dataset = providers.Factory(
        MNISTDataset,
        batch_size=config.dataset.batch_size
    )

    loss_fn = providers.Factory(
        MSELoss
    )

    trainer = providers.Factory(
        lambda model, optimizer, loss_fn, dataset, epochs:
        Trainer(model, optimizer, loss_fn, dataset, epochs),
        model=model,
        optimizer=optimizer,
        loss_fn=loss_fn,
        dataset=dataset,
        epochs=config.trainer.epochs
    )

```

`python-dependency-injector`では、コンテナクラスを使って依存関係をプロバイダとして記述し、`config`を経由してパラメータを注入します。

一方で、依存差し替えや設定変更を行いたい場合、`config`の値を書き換えたり`model.override(...)`のようなメソッドを呼ぶ必要があります。また、CLIから直接パラメータを上書きする仕組みは標準で用意されていません。

これに対してpinjectedは、`design()`を用いたkey-valueスタイルでの直感的な依存合成を採用しており、CLIを介したオーバーライドを標準サポートしています。  
モデル差し替えやハイパーパラメータ変更はコード編集なしで実行時に可能で、`--model='{your_module.model__resnet}'`や`--learning_rate=0.01`といったシンプルなCLIオプションで実現できます。

## 4.2 設定切り替え・overrideのしやすさ

`python-dependency-injector`で実行時に設定を変えるには、

- configをロードし直す
- 環境変数や別途コードでoverrideを呼ぶ  
  といった手間が必要になります。

pinjectedでは、`design`による基本設定の上にさらに`+`演算子で別デザインを合成したり、CLIオプションでパラメータを直接overrideすることで、即座に実行条件を変更できます。  
これにより、研究で試行錯誤を頻繁に行う場面での柔軟性が高まります。

## 4.3 複数エントリーポイント・テスト容易性の向上

`python-dependency-injector`でも複数のファクトリ関数やプロバイダを用意すれば複数エントリーポイントを擬似的に管理できますが、実行時に特定のターゲット（オブジェクト）だけを簡易に呼び出す仕組みは標準では用意されていません。

pinjectedでは`@instance`や`@injected`でデコレートしたオブジェクトや関数をターゲットとして直接`python -m pinjected run your_module.your_target`で呼び出せます。  
これにより、トレーニング用、評価用、デバッグ用など用途別のエントリーポイントをファイル内に定義して簡単に切り替え可能です。  
また、`dataset__mnist`や`model__resnet`など特定コンポーネントだけを呼び出してデバッグすることも容易で、テストや部分実行が直感的になります。


# 5. pinjected特有の高度な機能



前章までで、pinjectedによる基本的な依存管理と既存ツールとの比較について理解できたと思います。

この章では、pinjectedがさらに提供する高度な機能を紹介します。

これらの機能は、より柔軟な実行時引数の扱いや、一時的な設定のオーバーライド、ユーザーローカルな秘密情報や環境変数的な設定を扱う際に特に有用です。



## 5.1 @injectedデコレータと実行時引数の分離



@instanceデコレータは、引数すべてを依存パラメータとして扱い、DesignやCLIオーバーライドで全注入を行います。一方、@injectedデコレータは、関数引数を/を用いて「注入対象の引数」と「呼び出し時に指定する引数」に分離できます。



たとえば、以下の例を考えてみましょう。

```python
from pinjected import injected, `IProxy`

@injected
def generate_text(llm_model, /, prompt: str):
    # llm_modelはDIから注入される
    # promptは実行時に任意の値を渡せる
    return llm_model.generate(prompt)

test_generate_text:IProxy = generate_text('hello')
```

ここでllm_modelはDesignで注入され、promptは呼び出し時に指定します。

こうすることで、モデル（llm_model）の初期化は一度きりにしつつ、promptだけを変えて何度も実行できるようになります。



この@injectedの仕組みにより、**「固定的なリソースはDIで確保し、実行時に変わる引数は呼び出し時に直接指定」**するユースケースが簡単に実現可能です。



## 5.2 ~/.pinjected.pyによるユーザーローカル設定管理



研究開発では、APIキーやローカルパスなど、ユーザーごとに異なる機密情報やパス設定を安全かつ簡便に管理したいことがあります。

pinjectedは~/.pinjected.pyというファイルを通じて、ユーザーローカルなDesignを定義・注入できます。

```python
# ~/.pinjected.py
from pinjected import instances

default_design = instances(
    openai_api_key = "sk-xxxxxx_your_secret_key_here",
    cache_dir = "/home/user/.cache/myproject"
)
```

上記のように書いておくと、プロジェクト内でopenai_api_keyやcache_dirが注入され、コード変更なしでユーザーごとの設定を共有できます。

他人に見せたくない情報はこのローカルファイルに置き、Git管理外にすることで安全に運用可能です。



## 5.3 withステートメントによるDesignオーバーライド



pinjectedはdesign()を+演算子で合成するだけでなく、withステートメントを用いて一時的なオーバーライドを行うこともできます。

これは一時的に依存関係を差し替えて実行する際に有用です。

```python
from pinjected import providers, instances, `IProxy`, design

# __pinjected__.py
from pinjected import design

__design__ = design( # python -m pinjected runが自動的に収集する変数
    batch_size=128,
    learning_rate=0.001
)

# 以下のレガシーな方法は非推奨です
# __meta_design__ = design( # python -m pinjected runが自動的に収集する変数
#     overrides = design( # デフォルトで利用されるデザインの指定
#         batch_size=128,
#         learning_rate=0.001
#     )
# )

train_with_bs_128:IProxy = train() # __meta_design__.overridesが自動で適用される

with instances(
        batch_size=64  # 一時的にbatch_sizeを64へ
):
    # このwithブロック内ではbatch_sizeは64として解決される
    # テストやデバッグ用の`IProxy`/`Injected`宣言
    train_with_bs_64:`IProxy` = train()
    pass



# withブロック外のbatch_sizeは元の128に戻る
```

これにより、実験条件を一時的に差し替えたテストを手軽に行えます。

withステートメントは、design()で組み上げた依存関係を一時的に変更できるので、ちょっとした試行に非常に便利です。

## 5.4 `Injected`/`IProxy`はここまでの機能をさらに進化させる



@instanceや@injected、design()、withステートメント、~/.pinjected.pyによる拡張で、既にかなり柔軟なDI環境が整いつつあります。しかし、pinjectedはさらに進んで、依存関係を関数的に合成したり、複雑な計算ロジックを依存グラフ上で表現する`Injected`や`IProxy`といった機能を提供します。



`Injected`/`IProxy`を用いると、単なる依存注入を超えて、「依存する値同士を合成し、新たな値を計算して差し込む」「pathlibライクにパスを操作する」など、DSL（ドメイン固有言語）的な表現が可能になります。



これらの詳細は次章（7章）で取り上げますが、ひとまずpinjectedの高度な機能として以下を把握しておけばOKです。

• @injected: DI管理下で固定的に初期化されるリソースと、実行時に可変な引数を明確に分離できる

• ~/.pinjected.py: ユーザーローカルな設定や秘密情報を簡潔に注入可能

• withステートメント: 一時的なDesignオーバーライドで軽量な試行やテストが容易

• `Injected`/`IProxy`（次章詳細）: 依存関係から計算ロジックをDSL的に構築する強力な機能


# 6. ユースケース例



## 6.1 モデルロードと実行時パラメータ (LLMやStable Diffusionなど)



機械学習モデル、とくに大規模言語モデル（LLM）や拡散モデル（Stable Diffusion）のような巨大なモデルを用いる際、以下のような要望がよくあります。

• **一度だけモデルをロードして再利用したい**：

毎回関数を呼び出すたびに巨大モデルをロードしていると待ち時間が馬鹿になりません。

できればモデルは一度ロードしておき、その後の関数実行ではロード済みのモデルを使い、入出力パラメータ（promptやseed）は都度変えたいところです。

• **実行時に変わるパラメータを柔軟に渡したい**：

LLMであればpromptを毎回変えたいですし、画像生成モデルであればseedやstepsを呼び出し元が自由に指定できるようにしたいものです。



pinjectedの@injectedデコレータとwithステートメント、CLIオーバーライド、~/.pinjected.pyなどの機能を組み合わせれば、これらの要望を自然に実現できます。



**例: LLM生成タスク**

```python 
# llm_example.py
from pinjected import instance, injected, design
import openai
import os

@instance
def openai_api_key():
    # ~/.pinjected.py で設定されたキーを自動注入することも可能
    return os.environ['OPENAI_API_KEY']

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

base_design = design()

# CLIからrunコマンドで実行できるように
@instance
def run_gen_text(generate_text):
    # デフォルトのprompt指定（なければ、実行時にユーザーが指定する想定）
    return generate_text("Hello, who are you?")

# __pinjected__.py ファイルを作成し、以下のように書きます
from pinjected import design

__design__ = design()  # Pinjected対応を示すマーカー

# 以下のレガシーな方法は非推奨です
# __meta_design__ = design() # Pinjected対応を示すマーカー
```

上記ではllm_clientが一度注入され、generate_text関数ではllm_clientを再利用しつつ、promptは呼び出し時に好きな値を渡せます。



このrun_gen_textを実行するには、
```bash
python -m pinjected run llm_example.run_gen_text
```

とします。

promptを変えたい場合は、run_gen_textをgenerate_textに直接アクセスして呼び出すことも可能です。

例えば、promptをCLIから与えたいなら、@injectedな関数を直接実行し、--オプションで指定する仕組みを利用したり、run_gen_text関数自体を実行時に置き換えることも容易です。



**例: Stable Diffusionによる画像生成**



Stable Diffusionパイプラインを使う場合、GPU上で一度モデルをロードしておけば、後はpromptやseedを変えるだけで素早く画像生成が可能です。

```python
# sd_example.py
from pinjected import instance, injected, design

@instance
def sd_pipeline():
    # Stable Diffusionパイプラインをロード（重い処理）
    # 例: from diffusers import StableDiffusionPipeline
    # pipeline = StableDiffusionPipeline.from_pretrained("runwayml/stable-diffusion-v1-5", torch_device="cuda")
    return "LoadedSDPipeline"  # ダミー文字列で代替

@injected
def generate_image(sd_pipeline, /, prompt: str, seed: int = 42):
    # sd_pipelineはDIから
    # prompt, seedは実行時引数として好きな値を渡す
    print(f"Generating image with prompt='{prompt}' and seed={seed} using {sd_pipeline}")
    # 実際には sd_pipeline(prompt=prompt, num_inference_steps=50, generator=torch.Generator().manual_seed(seed))
    return "dummy_image"

@instance
def run_gen_image(generate_image, prompt,seed):
    return generate_image(prompt,seed)
```

run_gen_imageを通じて、promptやseedを変えるには、CLIで--prompt="..." --seed=123などを渡すことができます。



**まとめ**



@injectedを使うと「モデルロードはDIで固定」「変動パラメータは実行時に自由指定」という設計が自然に行えます。

これにより、大規模モデルを扱う際にも、**コード変更なしで反復試行**が容易になり、promptやseedを色々変えつつ実験を進める「研究開発」タスクが非常にスムーズになります。



このようなユースケースはLLMやStable Diffusionに限らず、あらゆる「重い初期化を伴うコンポーネント＋軽い実行時パラメータ」というパターンで有効に機能します。



次の節では、キャッシュパスや外部リソースパスの柔軟な管理など、別の観点からpinjectedの有用性を示します。

## 6.2 キャッシュパスや外部リソースパスの柔軟な管理



研究開発では、データやモデルのキャッシュをファイルシステムに保持したり、

環境によって異なるリソースパス（例: 研究室内サーバー用のパス、ローカルマシン用のパス、クラウドストレージ用のパス）を扱うことがよくあります。



従来は、cfg.cache_dirやos.getenv("CACHE_DIR")のように固定的な方法でパスを指定し、必要に応じてif分岐や文字列操作でパスを切り替えていました。

pinjectedを使えば、パスも依存関係として扱え、injected("cache_path") / "subdir" のような直観的なDSL的表記でパスを組み立てられます。



**シンプルな例: キャッシュパス管理**

```python
# cache_example.py
from pinjected import instance, design, injected

from pathlib import Path

@instance
def cache_dir():
    # ~/.pinjected.py でこの値を "/home/user/.cache/myproject" などに注入可能
    return Path("/tmp/myproject_cache")

@instance
def embeddings_cache_path(cache_dir):
    # embeddings.pkl ファイルまでのパスを返す
    return cache_dir / "embeddings.pkl"

@instance
def metadata_cache_path(cache_dir):
    return cache_dir / "metadata.json"
```

これでembeddings_cache_pathやmetadata_cache_pathは、cache_dirによって決まる相対パスを自動的に返すようになります。

cache_dirをユーザーローカルの~/.pinjected.pyで別の場所に差し替えれば、すべてのキャッシュパスが一括で変更されます。



**パス組み立てのDSL的記述**



pinjectedは、`Injected`や`IProxy`を使うと、もっと柔軟な記述が可能になります。

たとえば、injected("cache_dir")でcache_dirを`IProxy`オブジェクトとして参照し、/ "cache_1.pkl"のように書くと、依存関係上のパス計算がDSL的に行えます。

```python
from pinjected import Injected

cache_files = Injected.dict(
    embeddings = injected("cache_dir") / "embeddings.pkl",
    metadata = injected("cache_dir") / "metadata.json"
)
```

cache_filesは{'embeddings': Path(...), 'metadata': Path(...)}に相当する`IProxy`オブジェクトになり、`design.to_graph()[cache_files]`とアクセスすれば実際のパス辞書が得られます。



**環境切り替え例**



~/.pinjected.pyや--overridesオプションを使えば、環境に応じてcache_dirを切り替えることができます。

• ローカル開発環境ではcache_dir="/home/user/.cache/myproject"

• サーバー環境ではcache_dir="/mnt/server_storage/cache"

• クラウド環境ではcache_dir="gs://mybucket/cache"



このような設定を簡単に切り替えれば、同じコードがどの環境でも適応可能になり、特定のコード修正やif分岐なしでパス変更が実現できます。



**キャッシュ以外のリソースにも応用**



この考え方はキャッシュパスに限りません。モデルウェイトファイルのパス、ログディレクトリ、テンポラリファイル、さらには外部APIエンドポイントURLなど、あらゆる「環境によって変わるリソース指定」を依存パラメータとして扱えます。



たとえば、base_urlをinstances()で定義し、base_url / "api/v1/data"のような表記でエンドポイントを生成することも可能です。

特に複雑な条件分岐や文字列操作を行わなくとも、design()やinjected()でのDSL的操作でパスやURLを直感的に構築できます。

**まとめ**



pinjectedによるパスやリソース管理は、コード上でのif分岐や手動での文字列結合を排除し、

**直感的なDSL的表記で環境・条件依存のパスやURLを組み立てる**ことができます。



~/.pinjected.pyと組み合わせれば、研究開発者ごとのローカル設定や機密情報、リソース配置の違いを簡単に吸収できます。

また、CLIオプションによる一時的なオーバーライドも可能であり、実験状況に応じて即座にリソースパスを切り替えることができます。

## 6.3 設定バリエーション生成と再利用



研究開発の現場では、ハイパーパラメータ探索や条件分岐的な実験を数多く試す必要があります。

「学習率を0.001、0.01、0.1で試す」「モデルアーキテクチャをAとBで比較する」「保存先をローカルとリモートで切り替える」など、同じ基本的なコードを土台に、様々な設定バリエーションを展開したい場面は日常茶飯事です。



pinjectedでは、design()による依存合成を使って、これらのバリエーションをプログラム的に生成し、簡潔に管理できます。



**簡単な例：学習率バリエーション**

```python
from pinjected import instances

base_design = instances(
    learning_rate=0.001,
    batch_size=128,
    model_identifier="model_base"
)

# 学習率を変えたバリエーションを生成
conf_lr_001 = base_design + instances(learning_rate=0.001)
conf_lr_01 = base_design + instances(learning_rate=0.01)
conf_lr_1 = base_design + instances(learning_rate=0.1)
```

これでconf_lr_001、conf_lr_01、conf_lr_1という3つのバリエーションが得られ、CLIから--overrides={your_module.conf_lr_01}と指定すれば、その時点で学習率0.01での実験が行えます。



**モデルやデータセットの組み合わせ**



design()は単純な値の上書きだけでなく、依存オブジェクトの差し替えも可能です。

たとえば、model__resnetやmodel__transformerのような別々の@instance関数が定義されている場合、学習率バリエーションに加えて、モデルアーキテクチャのバリエーションも簡単に生成できます。

```python
model_resnet = instances(model=model__resnet)
model_transformer = instances(model=model__transformer)

conf_lr_001_resnet = conf_lr_001 + model_resnet
conf_lr_001_transformer = conf_lr_001 + model_transformer

conf_lr_01_resnet = conf_lr_01 + model_resnet
conf_lr_01_transformer = conf_lr_01 + model_transformer
```

このように、+演算子を繋げるだけで、学習率×モデルアーキテクチャの組み合わせを簡易に展開できます。

最終的には、python -m pinjected run your_module.run_train --overrides={your_module.conf_lr_01_resnet}のような形で、特定の条件を選び出して実験を即実行できるようになります。



**バリエーションの再利用性**



design()はイミュータブルなため、一度定義したバリエーションを何度でも再利用できます。

たとえば、次の日にはロス関数やデータセットのバリエーションも追加したくなったら、同様に+演算子で組み合わせればOKです。

```python
loss_crossentropy = instances(loss="crossentropy")
conf_lr_01_resnet_ce = conf_lr_01_resnet + loss_crossentropy
```

こうして、デザインはまるでレゴブロックのように組み合わせ可能で、管理コストを最小限に留めつつ多数の条件を表現できます。



**スクリプトやGUIとの連携**



もしGUIツールやスクリプトを用いて、多数の条件を自動実行するようなパイプラインを組みたい場合、design()で定義されたバリエーション群をプログラム的に列挙し、subprocess.run()でpinjected runコマンドを呼ぶなどして、ハイパーパラメータ探索を自動化できます。



この方法なら、コード本体は変更せずに、design()記述部分やCLIオプションで設定をコントロールするだけで、新たな実験条件を次々に投入できます。



**まとめ**



design()によるバリエーション生成と再利用により、ハイパーパラメータ探索や条件分岐的な実験設計が驚くほど簡潔になります。

学習率やモデル、データセット、ロス関数など、あらゆるパラメトリックな選択肢をinstances()やproviders()で記述し、+演算子で合成することで、数多くの実験条件を気軽に管理できます。



これにより、研究開発段階で重要となる「迅速な試行」「簡潔な条件切り替え」「コード本体の最小限な変更」での大規模なバリエーション生成が、ストレスなく実現可能となります。


# 7. `Injected`/`IProxy`による依存関係の関数的合成



## 7.1 `Injected`と`IProxy`の概念



これまで紹介してきたpinjectedの機能（@instance, @injected, design()による依存合成、CLIオーバーライド、~/.pinjected.py、withステートメントなど）を使えば、従来のDIツールと異なる柔軟性を得られます。しかし、pinjectedにはさらに一段階進んだ概念が存在します。それが`Injected`と`IProxy`です。



**`Injected`: 「未解決の依存」を表すオブジェクト**



`Injected`は、pinjectedが内部で「依存が必要な変数」を表現するためのオブジェクトです。

たとえば`Injected.by_name("cache_dir")`と書くと、「cache_dirという名前で解決されるはずの依存」が`Injected`オブジェクトとして表されます。



`Injected`は「DIによる解決がまだ行われていない値」を抽象的に表すため、

design.to_graph()で実際に提供されるまで具体的な値は決まりません。

この「未解決だが、将来DIによって解決されるであろう値」を操作することで、pinjectedは依存関係を素材として計算パイプラインを記述することが可能になります。



**`IProxy`: Python的なDSLで`Injected`を操るためのプロキシ**



`IProxy`は、`Injected`オブジェクトを直感的かつPythonicな記法で操作できるようにするためのラッパ（プロキシ）クラスです。



`IProxy`を使えば、injected("cache_dir") / "embeddings.pkl"のように、あたかもPathオブジェクトを操作するかのように演算子/でパス結合したり、

(injected("a") + injected("b")) / 2のように、`Injected`な値同士の算術演算を行うことができます。



つまり、`IProxy`は「依存関係に基づいて値が後で求まる」オブジェクト同士を、演算子オーバーロードやメソッドチェーンで合成し、一種のDSL（ドメイン固有言語）的に依存関係の計算ロジックを表現することを可能にします。



**なぜ`Injected`/`IProxy`が有用なのか**



これまでのDIは、「必要なオブジェクトをコンストラクタで注入する」という単純なモデルが中心でした。しかし、研究開発では依存関係が複雑になり、「依存する値を元に新しい値を計算」「複数の依存値を組み合わせて高度な初期化処理を行う」といった要件が生じることがあります。



`Injected`/`IProxy`を使えば、

• 複数の`Injected`な値をマップやジップのような関数的合成で組み合わせる

• `Injected`同士を辞書やリストにまとめる

• パラメータを動的に計算し、新たな依存値として利用する

といった柔軟な操作が実現します。



これは、DIフレームワークを超えて、依存関係グラフ上で計算ロジックを構築できるようになることを意味します。つまり、pinjectedは単なるDIツールではなく、**依存関係を素材とした計算パイプラインを記述する基盤**としても機能します。



**`Injected`と`IProxy`のシンプルな例**

```python
from pinjected import `Injected`

a = Injected.by_name('a')  # 'a'という名前の依存値を表す`Injected`オブジェクト
b = Injected.by_name('b')

# `IProxy`化して算術演算
a_proxy = a.proxy
b_proxy = b.proxy
sum_proxy = a_proxy + b_proxy

# designでa=10, b=5を定義しておけば、design.to_graph()[sum_proxy] == 15となる
```
このように、sum_proxyは「aとbが解決された後、その和を計算する依存値」を表し、design.to_graph()で実際に計算が実行されます。

## 7.2 map/zipによる関数的合成と`Injected.dict/list`



`Injected`オブジェクトは、mapやzip、あるいは`Injected.dict()`や`Injected.list()`などのメソッドを通じて、複数の依存値を関数的に合成できます。

これは、従来のDIでは考えにくかった「依存値同士を計算して新たな依存値を形成する」手法を、直感的かつ宣言的に記述できる強力な仕組みです。


**mapによる単純な変換**



mapは、1つの`Injected`値を別の値へ変換する関数を適用します。

たとえば、aという`Injected`な整数値を受け取り、それに1を足した`Injected`を作るには以下のようにします。

```python
from pinjected import `Injected`

a = Injected.by_name("a")  # aは例えばdesignでa=10と定義されていると仮定
a_plus_one = a.map(lambda x: x + 1)
```
a_plus_oneは「aが解決された後、その値に1を加えた値」を表します。

design.to_graph()[a_plus_one]を呼べば、a=10なら11が得られます。



**zip/mzipによる複数依存値の結合**



zipやmzipを使えば、複数の`Injected`値をタプルや複数引数の関数に渡せます。
```python
b = Injected.by_name("b")
ab_tuple = Injected.zip(a, b)  # (resolved_a, resolved_b)のタプル`Injected`
```

これでab_tupleは(a, b)のタプル値になる`Injected`です。

mzip(multi-zipの意)を使えば3つ以上の`Injected`値もまとめられます。
```python
c = Injected.by_name("c")
abc_tuple = Injected.mzip(a, b, c)  # (resolved_a, resolved_b, resolved_c)
```

**`Injected.dict()`や`Injected.list()`によるデータ構造化**



`Injected.dict()`や`Injected.list()`を用いると、複数の`Injected`値をまとめて辞書やリストとして表現できます。

```python
my_dict = Injected.dict(
    learning_rate=Injected.by_name("learning_rate"),
    batch_size=Injected.by_name("batch_size")
)

my_list = Injected.list(
    Injected.by_name("model"),
    Injected.by_name("dataset"),
    Injected.by_name("optimizer")
)
```

my_dictは{'learning_rate': resolved_learning_rate, 'batch_size': resolved_batch_size}を表し、

my_listは[resolved_model, resolved_dataset, resolved_optimizer]を表します。



これらは、design.to_graph()呼出し時に実際の値へと解決されます。

**部分的な計算組み立て**



mapやzipといった手法は、部分的な計算ロジックをInjection Graph上で組み立てるのに有用です。

例えば、ある値xに対し、y = f(x)と計算し、それをさらにz = g(y)と変換し、最後にh(z, w)を計算するといった一連の処理を、`Injected`とmap/zip操作で表現できます。



このような記述ができると、ハイパーパラメータが与えられた時にそれを元にモデル設定を計算する、あるいはcache_dirとmodel_nameからmodel_weights_pathを計算するといった、柔軟な依存グラフ計算が宣言的に行えます。



**`Injected`同士を組み合わせるユースケース例**

• **動的な学習率決定**：

learning_rate_baseとscale_factorを`Injected`で管理し、

learning_rate = learning_rate_base.map(lambda lr: lr * scale_factor)のように書けば、

環境やCLIオプションでscale_factorを変えるだけで最終学習率が自動計算されます。

• **パス結合・パラメータ結合**：

model_nameとcache_dirからmodel_weights_path = cache_dir / f"{model_name}_weights.pth"を計算するInjectされた関数を作るなど、パラメータ組み合わせで動的にリソースパスを生成可能。

• **複数設定を一度に取得**：

複数のパラメータを`Injected.dict()`でまとめて取得し、その集合を評価スクリプトに渡すことで、複雑な初期化ロジックを単純化できます。



**まとめ**



map, zip, `Injected.dict()`, `Injected.list()`といった関数的合成手法を用いることで、単なるオブジェクト注入を超えた計算パイプラインの記述が可能になります。



DIツールの領域を越え、pinjectedは「依存関係を素材に計算ロジックやデータ構造を宣言的に構築する」フレームワークとしても機能します。



こうした柔軟なDSL的表記は、研究開発の迅速な試行錯誤や、複雑な条件をコード最小限で扱う場合に特に有効です。


## 7.3 `IProxy`によるDSL的表記の拡張例


前節で紹介したmapやzipによる合成に加え、`IProxy`は演算子オーバーロードやインデックスアクセスなどをサポートしています。

これにより、`Injected`オブジェクト同士の計算や、依存オブジェクトから一部要素を取り出す操作が、あたかも普通のPythonオブジェクトを扱うような記法で記述できます。



**パス操作や計算式合成のさらなる例**



たとえば、"cache_dir"を依存キーとする`Injected`がある場合（cache_dirキーからパスオブジェクトが注入される想定）、`IProxy`を用いると次のような書き方が可能です。
```python
cache_subdir = injected("cache_dir") / "subdir" / "data.pkl"
```

ここでinjected("cache_dir")は"cache_dir"という依存キーに対応する`Injected`を`IProxy`として取得し、/ "subdir"でパス結合、その後さらに/ "data.pkl"でファイル名を付加しています。

このcache_subdirは最終的にdesign.to_graph()呼出し時にPath("/home/user/.cache/myproject/subdir/data.pkl")のような具体的パスに解決されます（cache_dirが何にマップされているかによります）。



**インデックスアクセスや属性アクセス**



`IProxy`オブジェクトは、`[]`によるインデックスアクセスもサポートしており、辞書やリスト、属性アクセスを用いて依存オブジェクトの一部要素を柔軟に扱えます。
```python
train_sample_0: `IProxy` = injected("dataset")["train"][0]
```
ここで、injected("dataset")は"dataset"という依存キーに対応する`Injected`を`IProxy`として取得し、`["train"]`で"train"キーを参照、`[0]`でその最初のサンプルを取得する`IProxy`を表します。

最終的な解決時にdatasetがどのような構造を持つかにより、このtrain_sample_0は実際のデータサンプルを返すことになります。

**@injectedを関数ではなく文字列引数で利用**



@injectedは通常デコレータとして使用しますが、@injected("some_name")のように文字列を渡すと、`Injected`.by_name("some_name")と同等の`IProxy`が返されます。

これにより、`injected("dataset")["train"][0]`のような記述が可能になり、依存オブジェクトへのアクセスをシンプルなDSLのような形で記述できます。

**モデル生成やLLMの操作にも応用**



このようなDSL的表記は、単にパスやデータの要素参照だけでなく、複雑なモデル生成処理やLLM呼び出しにも応用可能です。

たとえば、injected("llm_client").chat("Hello")と書けば、llm_client依存キーに対応するオブジェクトが解決されてからchat("Hello")メソッドが呼ばれ、その結果がInjectされた値として扱えるでしょう。

**まとめ**



`IProxy`を使った演算子オーバーロード、インデックスアクセス、属性アクセスにより、pinjectedはDIグラフ上での計算パイプラインを自然かつDSL的に記述できます。

@injectedが文字列引数をとった場合に`IProxy`を返す仕組みを活用すれば、依存オブジェクトへのアクセスが一層直感的になり、コードの可読性や再利用性が向上します。



こうした機能を組み合わせることで、pinjectedは「依存するオブジェクトを、遅延評価される変数や関数呼び出しのように操作する」強力な言語内DSL環境を提供します。


## 7.4 複雑なユースケース例の再構築：LLM応答をキャッシュに保存する計算パイプライン

これまで、`Injected`/`IProxy`や`@injected`、`@instance`、`design()`などを使ったDIとDSL的記法を紹介してきました。ここでは、これらを総合的に組み合わせたやや複雑なユースケースとして、「LLMモデルへの問い合わせ結果を指定パスに保存する」パイプラインを示します。

### シナリオ

- LLMモデルに対して`prompt`と`temperature`を指定して問い合わせ（`run_llm_query`）し、その応答をファイルに保存（`save_response_to_cache`）します。
- `cache_dir`はユーザーローカルな`~/.pinjected.py`で変更可能。
- `prompt`や`temperature`は`__pinjected__.py`の`__design__`で指定し、CLIオプションで上書き可能。
- `response_cache_path`は`cache_dir`とファイル名の合成で決まるため、``IProxy``を用いて`__design__`で定義します。
### コード例

```python
# complex_example.py
from pinjected import instance, injected, design, Injected

@instance
def llm_api_key():
    return "sk-xxxxx"  # ~/.pinjected.pyでこの値をユーザー毎に上書き可能

@instance
def llm_client(llm_api_key):
    class DummyLLMClient:
        def query(self, prompt, temperature=0.7):
            return f"LLM-response-to:{prompt} at temp:{temperature}"
    return DummyLLMClient()

@instance
def cache_dir():
    # ~/.pinjected.pyで "/home/user/.cache/myproject" に変更するなど
    return "/tmp/myproject_cache"

@injected
def run_llm_query(llm_client, /, prompt: str, temperature: float = 0.7):
    # prompt, temperatureはDIで注入される
    response = llm_client.query(prompt, temperature=temperature)
    return response

@instance
def save_response_to_cache(run_llm_query,response_cache_path):
    # run_llm_queryはLLM応答文字列（DIで解決済み）
    response = run_llm_query
    print(f"Saving response='{response}' to {response_cache_path}")
    with open(response_cache_path, "w") as f:
        f.write(response)
    return response_cache_path

# __pinjected__.py ファイルを作成し、__design__でresponse_cache_path, prompt, temperatureを組み込む
# Injected.by_name('cache_dir').proxy / "llm_response.pkl" とすることで
# cache_dirが変われば自動的にキャッシュファイルパスが変わる

# __pinjected__.py
from pinjected import design

__design__ = design(
    response_cache_path=Injected.by_name('cache_dir').proxy / "llm_response.pkl",
    prompt="Hello world",
    temperature=0.9
)

# 以下のレガシーな方法は非推奨です
# __meta_design__ = design(
#     overrides=design(
#         response_cache_path=Injected.by_name('cache_dir').proxy / "llm_response.pkl",
#         prompt="Hello world",
#         temperature=0.9
#     )
# )

```

### 実行方法

```bash
# デフォルト設定(hello world, temp=0.9, cache=/tmp/myproject_cache/llm_response.pkl)
python -m pinjected run complex_example.save_response_to_cache
```
出力例:

```bash
Saving response='LLM-response-to:Hello world at temp:0.9' to /tmp/myproject_cache/llm_response.pkl
```
`prompt`や`temperature`を変えたい場合は、CLIオプションで上書き可能です。

```bash
python -m pinjected run complex_example.save_response_to_cache --prompt="How are you?" --temperature=1.0

```
結果は
```bash
Saving response='LLM-response-to:How are you? at temp:1.0' to /tmp/myproject_cache/llm_response.pkl

```

となり、`prompt`と`temperature`が実行時に変更されました。

`cache_dir`を`~/.pinjected.py`で`/home/user/.cache/myproject`に変えれば、`llm_response.pkl`はそちらのディレクトリに保存されるようになります。  
コードの変更は不要で、環境設定やCLIオプションの指定だけで動作が切り替わる点がpinjectedの強みです。

### まとめ

この例では、DI経由で依存を渡し、`@injected`で実行時可変なパラメータ（prompt, temperature）を宣言的に扱い、``IProxy``でパスをDSL的に構築し、`__meta_design__`でdefault値を提供しつつCLIや`~/.pinjected.py`で上書き可能な体制を示しました。

pinjectedが提供する多層的な柔軟性（DI、DSL的記法、ユーザーローカル設定、CLIオプション、`Injected`/`IProxy`による関数的合成）によって、研究開発の実験環境は柔軟かつ再利用性の高いものになります。

# 8 VSCode, PyCharmプラグイン
pinjectedを用いた開発をより快適にするため、以下の機能を持ったプラグインを用意しています。
VSCode版: pinjected-runner
PyCharm版: 公開準備中

## ワンクリック実行
![](https://storage.googleapis.com/zenn-user-upload/ab6e9e608516-20241214.png)
画像はPyCharmのものですが、プラグインをインストールすると、
@injected,@instanceを付与された関数か、`Injected`/`IProxy`の型アノテーションがつけられた変数について、ワンクリックで実行可能なボタンが追加されます。

これにより、例えばデータセットの１つ目だけを確認したいと思ったときには、
```python
check_dataset:IProxy = injected('dataset')[0]
```
と記述しクリックするだけで、データセットの0番目を出力することができるようになります。

## 依存関係可視化
![](https://storage.googleapis.com/zenn-user-upload/1132606fd41b-20241214.png)
pinjectedは依存関係解決時に依存グラフの解決結果をログに出力しますが、追加でこの木構造をブラウザで視覚的に可視化することが可能です。
これによって特定の変数がどのモジュールに利用されているか、もしくは特定のモジュールが依存過多に陥っていないかなどを視覚的に確認することが可能です。


# 9. まとめと今後の展望

## 9.1 Pinjected導入によるQOL向上のポイント

これまでの章を通じて、pinjectedが実験コード管理において以下のような利点をもたらすことを示してきました。

1. **cfgオブジェクト全依存やif分岐地獄からの脱却**  
   従来の`cfg`ベース実装では、全てのパラメータが一箇所に集中し、コード全体がそのオブジェクトに依存しがちでした。また、条件分岐を多用しなければならず、機能の切り替えや拡張のたびに複雑なif文が増える問題がありました。

   pinjectedでは、`@instance`や`design()`を利用して、必要なオブジェクトやパラメータを明示的かつ独立に記述できます。  
   if分岐ではなく、`design()`による依存オブジェクトの切り替えで拡張性と可読性が大幅に向上し、「コードを読んでどこで何が実行されるかがわからない」という状況が緩和されます。

2. **CLIと`~/.pinjected.py`による柔軟な実行条件変更**  
   pinjectedはCLIオプションを標準サポートしており、`--model=...`や`--batch_size=64`などの指定で、コードを書き換えることなくパラメータや依存関係を切り替えられます。  
   また、ユーザーローカルな`~/.pinjected.py`により、個人環境固有のAPIキーやパス設定を安全かつ簡潔に管理可能です。

   これにより、研究開発者は環境や条件を素早く切り替え、追加実験やデバッグを行えます。  
   コードが一切変わらなくても、実行時のオプションやローカル設定で新たな実験条件を即座に試せるQOL向上があります。

3. **@injectedによる実行時引数分離と部品テスト容易化**  
   `@injected`を用いることで、モデルロードなどの固定的な重い処理はDIで行いながら、`prompt`や`seed`といった実行時可変なパラメータを呼び出し時に決める構造を作れます。  
   これにより、大規模モデルを一度ロードしておけば、プロンプトやハイパーパラメータを何度も変えながら素早く実行でき、実験速度と開発効率が向上します。

   また、特定のデータセットやモデルのみを単独で取得・テストすることが容易になり、部分的デバッグも簡単です。

4. **`Injected`/`IProxy`による高度なDSL表記と計算パイプライン構築**  
   `Injected`や`IProxy`を使えば、依存関係をDSL的に記述し、複雑な計算ロジックやリソースパス合成を宣言的かつ直感的に表現できます。  
   従来はif分岐や文字列操作、膨大な初期化コードで対処していた複雑な条件を、`design()`と組み合わせてシンプルに記述可能です。

   このレベルの抽象化により、実験コードは「依存するものを組み合わせて結果を得る」計算パイプラインとして表現でき、コード再利用性や保守性が向上します。


### 総合的効果

pinjectedの導入により、研究開発において頻繁に要求される「ちょっとした設定変更」「部分的な機能テスト」「新たなモデルやパラメータを試す」という行為が、数行の最低限な追加で既存機能を影響に与えずに実装可能になります。

結果として、

- 実験コードの再利用性・可読性が向上
- if分岐や冗長な設定管理の削減
- 部分テスト、デバッグ、迅速な条件変更がストレスフリーに

といった効果が得られ、研究開発の反復速度と品質が大幅に改善されます。

次節では、この先pinjectedがどのような拡張や応用可能性を持っているか、今後の展望を考えてみます。

## 9.2 DIを超えた依存関係管理・計算基盤としての可能性

これまで見てきたように、pinjectedは単なるDI（Dependency Injection）ツールにとどまりません。  
``Injected``や``IProxy``を活用することで、依存関係は単なるオブジェクト生成手続きではなく、「後で解決される値（Lazy Value）」や「計算前の抽象的なAST（Abstract Syntax Tree）」のように扱えます。  
これにより、依存グラフがまるで小さな関数的言語やDSLのように振る舞い、複雑なロジックをシンプルな宣言的表記で記述できるようになります。

### さらなる応用例

1. **大規模ハイパーパラメータ探索**：  
   複数のパラメータバリエーション（学習率、モデル構造、データセット構成）を`design()`で組み立て、``Injected`/`IProxy``で最終的な実行パイプラインを生成すれば、多数の実験条件を管理する際に特別なコードを追加せずに、CLIやconfigファイル上で自由に条件を切り替えられます。  
   自動スクリプトやGUI、RayやDaskなどの分散フレームワークと組み合わせれば、大規模な条件探索や実験管理がスムーズになります。

2. **複合パイプラインの一元管理**：  
   データ取得、前処理、モデル推論、結果可視化、ログ保存といった複合的な処理を、``Injected`/`IProxy``を用いて一つの計算グラフとして記述できます。  
   例えば、`dataset -> model -> postprocess -> save_results`といった一連の流れを全て`injected()`で定義し、`design()`で繋いでいくことで、条件変更やモジュール差し替えが容易になります。

3. **研究開発ツールチェーンとの統合**：  
   pinjectedはIDE統合や`__meta_design__`、`~/.pinjected.py`などを介して既存の研究開発フローに溶け込みやすい構造になっています。


### まとめ

pinjectedは、もともとDIをシンプルかつ強力に扱うためのツールとして設計されましたが、  
``Injected`/`IProxy``による関数的合成やDSL的記法、`design()`との組み合わせにより、「依存関係の管理」を超えた「依存関係に基づく計算パイプライン構築基盤」と見ることもできます

# 10. リスクと課題

## 10.1 学習コストと開発体制への影響

pinjectedはDIや`Injected`/`IProxy`といった、従来のcfg依存型コードとは異なるパラダイムを導入します。そのため、以下の点が課題となり得ます。

- **学習コスト**:  
  開発チームメンバーが、`@instance`や`@injected`、`design()`、`Injected`/`IProxy`などの概念を理解・習熟する必要があります。特にDSL的な記法は、慣れるまでに時間がかかるかもしれません。

- **チーム内共通理解の確立**:  
  DIやDSL的表現への理解度がチームメンバー間でまちまちだと、コードレビューやバグ対応が難しくなります。

## 10.2 デバッグやエラー追跡の難しさ

pinjectedでは依存解決が遅延され、実行時に値が生成されます。この仕組みは柔軟性を生む一方、以下のような課題を伴います。

- **エラー発生タイミング**
  `Injected`/`IProxy`を多用した複雑な計算パイプラインでは、実行中のどの段階で問題が起きたか把握しにくい場合があります。
- **スタックトレースの不明瞭化**:  
  DIとDSL的記法が絡むことで、どの関数で例外が出たのかが直感的にわかりづらいことがあります。

**実装済みの対策**:
- IDE統合された依存関係可視化機能が提供されています。
- キーが解決できなかった場合、何がそのキーに依存しているのか明確に示されます。

## 10.3 メンテナンス性とスケール問題

大規模プロジェクトで大量の`design()`や`instances()`を合成し、多数の依存キーを扱うと、以下の問題が顕在化します。

- **依存キーの衝突や整理難**:  
  同じ名前のキーが別の箇所で定義されて競合したり、意味不明な名前が増えて整理できなくなる恐れがあります。
- **爆発的なバリエーション管理**:  
  ハイパーパラメータや条件バリエーションが指数的に増えた場合、`design()`の組み合わせが膨大になり、管理不能になる可能性があります。

**対策案**:

- 命名規約による命名衝突の回避
    - pinjectedをライブラリ用途で使う場合には依存名として`__my_package__module__param1__"など衝突しない名前を用いるなど

# まとめ

本記事では、研究開発現場の実験コードが抱える課題（巨大なcfg依存や膨大なif分岐、部分的テストの難しさなど）に対し、pinjectedを用いたDependency Injection (DI) アプローチを有効な解決策として提案してきました。

pinjectedの主なメリット:

- 設定管理の柔軟性：design()による依存定義とCLIオプション、~/.pinjected.pyによるローカル設定上書きにより、コードを書き換えずに実行条件を即座に変更できます。
- if分岐の削減と可読性向上：@instanceや@injectedを使った明示的なオブジェクト注入により、条件分岐に依存しないコード設計が可能です。
  部分テスト・デバッグの容易化：特定コンポーネント（モデル、データセットなど）を単独で実行・確認できるため、小規模な検証やデバッグがシンプルになります。
- 高度なDSL的表現：`Injected`/`IProxy`を用いて、パラメータ計算やパス生成などを宣言的かつ直感的に記述でき、複雑な実験条件をスムーズに扱えます。

これらの特徴により、研究開発の反復速度が向上し、拡張や再利用も容易になります。今後はさらにIDEとの統合強化や、大規模ハイパーパラメータ探索・分散実行への対応など、[pinjected](https://github.com/proboscis/pinjected)が実験管理基盤として進化していく可能性もあります。

実際の導入時には、学習コストや既存コードからの移行などのハードルがありますが、段階的な導入や個人開発に適していると思います。快適なコーディングのため、役に立てば何よりです。

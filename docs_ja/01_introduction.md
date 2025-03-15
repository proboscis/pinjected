Pinjected
Pinjectedは、pinjectにインスパイアされた依存性注入/依存性解決ライブラリです。
このライブラリを使用すると、複数のPythonオブジェクトを簡単に組み合わせて最終的なオブジェクトを作成できます。
最終的なオブジェクトを要求すると、このライブラリは自動的にすべての依存関係を作成し、それらを組み合わせて最終的なオブジェクトを作成します。
インストール
pip install pinjected
ドキュメント
チュートリアルと例については、以下をお読みください。
より具体的なAPIドキュメントについては、ドキュメントをご覧ください。
機能

コンストラクタを介した依存性注入
オブジェクト依存性解決
依存関係グラフの可視化
IntelliJ IDEA用の実行構成の作成
CLIサポート
関数型依存性注入の構成

問題
機械学習コードを書く際、多くのオブジェクトを作成し、それらを組み合わせて最終的なオブジェクトを作成する必要があることがよくあります。
例えば、モデル、データセット、オプティマイザ、損失計算器、トレーナー、評価器を作成する必要があるかもしれません。
また、モデルを保存および読み込むためのセーバーとローダーを作成する必要もあるかもしれません。
通常、これらのオブジェクト作成はYAMLなどの設定ファイルによって制御されます。
設定ファイルはコードの最上部で読み込まれ、各オブジェクト作成関数に渡されます。
これにより、すべてのコードが設定ファイルに依存し、'cfg'を引数として持つ必要があります。
結果として、すべてのコードがcfgの構造に大きく依存し、cfg オブジェクトなしでは使用不可能になります。
これにより、コードの再利用が難しくなり、コードの構造を変更することも困難になります。
また、各コンポーネントをテストするためには、設定ファイルとともにオブジェクト作成コードを書く必要があるため、簡単なテストも難しくなります。
さらに、設定解析コードとオブジェクト作成コードが組み合わさった数百行のコードをよく目にします。
これにより、コードの読みやすさが低下し、どの部分が実際に作業を行っているのかを推測するのが難しくなります。
解決策
Pinjectedは、各オブジェクト作成関数に設定オブジェクトを渡すことなく、最終的なオブジェクトを作成する方法を提供することでこれらの問題を解決します。
代わりに、このライブラリは依存関係グラフに従って、すべての依存関係を自動的に作成し、それらを組み合わせて最終的なオブジェクトを作成します。
必要なのは、依存関係グラフと各オブジェクトの作成方法を定義することだけです。
残りはこのライブラリが処理します。
このライブラリはまた、依存関係グラフを修正および結合する方法を提供するため、ハイパーパラメータ管理が容易で移植可能になります。
単一責任の原則と依存性逆転の原則を導入することで、コードがよりモジュール化され、再利用可能になります。
このために、このライブラリはDesignとInjectedオブジェクトの概念を導入します。Designは依存関係を持つオブジェクトプロバイダーの集合です。
Injectedオブジェクトは、Designオブジェクトによって構築できる依存関係を持つオブジェクトの抽象化です。
ユースケース
では、これが機械学習実験にどのように役立つのでしょうか？以下に例を示します。
典型的な機械学習コードから始めましょう。（以下のコードを理解する必要はありません。構造だけを見てください。）
pythonCopyfrom dataclasses import dataclass

from abc import ABC,abstractmethod
class IoInterface(ABC): # セーバー/ローダーで使用されるIOのインターフェース
@abstractmethod
def save(self,object,identifier):
pass
@abstractmethod
def load(self,identifier):
pass
class LocalIo(IoInterface):pass
# ローカルでのセーブ/ロードを実装
class MongoDBIo(IoInterface):pass
# MongoDBでのセーブ/ロードを実装
class Saver(ABC):
io_interface : IoInterface
def save(self,model,identifier:str):
self.io_interface.save(model,identifier)

class Loader(ABC):
io_interface : IoInterface # 後で実際の実装を変更できるようにインターフェースのみに依存するようにする
def load(self,identifier):
return self.io_interface.load(identifier)

@dataclass
class Trainer: # 構成可能性を維持するために、クラスをできるだけ小さく保つ
model:Module
optimizer:Optimizer
loss:Callable
dataset:Dataset
saver:Saver
model_identifier:str
def train(self):
while True:
for batch in self.dataset:
self.optimizer.zero_grad()
loss = self.loss_calculator(self.model,batch)
loss.backward()
self.optimizer.step()
self.saver.save(self.model,self.model_identifier)

@dataclass
class Evaluator:
dataset:Dataset
model_identifier:str
loader:Loader
def evaluate(self):
model = self.loader.load(self.model_identifier)
# 読み込んだモデルとデータセットを使用して評価を行う
そして設定パーサー：
pythonCopy       
def get_optimizer(cfg:dict,model):
if cfg['optimizer'] == 'Adam':
return Adam(lr=cfg['learning_rate'],model.get_parameters())
elif cfg['optimizer'] == 'SGD':
return SGD(lr=cfg['learning_rate'],model.get_parameters())
else:
raise ValueError("Unknown optimizer")

def get_dataset(cfg:dict):
if cfg['dataset'] == 'MNIST':
return MNISTDataset(cfg['batch_size'],cfg['image_w'])
elif cfg['dataset'] == 'CIFAR10':
return CIFAR10Dataset(cfg['batch_size'],cfg['image_w'])
else:
raise ValueError("Unknown dataset")

def get_loss(cfg):
if cfg['loss'] == 'MSE':
return MSELoss(lr=cfg['learning_rate'])
elif cfg['loss'] == 'CrossEntropy':
return CrossEntropyLoss(lr=cfg['learning_rate'])
else:
raise ValueError("Unknown loss")

def get_saver(cfg):
if cfg['saver'] == 'Local':
return Saver(LocalIo())
elif cfg['saver'] == 'MongoDB':
return Saver(MongoDBIo())
else:
raise ValueError("Unknown saver")

def get_loader(cfg):
if cfg['loader'] == 'Local':
return Loader(LocalIo())
elif cfg['loader'] == 'MongoDB':
return Loader(MongoDBIo())
else:
raise ValueError("Unknown loader")
def get_model(cfg):
if cfg['model'] == 'SimpleCNN':
return SimpleCNN(cfg)
elif cfg['model'] == 'ResNet':
return ResNet(cfg)
else:
raise ValueError("Unknown model")

def get_trainer(cfg):
model = get_model(cfg),
return Trainer(
model=model,
optimizer = get_optimizer(cfg,model),
loss = get_loss(cfg),
dataset = get_dataset(cfg),
saver = get_saver(cfg),
model_identifier = cfg['model_identifier']
)

def get_evaluator(cfg):
return Evaluator(
dataset = get_dataset(cfg),
model_identifier = cfg['model_identifier'],
loader = get_loader(cfg)
)

def build_parser():
"""
設定構造が変更されるたびに修正が必要な非常に長いargparseコード
"""

if __name__ == "__main__":
# argparseまたはconfig.jsonを使用可能
# cfg:dict = json.loads(Path("config.json").read_text())
# cfg = build_parser().parse_args()
cfg = dict(
optimizer = 'Adam',
learning_rate = 0.001,
dataset = 'MNIST',
batch_size = 128,
image_w = 256,
loss = 'MSE',
saver = 'Local',
loader = 'Local',
model = 'SimpleCNN',
model_identifier = 'model1'
)
trainer = get_trainer(cfg)
trainer.train()
このコードはまず、ファイルまたはargparseを通じて設定を読み込みます。
（ここでは簡単のために、cfgは手動で構築されています。）
次に、cfgオブジェクトを使用してすべてのオブジェクトを作成し、それらを組み合わせて最終的なオブジェクトを作成します。
ここで見られる問題は以下の通りです：

設定への依存：

すべてのオブジェクトがcfgオブジェクトに依存しているため、コードの再利用が難しくなります。
cfgオブジェクトは、PyTorchモジュールやロギングモジュールなど、コードの深い部分で参照されます。
cfgオブジェクトは、コンストラクタだけでなく、オブジェクトの動作を変更するためにメソッド内でも参照されることがあります。


複雑なパーサー：

機能を追加するにつれて、設定オブジェクトのパーサーが非常に長く複雑になります。
コード内に多くのネストされたif-else文が見られます。
ネストされたif-else文のため、実際に実行されるコードブロックを追跡することが不可能です。


手動の依存関係構築：

オブジェクトの依存関係を手動で構築する必要があり、どのオブジェクトを先に作成して渡す必要があるかを考慮しなければなりません。
オブジェクトの依存関係が変更された場合、オブジェクト作成コードを修正する必要があります。

（例えば、新しい損失関数がモデルのハイパーパラメータを使用したい場合、get_model()関数にモデルを渡す必要があります！）





代わりに、Pinjectedを使用してこれらの問題を以下のように解決できます：
pythonCopyfrom dataclasses import dataclass
from pinjected import design,injected,instance

@instance
def optimizer__adam(learning_rate,model):
return Adam(lr=learning_rate,model.get_parameters())
@instance
def dataset__mydataset(batch_size,image_w):
return MyDataset(batch_size,image_w)
@instance
def model__sequential():
return Sequential()
@instance
def loss__myloss():
return MyLoss()

conf:Design = design(
learning_rate = 0.001,
batch_size = 128,
image_w = 256,
optimizer = optimizer__adam,
dataset = dataset__mydataset,
model = model__sequential,
loss = loss__myloss,
io_interface = LocalIo # デフォルトでローカルファイルシステムを使用
)

g = conf.to_graph()
#モデル構造を見てみましょう
print(g['model'])
# トレーニングを行います
g[Trainer].train()
# 評価を行います
g[Evaluator].evaluate()
上記のコードが先ほど述べた問題をどのように解決しているか見てみましょう。

設定への依存：

すべてのオブジェクトがcfgオブジェクトに依存せずに作成されます。
Designオブジェクトが最終的なオブジェクトを構築するための設定として機能します。
各オブジェクトは、オブジェクトが必要とするものにのみ依存し、設定全体には依存しません。
各オブジェクトは最小限の設定でテストできます。

例えば、データセットオブジェクトはbatch_sizeとimage_wだけでテストできます。




複雑なパーサー：

パーサーが単純な関数定義に置き換えられています。
関数定義がシンプルで理解しやすくなっています。
実際に実行されるコードブロックが明確です。
ネストされたif-else文がありません。
文字列から実際の実装への解析がありません。実装オブジェクトを直接渡す
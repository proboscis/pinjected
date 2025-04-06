# Pinjected design() function usage reviewer
This reviewer checks code diff and see if design() function is correctly used.
- When to trigger: pre_commit
- Return Type: approval
- Target Files: .py
- Model: google/gemini-2.5-pro-preview-03-25
- Review scope: file_diff

# design()関数の適切な使用法

## 基本的な使用法

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
    trainer=Injected.bind(Trainer)  # クラスはInjected.bindでラップするか、以下のケースではinjected()でラップする。
)

# Classをbindするその他の例
from dataclasses import dataclass
from torch import nn
@dataclass
class MyTrainer:
    # '_'でprefixされた引数は、injected()によって自動的に依存性として解釈されます。
    _learning_rate: float
    _batch_size: int
    _model:nn.Module
    name:str
    def train(self):
        pass

example_design = design(
    learning_rate=0.001,
    batch_size=128,
    model=injected('model__simplecnn'),
    trainer=injected(MyTrainer)('example_trainer') # name以外は自動的に注入される。
)
"""
上記の例は、コンストラクタ定義がユーザーの管理下にあり完全に引数名を制御できる場合にのみ推奨。
他者のライブラリのクラスを注入する際には、以下の様にファクトリを定義するのが無難
@injected
def lib_trainer(learning_rate,/,name):
    return LibTrainer(learning_rate=learning_rate, name=name)
"""
```



## 注意点

1. クラスを直接指定する場合は、必ず`Injected.bind()`でラップしてください。
```python
# 正しい使用法
trainer=Injected.bind(Trainer)

# 誤った使用法
trainer=Trainer  # クラスを直接指定するとエラーになる
```

2. `design()`関数は不変オブジェクトを返します。変更したい場合は新しい`design()`を作成して`+`演算子で合成してください。
```python
# 正しい使用法
new_design = old_design + design(batch_size=64)

# 誤った使用法
old_design.batch_size = 64  # designは不変オブジェクトなのでエラーになる
```

3. 設定バリエーションを作成する際は、ベースとなるdesignを再利用して合成するとコードが簡潔になります。
```python
base_design = design(learning_rate=0.001, batch_size=128)
conf_lr_01 = base_design + design(learning_rate=0.01)
conf_lr_1 = base_design + design(learning_rate=0.1)
```

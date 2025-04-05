# Pinjected CLI options and execution reviewer
This reviewer checks code diff and see if CLI options and execution are correctly used.
- When to trigger: pre_commit
- Return Type: approval
- Target Files: .py
- Model: anthropic/claude-3.7-sonnet:thinking
- Review scope: file_diff

# 実行方法とCLIオプション

## 基本的な実行方法

Pinjectedは、`python -m pinjected run <path.to.target>`の形式で実行します。

```bash
# run_trainを実行する例
python -m pinjected run example.run_train

# 依存関係グラフを可視化する例
python -m pinjected describe example.run_train
```

## パラメータ上書き

`--`オプションを用いて、個別のパラメータや依存項目を指定してdesignを上書きできます。

```bash
# batch_sizeとlearning_rateを上書きする例
python -m pinjected run example.run_train --batch_size=64 --learning_rate=0.0001
```

## 依存オブジェクトの差し替え

`{}`で囲んだパスを指定することで、依存オブジェクトを差し替えられます。

```bash
# modelとdatasetを差し替える例
python -m pinjected run example.run_train --model='{example.model__another}' --dataset='{example.dataset__cifar10}'
```

## overridesによるデザイン切り替え

`--overrides`オプションで、事前に定義したデザインを指定できます。

```bash
# mnist_designを使って実行する例
python -m pinjected run example.run_train --overrides={example.mnist_design}
```

## 依存関係グラフの可視化

`describe`コマンドを使用して、変数の依存関係グラフの人間が読みやすい説明を生成できます。

```bash
# 依存関係グラフを可視化する例
python -m pinjected describe example.run_train
```

このコマンドは以下を表示します：
- 依存関係のツリー構造
- 各依存関係のドキュメント
- 依存関係間の関係

これは複雑な依存関係と目的を理解するのに役立ちます。

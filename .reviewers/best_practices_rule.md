# Pinjected best practices reviewer
This reviewer checks code diff and see if best practices are followed.
- When to trigger: pre_commit
- Return Type: approval
- Target Files: .py
- Model: google/gemini-2.5-pro-preview-03-25
- Review scope: file_diff

# 実装パターンとベストプラクティス

## 依存関係の命名規則

Pinjectedでは、依存関係の命名に関して以下の規則が推奨されています：

1. **一般的な依存関係**: スネークケースで記述（例: `learning_rate`, `batch_size`）
2. **モデル関連**: `model__`プレフィックスを使用（例: `model__resnet`, `model__transformer`）
3. **データセット関連**: `dataset__`プレフィックスを使用（例: `dataset__mnist`, `dataset__cifar10`）
4. **関数型依存**: `a_`プレフィックスを使用（例: `a_process_data`, `a_transform_image`）

```python
# 命名規則に従った例
@instance
def model__resnet(input_size, hidden_units):
    return ResNet(input_size, hidden_units)

@instance
def dataset__mnist(batch_size):
    return MNISTDataset(batch_size)

@instance
def a_transform_image(image_size):
    def transform(image):
        return resize(image, (image_size, image_size))
    return transform
```

## テスト構造のベストプラクティス

1. テストファイルは`tests/test_*.py`の形式で配置する
2. テスト関数は`@injected_pytest`デコレータを使用する
3. テスト用のモックは`design()`を使って注入する

```python
# tests/test_model.py
from pinjected.test import injected_pytest
from pinjected import design

# モックデータセット
class MockDataset:
    def __len__(self):
        return 100
    def __getitem__(self, idx):
        return {"input": [0, 0, 0], "label": 0}

# テスト用デザイン
test_design = design(
    dataset=MockDataset(),
    learning_rate=0.001
)

@injected_pytest(test_design)
def test_model_forward(model, dataset):
    # modelとdatasetは依存性注入によって提供される
    sample = dataset[0]
    output = model(sample["input"])
    assert output.shape == (1, 10)  # 出力形状を検証
```

## 設計実装の考慮事項

1. **依存関係の明確化**: 各関数やクラスが必要とする依存関係を明示的に宣言する
2. **単一責任の原則**: 各プロバイダは単一の責任を持つように設計する
3. **依存関係の最小化**: 必要最小限の依存関係のみを宣言する
4. **循環依存の回避**: 循環依存を作らないよう注意する

```python
# 良い例: 依存関係が明確
@instance
def optimizer(model, learning_rate):
    return torch.optim.Adam(model.parameters(), lr=learning_rate)

# 悪い例: 依存関係が不明確
@instance
def bad_optimizer(config):
    # configの中身が不明確
    return torch.optim.Adam(config.model.parameters(), lr=config.learning_rate)
```

## 一般的な間違いと回避策

1. **グローバル変数の過剰使用**: グローバル変数ではなく、依存性注入を使用する
2. **過度に複雑な依存グラフ**: 依存関係はシンプルに保ち、必要に応じて分割する
3. **型アノテーションの欠如**: 可能な限り型アノテーションを使用して可読性を高める
4. **ドキュメントの不足**: 複雑な依存関係には適切なドキュメントを提供する

```python
# 良い例: 型アノテーションとドキュメントを含む
@instance
def model(input_size: int, hidden_units: int) -> nn.Module:
    """
    モデルを作成する関数
    
    Args:
        input_size: 入力サイズ
        hidden_units: 隠れ層のユニット数
        
    Returns:
        nn.Module: 初期化されたモデル
    """
    return Model(input_size, hidden_units)
```

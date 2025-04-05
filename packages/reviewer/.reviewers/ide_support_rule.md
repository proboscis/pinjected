# Pinjected IDE support reviewer
This reviewer checks code diff and see if IDE support features are correctly used.
- When to trigger: pre_commit
- Return Type: approval
- Target Files: .py
- Model: google/gemini-2.5-pro-preview-03-25
- Review scope: file_diff

# IDEサポート

## VSCode/PyCharmプラグイン

Pinjectedは以下のIDE機能をサポートしています：

- **ワンクリック実行**: `@injected`/`@instance`デコレータ付き関数や`IProxy`型アノテーション付き変数をワンクリックで実行可能
- **依存関係可視化**: 依存グラフをブラウザで視覚的に表示

## 実行例

```python
# IProxyアノテーションを付けると実行ボタンが表示される
check_dataset: IProxy = injected('dataset')[0]
```

## 効果的なIDEサポートのためのベストプラクティス

1. IProxyアノテーションを活用して、IDEでの型情報を明確にする：
```python
# IProxyアノテーションを使用した例
dataset_item: IProxy = injected("dataset")[0]

# さらに具体的な型情報を提供することも可能
model_output: IProxy[torch.Tensor] = model(input_data)
```

2. 複雑な依存グラフを持つ関数やクラスには、docstringで依存関係を明示する：
```python
@instance
def complex_model(dataset, optimizer, learning_rate):
    """
    複雑なモデルを作成する関数
    
    依存関係:
    - dataset: データセット
    - optimizer: 最適化アルゴリズム
    - learning_rate: 学習率
    """
    return Model(dataset, optimizer, learning_rate)
```

3. VSCodeでの実行設定例：
```json
// .vscode/launch.json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Pinjected Run",
            "type": "python",
            "request": "launch",
            "module": "pinjected",
            "args": ["run", "path.to.target", "--param=value"]
        }
    ]
}
```

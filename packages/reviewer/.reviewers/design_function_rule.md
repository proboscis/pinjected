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
    trainer=Injected.bind(Trainer)  # クラスは必ずInjected.bindでラップする
)
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

# Pinjected use cases reviewer
This reviewer checks code diff and see if use cases are implemented correctly.
- When to trigger: pre_commit
- Return Type: approval
- Target Files: .py
- Model: google/gemini-2.5-pro-preview-03-25
- Review scope: file_diff

# ユースケース例

## モデルロードと実行時パラメータ

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

## キャッシュパスや外部リソースパスの管理

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

## 設定バリエーション生成と再利用

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

## 実行時のパターン

1. モデルの一部だけを変更して再利用する場合：
```python
# 基本モデルを定義
@instance
def base_model(config):
    return BaseModel(config)

# 派生モデルを定義（base_modelを利用）
@instance
def derived_model(base_model, extra_param):
    # base_modelを再利用して拡張
    model = copy.deepcopy(base_model)
    model.add_feature(extra_param)
    return model
```

2. 条件分岐パターン：
```python
@instance
def model_factory(model_type, *args):
    if model_type == "resnet":
        return ResNetModel(*args)
    elif model_type == "transformer":
        return TransformerModel(*args)
    else:
        raise ValueError(f"Unknown model type: {model_type}")
```

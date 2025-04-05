# Pinjected dependency configuration reviewer
This reviewer checks code diff and see if dependency configuration is correctly implemented.
- When to trigger: pre_commit
- Return Type: approval
- Target Files: .py
- Model: google/gemini-2.5-pro-preview-03-25
- Review scope: file_diff

# 依存関係の設定

## 推奨: `__pinjected__.py`ファイル内の`__design__`

推奨される方法は、`__pinjected__.py`ファイル内で`__design__`変数を定義することです：

```python
# __pinjected__.py
from pinjected import design

__design__ = design(
    learning_rate=0.001,
    batch_size=128,
    # その他のデフォルト設定
)
```

## レガシー: `__meta_design__`（非推奨）

`__meta_design__`は、非推奨となっている特別なグローバル変数です。以前はCLIから実行する際のデフォルトのデザインを指定するために使用されていました：

```python
# この方法は非推奨です
__meta_design__ = design(
    overrides=mnist_design  # CLIで指定しなかったときに利用されるデザイン
)
```

## ~/.pinjected.pyによるユーザーローカル設定

`~/.pinjected.py`ファイルを通じて、ユーザーローカルなデザインを定義・注入できます。ユーザーごとに異なるパス設定や環境固有の設定を管理するのに適しています。

```python
# ~/.pinjected.py
from pinjected import design
import os

default_design = design(
    data_dir = os.path.expanduser("~/data"),
    cache_dir = "/tmp/cache"
)
```

## withステートメントによるデザインオーバーライド

`with`ステートメントを用いて、一時的なオーバーライドを行えます。

```python
from pinjected import providers, IProxy, design

with design(
        batch_size=64  # 一時的にbatch_sizeを64へ
):
    # このwithブロック内ではbatch_sizeは64として解決される
    train_with_bs_64: IProxy = train()
```

## グローバル変数の注入に関する注意点

グローバル変数（テスト用の`test_*`変数を含む）は、単にグローバルに定義しただけでは注入されません。以下の点に注意が必要です：

- グローバル変数として定義しただけでは、pinjectedの依存解決の対象にならない
- `@injected`や`@instance`でデコレートされた関数は関数名で注入されるが、グローバル変数は異なる
- グローバル変数を注入するには、`__pinjected__.py`ファイル内の`__design__`を使って明示的に注入する必要がある

```python
# 以下のように単にグローバル変数として定義しても注入されない
my_global_var = some_function(arg1="value")  # IProxyオブジェクト

# 推奨される方法: __pinjected__.pyファイル内の__design__を使用
# __pinjected__.py
from pinjected import design

__design__ = design(
    my_global_var=some_function(arg1="value")
)
```

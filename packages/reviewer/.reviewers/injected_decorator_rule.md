# Pinjected @injected decorator usage reviewer
This reviewer checks code diff and see if @instance decorator is correctly used.
- When to trigger: pre_commit
- Return Type: Approval
- Target Files: .py
- Model: google/gemini-2.5-pro-preview-03-25

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

## 2. 基本機能

### 2.2 @injectedデコレータ
DI後にintやstrではなく、関数を得たいケースはよくあります。
```python
from pinjected import instance
@instance
def generate_text(llm_model):
    def impl(prompt: str):
        return llm_model.generate(prompt)
    return impl
```
しかし、この記法は冗長であるため、@injectedデコレータが糖衣構文として用意されています。

`@injected`デコレータは、関数引数を「注入対象の引数」と「呼び出し時に指定する引数」に分離できます。`/`の左側が依存として注入され、右側が実行時に渡される引数です。
```python
from pinjected import injected

@injected
def generate_text(llm_model, /, prompt: str):
    # llm_modelはDIから注入される
    # promptは実行時に任意の値を渡せる
    return llm_model.generate(prompt)
```
これにより、先のimpl関数と等価な関数を簡潔に記述できます。

# TODO add more examples.
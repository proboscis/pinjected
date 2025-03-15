# 問題レポート: 非推奨API使用による警告

## 概要
テスト実行時に31個の警告が発生しています。これらは主に非推奨のAPI使用、型ヒントの古い書き方、および設定の不足に関するものです。

## 詳細分析

### 警告の種類
1. 非推奨API使用警告（DeprecationWarning）
   - `instances`、`providers`、`classes`関数の使用
   - これらは`design()`に置き換えるべき

2. 型ヒント関連の警告（BeartypeDecorHintPep585DeprecationWarning）
   - PEP 585で非推奨とされた型ヒントの使用
   - `typing`モジュールからではなく`beartype.typing`からのインポートが必要

3. Pydantic関連の警告
   - Pydantic V1スタイルの`@validator`が非推奨
   - Pydantic V2スタイルの`@field_validator`に移行すべき

4. Pytest関連の警告
   - 非同期テスト設定の問題
   - データクラスのテスト収集問題

### 具体的な警告例
```
DeprecationWarning: 'providers' is deprecated and will be removed in a future version. Use 'design' instead.
  ) + providers(

DeprecationWarning: 'instances' is deprecated and will be removed in a future version. Use 'design' instead.
  design += instances(

BeartypeDecorHintPep585DeprecationWarning: Function pinjected.runnables.get_runnables() return PEP 484 type hint typing.List[pinjected.module_inspector.ModuleVarSpec] deprecated by PEP 585.

PydanticDeprecatedSince20: Pydantic V1 style `@validator` validators are deprecated.
```

## 影響を受けるファイル
1. 非推奨API使用
   - `/Users/s22625/.pinjected.py`
   - `/Users/s22625/repos/pinject-design/pinjected/test/injected_pytest.py`

2. 型ヒント問題
   - `/Users/s22625/repos/pinject-design/pinjected/test_helper/test_aggregator.py`
   - `/Users/s22625/repos/pinject-design/pinjected/runnables.py`

3. Pydantic関連
   - `/Users/s22625/repos/pinject-design/pinjected/runnables.py`

4. Pytest関連
   - `/Users/s22625/repos/pinject-design/pinjected/di/partially_injected.py`
   - `/Users/s22625/repos/pinject-design/pinjected/test_helper/test_runner.py`

## 推奨される修正方法

### 1. 非推奨API使用の修正
```python
# 修正前
design += instances(...)
result = providers(...)

# 修正後
design += design(...)
result = design(...)
```

### 2. 型ヒント問題の修正
```python
# 修正前
from typing import List, Dict, Callable

# 修正後
from beartype.typing import List, Dict, Callable
```

### 3. Pydantic関連の修正
```python
# 修正前
@validator('src')
def validate_src(cls, v):
    ...

# 修正後
@field_validator('src')
def validate_src(cls, v):
    ...
```

### 4. Pytest設定の修正
- `pyproject.toml`に適切な設定を追加
- テストクラスの定義方法を修正

## 優先度
中：警告は動作に直接影響しないが、将来のバージョンで問題が発生する可能性がある。特に非推奨APIは今後削除される予定であり、早めの対応が望ましい。

## 次のステップ
1. 非推奨API使用の修正（最も優先度高）
2. 型ヒントの更新（将来のPython互換性のため）
3. Pydantic V2スタイルへの移行
4. Pytestの設定と問題のあるテストクラスの修正
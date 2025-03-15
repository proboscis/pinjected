"""
injected_pytestのインポートテスト
"""
import pytest


def test_import_injected_pytest():
    """
    pinjected.test.injected_pytestがインポートできることを確認するテスト
    """
    try:
        from pinjected.test import injected_pytest
        assert callable(injected_pytest), "injected_pytestは呼び出し可能なオブジェクトであるべきです"
    except ImportError as e:
        pytest.fail(f"インポートエラー: {e}")


def test_injected_pytest_usage():
    """
    injected_pytestが正しく動作することを確認するテスト
    """
    from pinjected.test import injected_pytest
    from pinjected import design, instances, EmptyDesign, Injected

    # テスト用のロガーモック
    class MockLogger:
        def __init__(self):
            self.logs = []

        def info(self, message):
            self.logs.append(message)

    # テスト用のデザイン
    test_design = design()
    test_design += design(
        logger=Injected.pure(MockLogger())
    )

    # injected_pytestを使用してテスト関数を作成
    @injected_pytest(test_design)
    def test_func(logger):
        logger.info("テストメッセージ")
        return "テスト成功"

    # テスト関数を実行
    result = test_func()
    
    # 結果を検証
    assert result == "テスト成功", "テスト関数の戻り値が正しくありません"
    assert test_design.provide("logger").logs == ["テストメッセージ"], "ロガーが正しく使用されていません"
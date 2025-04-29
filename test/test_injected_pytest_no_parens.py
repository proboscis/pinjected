"""
injected_pytestの括弧なし使用テスト
"""


def test_injected_pytest_no_parens_usage():
    """
    injected_pytestが括弧なしで正しく動作することを確認するテスト
    """
    from pinjected.test import injected_pytest
    
    @injected_pytest
    def test_func():
        return "テスト成功（括弧なし）"
        
    assert callable(test_func), "括弧なしのデコレータが関数を返していません"
    
    assert test_func.__name__ == "test_impl", "括弧なしのデコレータが正しく関数をラップしていません"

import pytest

def test_importability():
    """Test that the package can be imported."""
    import pinjected_error_reports
    assert pinjected_error_reports is not None
    
    # Check some key components are importable and correctly defined
    assert hasattr(pinjected_error_reports, 'ErrorAnalysis')
    assert hasattr(pinjected_error_reports, 'design_for_error_reports')
    assert hasattr(pinjected_error_reports, 'a_handle_error_with_llm_voice')
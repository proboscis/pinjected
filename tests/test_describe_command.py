import pytest
import re
from pinjected.di.design_spec.impl import SimpleBindSpec

def format_value_for_test(value):
    """Simplified version of format_value for testing."""
    if value is None:
        return "None"
    
    value_str = str(value)
    
    if isinstance(value, dict) and 'documentation' in value:
        if value['documentation']:
            doc = value['documentation']
            doc = doc.replace('\\n', '\n')
            doc = re.sub(r'[ \t]+', ' ', doc)
            value['documentation'] = doc
            value_str = str(value)
    
    return value_str

def test_format_value_handles_newlines():
    """Test that format_value properly handles newlines in documentation."""
    test_dict = {
        'type': 'SimpleBindSpec',
        'has_validator': False,
        'documentation': '\\ntype: dict\\nprotocol:\\n    - label_look_forward_ns: int\\n    - label_check_delay_ns: int\\ndescription: Configuration for labeling data.'
    }
    
    formatted = format_value_for_test(test_dict)
    
    assert '\\n' not in formatted
    assert '\ntype: dict\n' in formatted

def test_simple_bind_spec_documentation():
    """Test that SimpleBindSpec documentation is properly formatted."""
    spec = SimpleBindSpec(
        documentation="""
type: dict
protocol:
    - label_look_forward_ns: int
    - label_check_delay_ns: int
description: Configuration for labeling data.
"""
    )
    
    spec_str = str(spec)
    
    assert 'documentation' in spec_str
    
    formatted = format_value_for_test(eval(spec_str))
    
    assert '\\n' not in formatted
    assert '\ntype: dict\n' in formatted

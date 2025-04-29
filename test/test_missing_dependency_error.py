import asyncio

import pytest

from pinjected import Injected, design
from pinjected.di.graph import MissingDependencyException
from pinjected.exceptions import DependencyResolutionError, DependencyResolutionFailure
from pinjected.v2.async_resolver import AsyncResolver


def test_dependency_resolution_failure_explanation():
    """Test that DependencyResolutionFailure.explanation_str provides detailed information."""
    failure = DependencyResolutionFailure(
        key="missing_key",
        trace=["parent", "child", "missing_key"],
        cause="Key not found"
    )
    
    explanation = failure.explanation_str()
    
    assert "Failed to find dependency: missing_key" in explanation
    assert "Dependency chain: parent => child => missing_key" in explanation
    assert "Cause: Key not found" in explanation


def test_missing_dependency_exception_message():
    """Test that MissingDependencyException.create_message formats error messages properly."""
    failures = [
        DependencyResolutionFailure(
            key="key1",
            trace=["root", "dep1", "key1"],
            cause="Key not found"
        ),
        DependencyResolutionFailure(
            key="key2",
            trace=["root", "dep2", "key2"],
            cause="Key not found"
        )
    ]
    
    message = MissingDependencyException.create_message(failures)
    
    assert "========== Missing Dependencies ==========" in message
    assert "Missing Dependencies: {'key1', 'key2'}" in message or "Missing Dependencies: {'key2', 'key1'}" in message
    assert "Failure #1:" in message
    assert "Missing Key: key1" in message
    assert "Dependency Chain: root => dep1 => key1" in message
    assert "Root Cause: Key not found" in message
    assert "Failure #2:" in message
    assert "Missing Key: key2" in message
    assert "Dependency Chain: root => dep2 => key2" in message
    assert "Use the 'describe' command for more detailed dependency information" in message


def test_integration_with_resolver():
    """Test that the enhanced error messages are used in real dependency resolution failures."""
    d = design(
        x=Injected.bind(lambda z: z)  # z is not defined and doesn't create a cycle
    )
    
    with pytest.raises(DependencyResolutionError) as excinfo:
        asyncio.run(AsyncResolver(d)['x'])
    
    error_message = str(excinfo.value)
    
    assert any(pattern in error_message for pattern in ["Missing Dependencies", "Cyclic Dependencies"])
    
    if "Cyclic Dependencies" in error_message:
        assert "Cyclic Dependency:" in error_message
    else:
        assert "Trace " in error_message
        assert "Missing Dependencies:" in error_message

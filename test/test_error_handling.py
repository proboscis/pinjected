import asyncio
import pytest
from pinjected.exceptions import DependencyValidationError
from pinjected.run_helpers.run_injected import PinjectedRunFailure, a_run_with_notify

def test_validation_error_handling():
    """Test that DependencyValidationError is properly handled."""
    
    async def task(ctx):
        raise DependencyValidationError("Test validation error", None)
    
    with pytest.raises(PinjectedRunFailure):
        asyncio.run(a_run_with_notify(None, task))

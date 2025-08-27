"""Simple tests for v2/callback.py module."""

import pytest
from unittest.mock import Mock

from pinjected.v2.callback import IResolverCallback
from pinjected.v2.events import ResolverEvent


class TestIResolverCallback:
    """Test the IResolverCallback interface."""

    def test_iresolvcallback_interface(self):
        """Test that IResolverCallback is a class with __call__ method."""
        assert hasattr(IResolverCallback, "__call__")

        # Can be instantiated
        callback = IResolverCallback()
        assert callable(callback)

    def test_iresolvcallback_call_method(self):
        """Test the __call__ method signature."""
        callback = IResolverCallback()

        # Create a mock event
        mock_event = Mock(spec=ResolverEvent)

        # Call should work and return None
        result = callback(mock_event)
        assert result is None

    def test_iresolvcallback_subclass(self):
        """Test that IResolverCallback can be subclassed."""

        class MyCallback(IResolverCallback):
            def __init__(self):
                self.events = []

            def __call__(self, event: ResolverEvent):
                self.events.append(event)

        # Create instance
        my_callback = MyCallback()

        # Test it works
        mock_event1 = Mock(spec=ResolverEvent)
        mock_event2 = Mock(spec=ResolverEvent)

        my_callback(mock_event1)
        my_callback(mock_event2)

        assert len(my_callback.events) == 2
        assert my_callback.events[0] is mock_event1
        assert my_callback.events[1] is mock_event2

    def test_module_imports(self):
        """Test that the module imports correctly."""
        from pinjected.v2 import callback

        # Check ResolverEvent is imported
        assert hasattr(callback, "ResolverEvent")

        # Check IResolverCallback is defined
        assert hasattr(callback, "IResolverCallback")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

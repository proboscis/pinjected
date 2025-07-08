"""Simple tests for v2/callback.py module."""

import pytest
from unittest.mock import Mock

from pinjected.v2.callback import IResolverCallback
from pinjected.v2.events import ResolverEvent


class TestIResolverCallback:
    """Test the IResolverCallback interface."""

    def test_iresolve_callback_exists(self):
        """Test that IResolverCallback exists."""
        assert IResolverCallback is not None
        assert isinstance(IResolverCallback, type)

    def test_iresolve_callback_callable(self):
        """Test that IResolverCallback has __call__ method."""
        assert hasattr(IResolverCallback, "__call__")
        assert callable(IResolverCallback.__call__)

    def test_iresolve_callback_instantiation(self):
        """Test that IResolverCallback can be instantiated."""
        callback = IResolverCallback()
        assert callback is not None
        assert isinstance(callback, IResolverCallback)

    def test_iresolve_callback_call_with_event(self):
        """Test calling IResolverCallback with an event."""
        callback = IResolverCallback()
        mock_event = Mock(spec=ResolverEvent)

        # Should not raise an exception
        result = callback(mock_event)

        # The base implementation returns None
        assert result is None

    def test_iresolve_callback_subclass(self):
        """Test creating a subclass of IResolverCallback."""

        class MyCallback(IResolverCallback):
            def __init__(self):
                self.events = []

            def __call__(self, event: ResolverEvent):
                self.events.append(event)
                return "processed"

        # Create instance
        my_callback = MyCallback()
        assert isinstance(my_callback, IResolverCallback)

        # Test calling it
        mock_event = Mock(spec=ResolverEvent)
        result = my_callback(mock_event)

        assert result == "processed"
        assert len(my_callback.events) == 1
        assert my_callback.events[0] is mock_event

    def test_iresolve_callback_type_annotation(self):
        """Test that __call__ has proper type annotation."""
        import inspect

        # Get the signature
        sig = inspect.signature(IResolverCallback.__call__)

        # Should have 'self' and 'event' parameters
        params = list(sig.parameters.keys())
        assert "self" in params
        assert "event" in params

        # Check event parameter annotation
        event_param = sig.parameters["event"]
        assert event_param.annotation.__name__ == "ResolverEvent"

    def test_multiple_callbacks(self):
        """Test using multiple IResolverCallback instances."""
        callbacks = [IResolverCallback() for _ in range(3)]

        mock_event = Mock(spec=ResolverEvent)

        # Call all callbacks
        results = [cb(mock_event) for cb in callbacks]

        # All should return None
        assert all(r is None for r in results)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

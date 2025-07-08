"""Tests for v2/callback.py module."""

import pytest
from unittest.mock import Mock

from pinjected.v2.callback import IResolverCallback
from pinjected.v2.events import ResolverEvent


class TestIResolverCallback:
    """Tests for IResolverCallback interface."""

    def test_iresolve_callback_interface(self):
        """Test IResolverCallback interface."""

        # Create a concrete implementation
        class ConcreteCallback(IResolverCallback):
            def __init__(self):
                self.called = False
                self.event = None

            def __call__(self, event: ResolverEvent):
                self.called = True
                self.event = event

        # Create instance
        callback = ConcreteCallback()

        # Mock event
        mock_event = Mock(spec=ResolverEvent)

        # Call the callback
        callback(mock_event)

        # Verify it was called
        assert callback.called
        assert callback.event == mock_event

    def test_base_class_call(self):
        """Test base class __call__ method."""
        # Create instance of base class
        callback = IResolverCallback()

        # Mock event
        mock_event = Mock(spec=ResolverEvent)

        # Call should not raise any errors
        result = callback(mock_event)

        # Base implementation returns None
        assert result is None

    def test_multiple_callbacks(self):
        """Test using multiple callbacks."""
        callbacks = []

        # Create multiple callback implementations
        for i in range(3):

            class TestCallback(IResolverCallback):
                def __init__(self, index):
                    self.index = index
                    self.events = []

                def __call__(self, event: ResolverEvent):
                    self.events.append(event)

            callbacks.append(TestCallback(i))

        # Mock event
        mock_event = Mock(spec=ResolverEvent)

        # Call all callbacks
        for callback in callbacks:
            callback(mock_event)

        # Verify all were called
        for i, callback in enumerate(callbacks):
            assert len(callback.events) == 1
            assert callback.events[0] == mock_event
            assert callback.index == i


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

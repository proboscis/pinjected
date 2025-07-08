"""Tests for pinjected.injected_class.test_module."""

import pytest
from pinjected.injected_class.test_module import PClassExample, PClassUser


class TestPClassExample:
    """Tests for PClassExample class."""

    def test_pclass_example_attributes(self):
        """Test that PClassExample has expected attributes."""
        # Create instance with attributes
        obj = PClassExample()
        obj._dep1 = "dep1_value"
        obj._dep2 = "dep2_value"
        obj.a = "a_value"
        obj.b = 42
        obj.c = 3.14

        # Verify attributes
        assert obj._dep1 == "dep1_value"
        assert obj._dep2 == "dep2_value"
        assert obj.a == "a_value"
        assert obj.b == 42
        assert obj.c == 3.14

    def test_method(self):
        """Test _method returns tuple of a, b, c."""
        obj = PClassExample()
        obj.a = "test"
        obj.b = 123
        obj.c = 4.5

        result = obj._method()
        assert result == ("test", 123, 4.5)

    @pytest.mark.asyncio
    async def test_simple_method(self):
        """Test simple_method returns the input."""
        obj = PClassExample()

        result = await obj.simple_method("input_value")
        assert result == "input_value"

        result = await obj.simple_method(42)
        assert result == 42

    @pytest.mark.asyncio
    async def test_method_with_dep1(self):
        """Test method_with_dep1 returns dep1 and input."""
        obj = PClassExample()
        obj._dep1 = "dependency1"

        result = await obj.method_with_dep1("test_input")
        assert result == ("dependency1", "test_input")

    @pytest.mark.asyncio
    async def test_method1(self):
        """Test method1 concatenates attributes and input."""
        obj = PClassExample()
        obj.a = "A"
        obj.b = 10
        obj.c = 2.5

        result = await obj.method1("_suffix")
        # Result should be a + str(b) + str(c) + x
        expected = "A" + "10" + "2.5" + "_suffix"
        assert result == expected

    @pytest.mark.asyncio
    async def test_method1_inner_function(self):
        """Test that method1's inner function works correctly."""
        obj = PClassExample()
        obj.a = "X"
        obj.b = 99
        obj.c = 1.1

        # Call method1 which defines and uses test_inner
        result = await obj.method1("_end")

        # The inner function concatenates a, b, c
        # The method returns a + str(b) + str(c) + x
        expected = "X" + "99" + "1.1" + "_end"
        assert result == expected

    @pytest.mark.asyncio
    async def test_method2(self):
        """Test method2 performs calculation with dep1 and c."""
        obj = PClassExample()
        obj._dep1 = "AB"
        obj.c = 7.0

        result = await obj.method2(3)
        # Result should be dep1 * y + str(c)
        # "AB" * 3 + "7.0" = "ABABAB7.0"
        expected = "ABABAB" + "7.0"
        assert result == expected

    @pytest.mark.asyncio
    async def test_method2_different_values(self):
        """Test method2 with different values."""
        obj = PClassExample()
        obj._dep1 = "X"
        obj.c = 2.5

        result = await obj.method2(5)
        expected = "XXXXX" + "2.5"
        assert result == expected


class TestPClassUser:
    """Tests for PClassUser class."""

    @pytest.mark.asyncio
    async def test_do_something(self):
        """Test PClassUser.do_something calls dep.method_with_dep1."""

        # Create a mock PClassExample
        class MockPClassExample:
            def __init__(self):
                self.method_called = False
                self.method_arg = None

            async def method_with_dep1(self, x):
                self.method_called = True
                self.method_arg = x
                return "mock_result"

        # Create PClassUser with mock dependency
        user = PClassUser()
        user.dep = MockPClassExample()

        # Call do_something
        await user.do_something("test_arg")

        # Verify the dependency method was called
        assert user.dep.method_called
        assert user.dep.method_arg == "test_arg"

    def test_pclass_user_has_dep_attribute(self):
        """Test that PClassUser has dep attribute annotation."""
        # Check class annotations
        assert hasattr(PClassUser, "__annotations__")
        assert "dep" in PClassUser.__annotations__
        assert PClassUser.__annotations__["dep"] is PClassExample


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

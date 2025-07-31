"""Tests for pinjected/test_helper/test_aggregator.py module."""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import time

from pinjected.test_helper.test_aggregator import (
    check_design_variable,
    design_acceptor,
    TimeCachedFileData,
    Annotation,
    VariableInFile,
    find_pinjected_annotations,
    find_annotated_vars,
    find_run_targets,
    find_test_targets,
    PinjectedTestAggregator,
)


class TestCheckDesignVariable:
    """Tests for check_design_variable function."""

    def test_check_design_variable_with_global(self):
        """Test file with global __design__ declaration."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("""
def some_function():
    global __design__
    __design__ = "test"
""")
            f.flush()

            result = check_design_variable(f.name)
            assert result is True

            Path(f.name).unlink()

    def test_check_design_variable_with_assignment(self):
        """Test file with __design__ assignment."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("""
from pinjected import design

__design__ = design()
""")
            f.flush()

            result = check_design_variable(f.name)
            assert result is True

            Path(f.name).unlink()

    def test_check_design_variable_without_design(self):
        """Test file without __design__ variable."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("""
def regular_function():
    return "hello"
""")
            f.flush()

            result = check_design_variable(f.name)
            assert result is False

            Path(f.name).unlink()


class TestDesignAcceptor:
    """Tests for design_acceptor function."""

    def test_design_acceptor_with_design_py_file(self):
        """Test accepting .py file with __design__."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("__design__ = 'test'")
            f.flush()

            result = design_acceptor(Path(f.name))
            assert result is True

            Path(f.name).unlink()

    def test_design_acceptor_non_py_file(self):
        """Test rejecting non-.py file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("__design__ = 'test'")
            f.flush()

            result = design_acceptor(Path(f.name))
            assert result is False

            Path(f.name).unlink()

    def test_design_acceptor_py_file_without_design(self):
        """Test rejecting .py file without __design__."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("regular_code = 'test'")
            f.flush()

            result = design_acceptor(Path(f.name))
            assert result is False

            Path(f.name).unlink()


class TestTimeCachedFileData:
    """Tests for TimeCachedFileData class."""

    def test_get_cache_creates_directory(self):
        """Test that get_cache creates cache directory if needed."""
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_path = Path(temp_dir) / "subdir" / "cache.db"

            def dummy_processor(path):
                return "processed"

            cached_data = TimeCachedFileData(
                cache_path=cache_path, file_to_data=dummy_processor
            )

            with cached_data.get_cache() as cache:
                assert cache is not None

            assert cache_path.parent.exists()

    def test_get_data_fresh_file(self):
        """Test get_data with fresh file (not in cache)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_path = Path(temp_dir) / "cache.db"
            test_file = Path(temp_dir) / "test.txt"
            test_file.write_text("content")

            mock_processor = Mock(return_value="processed_data")

            cached_data = TimeCachedFileData(
                cache_path=cache_path, file_to_data=mock_processor
            )

            result = cached_data.get_data(test_file)

            assert result == "processed_data"
            mock_processor.assert_called_once_with(test_file)

    def test_get_data_cached_file(self):
        """Test get_data returns cached data for unchanged file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_path = Path(temp_dir) / "cache.db"
            test_file = Path(temp_dir) / "test.txt"
            test_file.write_text("content")

            mock_processor = Mock(side_effect=["first_call", "second_call"])

            cached_data = TimeCachedFileData(
                cache_path=cache_path, file_to_data=mock_processor
            )

            # First call - should process
            result1 = cached_data.get_data(test_file)
            assert result1 == "first_call"

            # Second call - should use cache
            result2 = cached_data.get_data(test_file)
            assert result2 == "first_call"

            # Processor should only be called once
            assert mock_processor.call_count == 1

    def test_get_data_updated_file(self):
        """Test get_data reprocesses file when it's updated."""
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_path = Path(temp_dir) / "cache.db"
            test_file = Path(temp_dir) / "test.txt"
            test_file.write_text("content")

            mock_processor = Mock(side_effect=["first_call", "second_call"])

            cached_data = TimeCachedFileData(
                cache_path=cache_path, file_to_data=mock_processor
            )

            # First call
            result1 = cached_data.get_data(test_file)
            assert result1 == "first_call"

            # Update file (change modification time)
            time.sleep(0.01)  # Ensure different timestamp
            test_file.write_text("new content")

            # Second call - should reprocess
            result2 = cached_data.get_data(test_file)
            assert result2 == "second_call"

            assert mock_processor.call_count == 2

    def test_get_data_cache_error(self):
        """Test get_data handles cache errors gracefully."""
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_path = Path(temp_dir) / "cache.db"
            test_file = Path(temp_dir) / "test.txt"
            test_file.write_text("content")

            mock_processor = Mock(return_value="processed_data")

            cached_data = TimeCachedFileData(
                cache_path=cache_path, file_to_data=mock_processor
            )

            # Mock shelve to raise an exception when getting data
            with patch("shelve.open") as mock_shelve:
                mock_cache = MagicMock()
                mock_cache.__enter__.return_value = mock_cache
                mock_cache.get.side_effect = Exception("Cache error")
                mock_shelve.return_value = mock_cache

                result = cached_data.get_data(test_file)

                assert result == "processed_data"
                mock_processor.assert_called_once_with(test_file)


class TestAnnotation:
    """Tests for Annotation dataclass."""

    def test_annotation_creation(self):
        """Test creating Annotation instances."""
        ann = Annotation(name="test_func", value="@injected")
        assert ann.name == "test_func"
        assert ann.value == "@injected"


class TestVariableInFile:
    """Tests for VariableInFile class."""

    def test_variable_in_file_creation(self):
        """Test creating VariableInFile instance."""
        path = Path("/test/path/module.py")
        var = VariableInFile(file_path=path, name="my_var")
        assert var.file_path == path
        assert var.name == "my_var"

    @patch("pinjected.test_helper.test_aggregator.get_project_root")
    @patch("pinjected.test_helper.test_aggregator.get_module_path")
    def test_to_module_var_path(self, mock_get_module_path, mock_get_project_root):
        """Test converting to ModuleVarPath."""
        mock_get_project_root.return_value = "/project/root"
        mock_get_module_path.return_value = "src.package.module"

        path = Path("/project/root/src/package/module.py")
        var = VariableInFile(file_path=path, name="my_var")

        result = var.to_module_var_path()

        assert result.path == "package.module.my_var"
        mock_get_project_root.assert_called_once_with(str(path))
        mock_get_module_path.assert_called_once_with("/project/root", path)


class TestFindPinjectedAnnotations:
    """Tests for find_pinjected_annotations function."""

    def test_find_injected_decorator(self):
        """Test finding @injected decorator."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("""
@injected
def my_function():
    pass
""")
            f.flush()

            results = find_pinjected_annotations(f.name)

            assert len(results) == 1
            assert results[0].name == "my_function"
            assert results[0].value == "@injected"

            Path(f.name).unlink()

    def test_find_instance_decorator(self):
        """Test finding @instance decorator."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("""
@instance
def my_instance():
    return "value"
""")
            f.flush()

            results = find_pinjected_annotations(f.name)

            assert len(results) == 1
            assert results[0].name == "my_instance"
            assert results[0].value == "@instance"

            Path(f.name).unlink()

    def test_find_injected_annotation(self):
        """Test finding :Injected type annotation."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("""
my_var: Injected = injected("dependency")
""")
            f.flush()

            results = find_pinjected_annotations(f.name)

            assert len(results) == 1
            assert results[0].name == "my_var"
            assert results[0].value == ":Injected"

            Path(f.name).unlink()

    def test_find_iproxy_annotation(self):
        """Test finding :IProxy type annotation."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("""
proxy_var: IProxy = IProxy()
""")
            f.flush()

            results = find_pinjected_annotations(f.name)

            assert len(results) == 1
            assert results[0].name == "proxy_var"
            assert results[0].value == ":IProxy"

            Path(f.name).unlink()

    def test_find_type_comment(self):
        """Test finding type comments."""
        # Note: type comments need type_comments=True in ast.parse
        # and the current implementation doesn't use it, so this test
        # verifies the current behavior (no results)
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("""
my_var = injected("dep")  # type: Injected
""")
            f.flush()

            results = find_pinjected_annotations(f.name)

            # Current implementation doesn't parse type comments
            assert len(results) == 0

            Path(f.name).unlink()

    def test_find_async_function(self):
        """Test finding async function with decorator."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("""
@injected
async def async_func():
    pass
""")
            f.flush()

            results = find_pinjected_annotations(f.name)

            assert len(results) == 1
            assert results[0].name == "async_func"
            assert results[0].value == "@injected"

            Path(f.name).unlink()

    def test_find_class_decorator(self):
        """Test finding class with decorator."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("""
@injected
class MyClass:
    pass
""")
            f.flush()

            results = find_pinjected_annotations(f.name)

            assert len(results) == 1
            assert results[0].name == "MyClass"
            assert results[0].value == "@injected"

            Path(f.name).unlink()

    def test_find_multiple_annotations(self):
        """Test finding multiple annotations in one file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("""
@injected
def func1():
    pass

@instance
def func2():
    pass

var1: Injected = injected("dep1")
var2: IProxy = IProxy()
""")
            f.flush()

            results = find_pinjected_annotations(f.name)

            assert len(results) == 4
            names = [r.name for r in results]
            values = [r.value for r in results]

            assert "func1" in names
            assert "func2" in names
            assert "var1" in names
            assert "var2" in names

            assert "@injected" in values
            assert "@instance" in values
            assert ":Injected" in values
            assert ":IProxy" in values

            Path(f.name).unlink()


class TestFindAnnotatedVars:
    """Tests for find_annotated_vars function."""

    def test_find_annotated_vars(self):
        """Test finding annotated variables."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("""
@injected
def my_func():
    pass

var: Injected = injected("dep")
""")
            f.flush()

            path = Path(f.name)
            results = find_annotated_vars(path)

            assert len(results) == 2
            assert all(isinstance(r, VariableInFile) for r in results)
            assert results[0].file_path == path
            assert results[0].name == "my_func"
            assert results[1].name == "var"

            path.unlink()


class TestFindRunTargets:
    """Tests for find_run_targets function."""

    def test_find_run_targets_with_design(self):
        """Test finding run targets in file with __design__."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("""
__design__ = design()

@injected
def run_me():
    pass
""")
            f.flush()

            path = Path(f.name)
            results = find_run_targets(path)

            assert len(results) == 1
            assert results[0].name == "run_me"

            path.unlink()

    def test_find_run_targets_without_design(self):
        """Test finding run targets in file without __design__."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("""
@injected
def run_me():
    pass
""")
            f.flush()

            path = Path(f.name)
            results = find_run_targets(path)

            assert len(results) == 0

            path.unlink()


class TestFindTestTargets:
    """Tests for find_test_targets function."""

    def test_find_test_targets(self):
        """Test finding test targets (starting with test_)."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("""
__design__ = design()

@injected
def test_something():
    pass

@injected
def run_something():
    pass
""")
            f.flush()

            path = Path(f.name)
            results = find_test_targets(path)

            assert len(results) == 1
            assert results[0].name == "test_something"

            path.unlink()


class TestPinjectedTestAggregator:
    """Tests for PinjectedTestAggregator class."""

    def test_gather_from_file(self):
        """Test gathering from a single file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("""
__design__ = design()

@injected
def test_func():
    pass
""")
            f.flush()

            path = Path(f.name)

            # Create aggregator with temp cache
            with tempfile.TemporaryDirectory() as temp_dir:
                cache_path = Path(temp_dir) / "test_cache.db"
                aggregator = PinjectedTestAggregator()
                aggregator.cached_data.cache_path = cache_path

                results = aggregator.gather_from_file(path)

                assert len(results) == 1
                assert results[0].name == "test_func"

            path.unlink()

    @patch("pinjected.test_helper.test_aggregator.logger")
    def test_gather_from_directory(self, mock_logger):
        """Test gathering from a directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test files
            file1 = Path(temp_dir) / "test1.py"
            file1.write_text("""
__design__ = design()

@injected
def test_one():
    pass
""")

            file2 = Path(temp_dir) / "test2.py"
            file2.write_text("""
__design__ = design()

@injected
def test_two():
    pass
""")

            # File without __design__
            file3 = Path(temp_dir) / "test3.py"
            file3.write_text("""
@injected
def test_three():
    pass
""")

            # Create aggregator with temp cache
            cache_path = Path(temp_dir) / "test_cache.db"
            aggregator = PinjectedTestAggregator()
            aggregator.cached_data.cache_path = cache_path

            results = aggregator.gather(Path(temp_dir))

            assert len(results) == 2
            names = [r.name for r in results]
            assert "test_one" in names
            assert "test_two" in names
            assert "test_three" not in names

    @patch("pinjected.test_helper.test_aggregator.logger")
    def test_gather_from_file_path(self, mock_logger):
        """Test gathering when given a file path (uses parent dir)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            file1 = Path(temp_dir) / "test.py"
            file1.write_text("""
__design__ = design()

@injected
def test_func():
    pass
""")

            # Create aggregator with temp cache
            cache_path = Path(temp_dir) / "test_cache.db"
            aggregator = PinjectedTestAggregator()
            aggregator.cached_data.cache_path = cache_path

            # Pass file path instead of directory
            results = aggregator.gather(file1)

            assert len(results) == 1
            assert results[0].name == "test_func"

    @patch("pinjected.test_helper.test_aggregator.logger")
    def test_gather_with_error(self, mock_logger):
        """Test gathering handles errors gracefully."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a file that will cause an error
            bad_file = Path(temp_dir) / "bad.py"
            bad_file.write_text("invalid python syntax {{{")

            # Create aggregator with temp cache
            cache_path = Path(temp_dir) / "test_cache.db"
            aggregator = PinjectedTestAggregator()
            aggregator.cached_data.cache_path = cache_path

            # Should not raise, just log warning
            results = aggregator.gather(Path(temp_dir))

            assert len(results) == 0
            # Check that warning was logged
            assert any(
                "error while checking" in str(call)
                for call in mock_logger.warning.call_args_list
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

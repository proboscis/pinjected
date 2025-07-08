"""Tests for the CLI module."""

import json
from pathlib import Path

from click.testing import CliRunner

from pinjected_linter.cli import collect_python_files, load_config, main


class TestCLI:
    """Test CLI command."""

    def test_help(self):
        """Test help output."""
        runner = CliRunner()
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "Pinjected linter" in result.output
        assert "--output-format" in result.output

    def test_no_files_found(self, tmp_path):
        """Test when no Python files are found."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(main, [str(tmp_path)])
            assert result.exit_code == 0
            # No output since logger is suppressed by default

    def test_single_file(self, tmp_path):
        """Test analyzing a single file."""
        # Create a test file
        test_file = tmp_path / "test.py"
        test_file.write_text("# Test file\nprint('hello')\n")

        runner = CliRunner()
        result = runner.invoke(main, [str(test_file)])
        assert result.exit_code == 0
        assert "✓ No issues found!" in result.output

    def test_directory(self, tmp_path):
        """Test analyzing a directory."""
        # Create test files
        (tmp_path / "test1.py").write_text("# Test 1")
        (tmp_path / "test2.py").write_text("# Test 2")
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (subdir / "test3.py").write_text("# Test 3")

        runner = CliRunner()
        result = runner.invoke(main, [str(tmp_path)])
        assert result.exit_code == 0
        assert "✓ No issues found!" in result.output

    def test_with_violations(self, tmp_path):
        """Test with violations found."""
        test_file = tmp_path / "test.py"
        test_file.write_text("""
from pinjected import instance

@instance
def get_database():
    return "db"
""")

        runner = CliRunner()
        result = runner.invoke(main, [str(test_file)])
        assert result.exit_code == 1  # Exit with error due to violations
        assert "PINJ001" in result.output
        assert "get_database" in result.output

    def test_json_output(self, tmp_path):
        """Test JSON output format."""
        test_file = tmp_path / "test.py"
        test_file.write_text("""
from pinjected import instance

@instance
def get_database():
    return "db"
""")

        runner = CliRunner()
        result = runner.invoke(main, [str(test_file), "-f", "json"])
        assert result.exit_code == 1

        # Parse JSON output
        output_data = json.loads(result.output)
        assert "violations" in output_data
        assert len(output_data["violations"]) > 0
        assert output_data["violations"][0]["rule_id"] == "PINJ001"

    def test_github_output(self, tmp_path):
        """Test GitHub Actions output format."""
        test_file = tmp_path / "test.py"
        test_file.write_text("""
from pinjected import instance

@instance
def get_database():
    return "db"
""")

        runner = CliRunner()
        result = runner.invoke(main, [str(test_file), "-f", "github"])
        assert result.exit_code == 1
        assert "::error file=" in result.output
        assert "PINJ001" in result.output

    def test_disable_rule(self, tmp_path):
        """Test disabling a specific rule."""
        test_file = tmp_path / "test.py"
        test_file.write_text("""
from pinjected import instance

@instance
def get_database():
    return "db"
""")

        runner = CliRunner()
        result = runner.invoke(main, [str(test_file), "-d", "PINJ001"])
        assert result.exit_code == 0
        assert "✓ No issues found!" in result.output

    def test_enable_only_specific_rule(self, tmp_path):
        """Test enabling only specific rules."""
        test_file = tmp_path / "test.py"
        test_file.write_text("""
from pinjected import instance

@instance
def get_database():
    return "db"
""")

        runner = CliRunner()
        result = runner.invoke(main, [str(test_file), "-e", "PINJ002"])
        assert result.exit_code == 0
        assert "✓ No issues found!" in result.output

    def test_severity_filter(self, tmp_path):
        """Test severity filtering."""
        test_file = tmp_path / "test.py"
        test_file.write_text("""
from pinjected import instance

@instance
def database():
    return "db"
""")

        runner = CliRunner()
        # This should find no violations as there are no errors
        result = runner.invoke(main, [str(test_file), "-s", "error"])
        assert result.exit_code == 0
        assert "✓ No issues found!" in result.output

    def test_no_show_source(self, tmp_path):
        """Test hiding source in output."""
        test_file = tmp_path / "test.py"
        test_file.write_text("""
from pinjected import instance

@instance
def get_database():
    return "db"
""")

        runner = CliRunner()
        result = runner.invoke(main, [str(test_file), "--no-show-source"])
        assert result.exit_code == 1
        assert "def get_database():" not in result.output  # Source line not shown
        assert "PINJ001" in result.output  # But violation is shown

    def test_verbose_mode(self, tmp_path):
        """Test verbose logging."""
        test_file = tmp_path / "test.py"
        test_file.write_text("# Test file")

        runner = CliRunner()
        result = runner.invoke(main, [str(test_file), "-v"])
        assert result.exit_code == 0
        assert "Starting Pinjected linter" in result.output
        assert "Found 1 Python files to analyze" in result.output
        assert "Analyzing files..." in result.output

    def test_config_file(self, tmp_path):
        """Test loading configuration from file."""
        config_file = tmp_path / ".pinjected-dynamic-linter.toml"
        config_file.write_text("""
disable = ["PINJ001"]
""")

        test_file = tmp_path / "test.py"
        test_file.write_text("""
from pinjected import instance

@instance
def get_database():
    return "db"
""")

        runner = CliRunner()
        result = runner.invoke(main, [str(test_file), "-c", str(config_file)])
        assert result.exit_code == 0
        assert "✓ No issues found!" in result.output

    def test_exclude_config_from_file(self, tmp_path):
        """Test exclusion configuration from config file."""
        # Create config file with exclude patterns
        config_file = tmp_path / ".pinjected-dynamic-linter.toml"
        config_file.write_text("""
exclude = ["**/excluded/**", "temp_*.py"]
""")

        # Create test files
        good_file = tmp_path / "good.py"
        good_file.write_text("""
from pinjected import instance

@instance
def get_database():
    return "db"
""")

        # This should be excluded
        temp_file = tmp_path / "temp_test.py"
        temp_file.write_text("""
from pinjected import instance

@instance
def get_database():
    return "db"
""")

        # Create excluded directory
        excluded_dir = tmp_path / "excluded"
        excluded_dir.mkdir()
        excluded_file = excluded_dir / "excluded.py"
        excluded_file.write_text("""
from pinjected import instance

@instance
def get_database():
    return "db"
""")

        runner = CliRunner()
        # Change to tmp_path directory
        import os
        old_cwd = os.getcwd()
        try:
            os.chdir(str(tmp_path))

            result = runner.invoke(main, ["-v"])

            # Should only find violations in good.py, not in excluded files
            assert "good.py" in result.output
            assert "temp_test.py" not in result.output
            assert "excluded.py" not in result.output
            assert "Found 1 Python files to analyze" in result.output
        finally:
            os.chdir(old_cwd)

    def test_exclude_config_from_pyproject(self, tmp_path):
        """Test exclusion configuration from pyproject.toml."""
        # Create pyproject.toml with pinjected-linter config
        pyproject_file = tmp_path / "pyproject.toml"
        pyproject_file.write_text("""
[tool.pinjected-dynamic-linter]
exclude = ["**/ignore/**", "skip_*.py"]
""")

        # Create test files
        good_file = tmp_path / "analyze.py"
        good_file.write_text("""
from pinjected import instance

@instance
def database():
    return "db"
""")

        # This should be excluded
        skip_file = tmp_path / "skip_this.py"
        skip_file.write_text("""
from pinjected import instance

@instance
def get_database():
    return "db"
""")

        # Create ignore directory
        ignore_dir = tmp_path / "ignore"
        ignore_dir.mkdir()
        ignore_file = ignore_dir / "ignored.py"
        ignore_file.write_text("""
from pinjected import instance

@instance
def get_database():
    return "db"
""")

        runner = CliRunner()
        # Change to tmp_path directory
        import os
        old_cwd = os.getcwd()
        try:
            os.chdir(str(tmp_path))

            result = runner.invoke(main, ["-v"])

            # Should only find one file (analyze.py)
            assert "Found 1 Python files to analyze" in result.output
            # The excluded files should not cause any violations to be reported
            assert "skip_this.py" not in result.output
            assert "ignored.py" not in result.output
            assert "✓ No issues found!" in result.output
        finally:
            os.chdir(old_cwd)

    def test_no_parallel(self, tmp_path):
        """Test disabling parallel processing."""
        test_file = tmp_path / "test.py"
        test_file.write_text("# Test file")

        runner = CliRunner()
        result = runner.invoke(main, [str(test_file), "--no-parallel"])
        assert result.exit_code == 0
        assert "✓ No issues found!" in result.output

    def test_no_color(self, tmp_path):
        """Test disabling colored output."""
        test_file = tmp_path / "test.py"
        test_file.write_text("""
from pinjected import instance

@instance
def get_database():
    return "db"
""")

        runner = CliRunner()
        result = runner.invoke(main, [str(test_file), "--no-color"])
        assert result.exit_code == 1
        # Output should not contain color codes
        assert "[red]" not in result.output
        assert "[bold]" not in result.output

    def test_current_directory_default(self):
        """Test that current directory is used when no paths provided."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            # Create a test file in current directory
            Path("test.py").write_text("# Test file")

            result = runner.invoke(main, [])
            assert result.exit_code == 0
            assert "✓ No issues found!" in result.output


class TestCollectPythonFiles:
    """Test collect_python_files function."""

    def test_single_file(self, tmp_path):
        """Test collecting a single Python file."""
        test_file = tmp_path / "test.py"
        test_file.write_text("# Test")

        files = collect_python_files([str(test_file)])
        assert len(files) == 1
        assert files[0] == test_file

    def test_directory(self, tmp_path):
        """Test collecting from directory."""
        (tmp_path / "test1.py").write_text("# Test 1")
        (tmp_path / "test2.py").write_text("# Test 2")
        (tmp_path / "not_python.txt").write_text("Not Python")

        files = collect_python_files([str(tmp_path)])
        assert len(files) == 2
        assert all(f.suffix == ".py" for f in files)

    def test_recursive(self, tmp_path):
        """Test recursive collection."""
        (tmp_path / "test1.py").write_text("# Test 1")
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (subdir / "test2.py").write_text("# Test 2")

        files = collect_python_files([str(tmp_path)])
        assert len(files) == 2

    def test_ignore_directories(self, tmp_path):
        """Test ignoring common directories."""
        (tmp_path / "test.py").write_text("# Test")

        # Create ignored directories
        for ignored in [".venv", "venv", "__pycache__", ".git", "build", "dist"]:
            ignored_dir = tmp_path / ignored
            ignored_dir.mkdir()
            (ignored_dir / "ignored.py").write_text("# Ignored")

        files = collect_python_files([str(tmp_path)])
        assert len(files) == 1
        assert files[0].name == "test.py"

    def test_multiple_paths(self, tmp_path):
        """Test multiple input paths."""
        file1 = tmp_path / "file1.py"
        file1.write_text("# File 1")

        dir2 = tmp_path / "dir2"
        dir2.mkdir()
        (dir2 / "file2.py").write_text("# File 2")

        files = collect_python_files([str(file1), str(dir2)])
        assert len(files) == 2

    def test_deduplication(self, tmp_path):
        """Test that files are deduplicated."""
        test_file = tmp_path / "test.py"
        test_file.write_text("# Test")

        # Pass same file multiple times
        files = collect_python_files([str(test_file), str(test_file), str(tmp_path)])
        assert len(files) == 1

    def test_exclude_patterns(self, tmp_path):
        """Test exclusion patterns."""
        # Create test files
        (tmp_path / "test.py").write_text("# Test")
        (tmp_path / "exclude_me.py").write_text("# Exclude")

        excluded_dir = tmp_path / "excluded"
        excluded_dir.mkdir()
        (excluded_dir / "file.py").write_text("# Excluded")

        test_dir = tmp_path / "tests"
        test_dir.mkdir()
        (test_dir / "test_file.py").write_text("# Test file")

        # Change to tmp_path as working directory to make paths relative
        import os
        old_cwd = os.getcwd()
        try:
            os.chdir(str(tmp_path))

            # Test with exclude patterns
            files = collect_python_files(
                ["."],
                exclude_patterns=["exclude_me.py", "excluded/*", "**/tests/**"]
            )
            assert len(files) == 1
            assert files[0].name == "test.py"
        finally:
            os.chdir(old_cwd)

    def test_exclude_patterns_glob(self, tmp_path):
        """Test glob patterns in exclusions."""
        # Create test files
        (tmp_path / "good.py").write_text("# Good")
        (tmp_path / "test_bad.py").write_text("# Bad")
        (tmp_path / "bad_test.py").write_text("# Bad")

        subdir = tmp_path / "src"
        subdir.mkdir()
        (subdir / "test_file.py").write_text("# Test")
        (subdir / "file_test.py").write_text("# Test")

        # Change to tmp_path as working directory
        import os
        old_cwd = os.getcwd()
        try:
            os.chdir(str(tmp_path))

            # Exclude files with "test" in name
            files = collect_python_files(
                ["."],
                exclude_patterns=["*test*"]
            )
            assert len(files) == 1
            assert files[0].name == "good.py"
        finally:
            os.chdir(old_cwd)

    def test_exclude_tmp_directory(self, tmp_path):
        """Test excluding tmp directory patterns."""
        # Create test files
        (tmp_path / "good.py").write_text("# Good file")

        # Create tmp directory with files
        tmp_dir = tmp_path / "tmp"
        tmp_dir.mkdir()
        (tmp_dir / "temp_test.py").write_text("# Should be excluded")
        (tmp_dir / "another_test.py").write_text("# Also excluded")

        # Create nested tmp directory
        nested = tmp_path / "src" / "tmp"
        nested.mkdir(parents=True)
        (nested / "nested_test.py").write_text("# Nested excluded")

        # Change to tmp_path as working directory
        import os
        old_cwd = os.getcwd()
        try:
            os.chdir(str(tmp_path))

            # Test various tmp exclusion patterns
            files = collect_python_files(
                ["."],
                exclude_patterns=["tmp", "tmp/", "./tmp/", "**/tmp/**"]
            )
            # Should only find good.py
            assert len(files) == 1
            assert files[0].name == "good.py"
        finally:
            os.chdir(old_cwd)


class TestLoadConfig:
    """Test load_config function."""

    def test_valid_toml(self, tmp_path):
        """Test loading valid TOML config."""
        config_file = tmp_path / "config.toml"
        config_file.write_text("""
disable = ["PINJ001", "PINJ002"]

[rules.PINJ003]
some_option = true
""")

        config = load_config(str(config_file))
        assert config["disable"] == ["PINJ001", "PINJ002"]
        assert config["rules"]["PINJ003"]["some_option"] is True

    def test_missing_file(self, tmp_path):
        """Test loading non-existent file."""
        config = load_config(str(tmp_path / "nonexistent.toml"))
        assert config == {}

    def test_invalid_toml(self, tmp_path):
        """Test loading invalid TOML."""
        config_file = tmp_path / "invalid.toml"
        config_file.write_text("invalid toml content [[[")

        config = load_config(str(config_file))
        assert config == {}

    def test_empty_file(self, tmp_path):
        """Test loading empty TOML file."""
        config_file = tmp_path / "empty.toml"
        config_file.write_text("")

        config = load_config(str(config_file))
        assert config == {}

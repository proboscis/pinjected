"""Test the CLI documentation features."""

import pytest
from click.testing import CliRunner

from pinjected_linter.cli import main, show_rule_documentation


class TestCLIDocumentation:
    """Test CLI documentation features."""

    def test_show_rule_doc_option(self):
        """Test --show-rule-doc option with valid rule."""
        runner = CliRunner()
        result = runner.invoke(main, ["--show-rule-doc", "PINJ001"])

        assert result.exit_code == 0
        assert "PINJ001: Instance Naming" in result.output
        assert "Overview" in result.output
        assert "Rationale" in result.output
        assert "Examples of Violations" in result.output

    def test_show_rule_doc_lowercase(self):
        """Test --show-rule-doc option with lowercase rule ID."""
        runner = CliRunner()
        result = runner.invoke(main, ["--show-rule-doc", "pinj001"])

        assert result.exit_code == 0
        assert "PINJ001: Instance Naming" in result.output

    def test_show_rule_doc_invalid_rule(self):
        """Test --show-rule-doc option with invalid rule."""
        runner = CliRunner()
        result = runner.invoke(main, ["--show-rule-doc", "PINJ999"])

        assert result.exit_code == 1
        assert "Error: No documentation found for rule PINJ999" in result.output
        assert "Use --show-config-docs to see available rules" in result.output

    def test_show_config_docs_still_works(self):
        """Test that --show-config-docs still works."""
        runner = CliRunner()
        result = runner.invoke(main, ["--show-config-docs"])

        assert result.exit_code == 0
        assert "Pinjected Linter Configuration Documentation" in result.output
        assert "Available Rules:" in result.output

    def test_linter_output_includes_help_message(self, tmp_path):
        """Test that linter output includes help message about --show-rule-doc."""
        # Create a test file with a violation
        test_file = tmp_path / "test_violations.py"
        test_file.write_text("""
from pinjected.di.decorators import instance

@instance
def get_database():  # This violates PINJ001
    return "db"
""")

        runner = CliRunner()
        result = runner.invoke(main, [str(test_file)])

        # Check that help message is included
        assert (
            "Use --show-rule-doc <RULE_ID> for detailed rule information and examples"
            in result.output
        )
        assert (
            "Example: pinjected-dynamic-linter --show-rule-doc PINJ001" in result.output
        )


class TestShowRuleDocumentationFunction:
    """Test the show_rule_documentation function directly."""

    def test_show_rule_documentation_valid(self, capsys):
        """Test show_rule_documentation with valid rule."""
        with pytest.raises(SystemExit) as excinfo:
            show_rule_documentation("PINJ001")

        # Should exit successfully
        assert excinfo.value.code == 0

        captured = capsys.readouterr()
        assert "PINJ001: Instance Naming" in captured.out

    def test_show_rule_documentation_invalid(self, capsys):
        """Test show_rule_documentation with invalid rule."""
        with pytest.raises(SystemExit) as excinfo:
            show_rule_documentation("INVALID")

        # Should exit with error
        assert excinfo.value.code == 1

        captured = capsys.readouterr()
        assert "Error: No documentation found for rule INVALID" in captured.err

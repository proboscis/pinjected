"""Integration tests that run the linter on actual example files."""

from pathlib import Path
import pytest
from pinjected_linter.analyzer import PinjectedAnalyzer
from pinjected_linter.reporter import Reporter, TerminalFormatter


def test_lint_bad_instance_file():
    """Test linting a file with instance violations."""
    analyzer = PinjectedAnalyzer()
    bad_file = Path(__file__).parent / "fixtures" / "bad" / "instance_violations.py"
    
    violations = analyzer.analyze_file(bad_file)
    
    # Group violations by rule
    by_rule = {}
    for v in violations:
        by_rule.setdefault(v.rule_id, []).append(v)
    
    # Check we found the expected violations
    assert "PINJ001" in by_rule  # Verb naming
    assert len(by_rule["PINJ001"]) >= 3  # get_database, create_connection, setup_cache
    
    assert "PINJ002" in by_rule  # Default arguments
    assert len(by_rule["PINJ002"]) >= 2  # redis_client, logger
    
    assert "PINJ003" in by_rule  # Async with a_ prefix
    assert len(by_rule["PINJ003"]) >= 2  # a_database_connection, a_message_queue
    
    assert "PINJ004" in by_rule  # Direct calls
    assert len(by_rule["PINJ004"]) >= 5  # Multiple direct calls
    
    # Print report for debugging
    reporter = Reporter(output_format="terminal", color=False)
    print("\nViolations found in instance_violations.py:")
    print(reporter.report(violations))


def test_lint_bad_injected_file():
    """Test linting a file with injected violations."""
    analyzer = PinjectedAnalyzer()
    bad_file = Path(__file__).parent / "fixtures" / "bad" / "injected_violations.py"
    
    violations = analyzer.analyze_file(bad_file)
    
    # Group violations by rule
    by_rule = {}
    for v in violations:
        by_rule.setdefault(v.rule_id, []).append(v)
    
    # Check we found the expected violations
    assert "PINJ008" in by_rule  # Undeclared dependencies
    assert len(by_rule["PINJ008"]) >= 4  # Multiple undeclared calls
    
    # PINJ015 should trigger for functions with args but no slash
    if "PINJ015" in by_rule:
        # Check that it's flagging the right functions
        flagged_funcs = [v.message for v in by_rule["PINJ015"]]
        print("\nPINJ015 warnings (missing slash means NO dependency injection):")
        for msg in flagged_funcs:
            print(f"  - {msg}")


def test_lint_good_file():
    """Test linting a file with correct patterns."""
    analyzer = PinjectedAnalyzer()
    good_file = Path(__file__).parent / "fixtures" / "good" / "correct_patterns.py"
    
    violations = analyzer.analyze_file(good_file)
    
    # Should have no violations
    if violations:
        reporter = Reporter(output_format="terminal", color=False)
        print("\nUnexpected violations in correct_patterns.py:")
        print(reporter.report(violations))
        
    assert len(violations) == 0, "Good code should not have violations"


def test_reporter_formats():
    """Test different output formats."""
    analyzer = PinjectedAnalyzer()
    bad_file = Path(__file__).parent / "fixtures" / "bad" / "instance_violations.py"
    
    violations = analyzer.analyze_file(bad_file)
    assert len(violations) > 0
    
    # Test terminal format
    terminal_reporter = Reporter(output_format="terminal", color=False)
    terminal_output = terminal_reporter.report(violations)
    assert "PINJ001" in terminal_output
    assert "PINJ002" in terminal_output
    
    # Test JSON format
    json_reporter = Reporter(output_format="json")
    json_output = json_reporter.report(violations)
    assert '"rule_id"' in json_output
    assert '"violations"' in json_output
    
    # Test GitHub format
    github_reporter = Reporter(output_format="github")
    github_output = github_reporter.report(violations)
    assert "::error" in github_output or "::warning" in github_output


def test_analyzer_with_config():
    """Test analyzer with custom configuration."""
    # Disable specific rules
    config = {
        "disable": ["PINJ015"],  # Disable slash warning
    }
    
    analyzer = PinjectedAnalyzer(config=config)
    bad_file = Path(__file__).parent / "fixtures" / "bad" / "injected_violations.py"
    
    violations = analyzer.analyze_file(bad_file)
    
    # Should not have PINJ015 violations
    rule_ids = {v.rule_id for v in violations}
    assert "PINJ015" not in rule_ids
    assert "PINJ008" in rule_ids  # Other rules still work


if __name__ == "__main__":
    # Run tests manually for debugging
    test_lint_bad_instance_file()
    print("\n" + "="*60 + "\n")
    test_lint_bad_injected_file()
    print("\n" + "="*60 + "\n")
    test_lint_good_file()
    print("\n" + "="*60 + "\n")
    test_reporter_formats()
    print("\nAll integration tests completed!")
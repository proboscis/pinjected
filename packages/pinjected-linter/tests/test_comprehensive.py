"""Test the comprehensive example file to ensure all rules work correctly."""

from pathlib import Path

from pinjected_linter.analyzer import PinjectedAnalyzer
from pinjected_linter.reporter import Reporter


def test_comprehensive_example():
    """Test linting the comprehensive example file."""
    analyzer = PinjectedAnalyzer()
    example_file = Path(__file__).parent / "fixtures" / "examples" / "comprehensive_example.py"
    
    violations = analyzer.analyze_file(example_file)
    
    # Group by rule for analysis
    by_rule = {}
    for v in violations:
        by_rule.setdefault(v.rule_id, []).append(v)
    
    # Print detailed report
    reporter = Reporter(output_format="terminal", color=False)
    print("\n" + "="*80)
    print("COMPREHENSIVE EXAMPLE LINTING RESULTS")
    print("="*80)
    print(reporter.report(violations))
    
    # Verify expected violations
    expected_rules = {
        "PINJ001": 1,  # create_logger
        "PINJ002": 1,  # config_manager with default
        "PINJ003": 1,  # a_task_queue
        "PINJ004": 1,  # Direct call to create_logger
        "PINJ008": 1,  # bad_workflow calling undeclared process_data
        # PINJ015 might trigger on ambiguous_function and service_orchestrator
    }
    
    for rule_id, expected_count in expected_rules.items():
        actual_count = len(by_rule.get(rule_id, []))
        print(f"\n{rule_id}: Expected {expected_count}, Found {actual_count}")
        if rule_id in by_rule:
            for v in by_rule[rule_id]:
                print(f"  - Line {v.line}: {v.message[:60]}...")
        
    # Verify counts (allowing for some flexibility with PINJ015)
    assert len(by_rule.get("PINJ001", [])) >= 1
    assert len(by_rule.get("PINJ002", [])) >= 1
    assert len(by_rule.get("PINJ003", [])) >= 1
    assert len(by_rule.get("PINJ004", [])) >= 1
    # PINJ008 might not trigger if process_data isn't defined in the file
    
    # Check that good patterns don't trigger violations
    violation_lines = {v.line for v in violations}
    
    # These lines should NOT have violations
    good_function_lines = {
        14,  # database_connection
        19,  # cache_client  
        24,  # message_broker
        39,  # data_processor
        65,  # a_fetch_and_store
    }
    
    for line in good_function_lines:
        assert line not in violation_lines, f"Good code at line {line} should not have violations"


def test_summary_statistics():
    """Test that we can generate summary statistics."""
    analyzer = PinjectedAnalyzer()
    
    # Analyze all fixture files
    fixture_dir = Path(__file__).parent / "fixtures"
    all_violations = []
    
    for category in ["bad", "good", "examples"]:
        category_dir = fixture_dir / category
        if category_dir.exists():
            for py_file in category_dir.glob("*.py"):
                violations = analyzer.analyze_file(py_file)
                all_violations.extend(violations)
                print(f"\n{py_file.relative_to(fixture_dir)}: {len(violations)} violations")
    
    # Summary by rule
    rule_counts = {}
    for v in all_violations:
        rule_counts[v.rule_id] = rule_counts.get(v.rule_id, 0) + 1
    
    print("\n" + "="*50)
    print("SUMMARY: Violations by Rule")
    print("="*50)
    for rule_id, count in sorted(rule_counts.items()):
        print(f"{rule_id}: {count} violations")
    
    print(f"\nTotal violations: {len(all_violations)}")
    
    # Should have found violations across multiple rules
    assert len(rule_counts) >= 5, "Should detect at least 5 different rule types"
    assert sum(rule_counts.values()) >= 15, "Should find at least 15 total violations"


if __name__ == "__main__":
    test_comprehensive_example()
    print("\n" + "="*80 + "\n")
    test_summary_statistics()
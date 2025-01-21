from pinjected import design, injected

__meta_design__ = design(
    name="test_package.child.module1"
)

# Test variables required by test_pinjected_tester.py
test_viz_target = injected("test_visualization_target")
test_c = injected("test_context_variable")
test_cc = injected("test_context_child_variable")

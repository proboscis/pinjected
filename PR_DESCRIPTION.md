# Enhance exception traceback with detailed source info and optional level details

This PR improves the visualization of exception stack traces during IProxy AST evaluation by:
1. Adding detailed source error traceback information (line numbers, code context, underlines)
2. Implementing a global flag `PINJECTED_SHOW_DETAILED_EVALUATION_CONTEXTS` to control level 0...N details display
3. Collecting all evaluation contexts in a single exception rather than nested exceptions
4. Showing only the last level context by default for cleaner error messages

## Before/After Comparison

### Before:
```
EvaluationError:
    Context: __root__ -> error_func<>
    Context Expr: error_func<>
    Cause Expr: error_func<>
    Source Error: This is a test error in IProxy evaluation
```

### After (with detailed context disabled - default):
```
EvaluationError:
Context: __root__ -> error_func<>
Context Expr: error_func<>
Cause Expr: error_func<>
Source Error: This is a test error in IProxy evaluation

Detailed Source Error Traceback:
Traceback (most recent call last):
  File "/home/ubuntu/repos/pinjected/pinjected/v2/async_resolver.py", line 190, in eval_expr
    res = await bind.provide(new_cxt, deps)
          ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/ubuntu/repos/pinjected/pinjected/v2/binds.py", line 170, in provide
    data = await func(**dep_dict)
           ^^^^^^^^^^^^^^^^^^^^^^
  File "/home/ubuntu/repos/pinjected/test/test_iproxy_composition.py", line 96, in error_func
    raise RuntimeError("This is a test error in IProxy evaluation")
RuntimeError: This is a test error in IProxy evaluation
```

### After (with detailed context enabled):
```
EvaluationError:
Evaluation Path:
→ __root__ -> error_func<> -> __eval__10...6849406472
  → __root__ -> error_func<>

Context Details:
  Level 0:
    Context: __root__ -> error_func<> -> __eval__10...6849406472
    Context Expr: error_func<>
    Cause Expr: error_func<>
  Level 1:
    Context: __root__ -> error_func<>
    Context Expr: error_func<>
    Cause Expr: error_func<>

Source Error: This is a test error in IProxy evaluation

Detailed Source Error Traceback:
Traceback (most recent call last):
  File "/home/ubuntu/repos/pinjected/pinjected/v2/async_resolver.py", line 190, in eval_expr
    res = await bind.provide(new_cxt, deps)
          ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/ubuntu/repos/pinjected/pinjected/v2/binds.py", line 170, in provide
    data = await func(**dep_dict)
           ^^^^^^^^^^^^^^^^^^^^^^
  File "/home/ubuntu/repos/pinjected/test/test_iproxy_composition.py", line 96, in error_func
    raise RuntimeError("This is a test error in IProxy evaluation")
RuntimeError: This is a test error in IProxy evaluation
```

## Flag Usage Documentation

### PINJECTED_SHOW_DETAILED_EVALUATION_CONTEXTS

This global flag controls the verbosity of exception traceback information:

- When set to `True`: Shows all evaluation contexts with detailed information including the full evaluation path and context details for each level
- When set to `False` (default): Shows only the last level context for cleaner error messages

### How to Use

```python
# To enable detailed evaluation contexts via environment variable
export PINJECTED_SHOW_DETAILED_EVALUATION_CONTEXTS=1

# Or in code
from pinjected.v2.resolver import PINJECTED_SHOW_DETAILED_EVALUATION_CONTEXTS
PINJECTED_SHOW_DETAILED_EVALUATION_CONTEXTS = True

# Example usage in tests
try:
    global PINJECTED_SHOW_DETAILED_EVALUATION_CONTEXTS
    original_value = PINJECTED_SHOW_DETAILED_EVALUATION_CONTEXTS
    PINJECTED_SHOW_DETAILED_EVALUATION_CONTEXTS = True
    # Code that might raise EvaluationError
finally:
    PINJECTED_SHOW_DETAILED_EVALUATION_CONTEXTS = original_value
```

## Key Improvements
- **Simplified Default View**: Shows only the last level context by default for cleaner error messages
- **Detailed Source Error**: Includes line numbers, code context, and underlines for better debugging
- **Optional Context Details**: Level 0...N details can be toggled with a global flag
- **Simplified Exception Structure**: Eliminates nested exceptions in the traceback

## Test Results
All tests pass, including the new test case for exception visualization.

## Link to Devin run
https://app.devin.ai/sessions/2ca996ced7d24a7e8b2e33800f19a12f

## Requested by
masui_kento@cyberagent.co.jp

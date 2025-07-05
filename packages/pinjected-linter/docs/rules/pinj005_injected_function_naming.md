# PINJ005: Injected Function Naming Convention

## Overview

**Rule ID:** PINJ005  
**Category:** Naming  
**Severity:** Warning  
**Auto-fixable:** Yes

`@injected` functions should use verb forms in their names.

## Rationale

`@injected` functions represent actions or operations that can be performed with injected dependencies. Using verb forms makes it clear that these are functions to be called, not values to be provided. This convention helps distinguish between:

1. **Actions** (`@injected` functions) - Things that DO something with dependencies
2. **Providers** (`@instance` functions) - Things that PROVIDE dependencies

## Rule Details

This rule checks that functions decorated with `@injected` use verb forms in their names. The rule recognizes:

1. Common verb prefixes (get_, fetch_, create_, update_, etc.)
2. Standalone verbs (init, setup, build, etc.)
3. Verb-first naming patterns

### Examples of Violations

❌ **Bad:** Noun forms in @injected functions
```python
@injected
def user_data(db, /, user_id):  # ❌ Noun form
    return db.query(user_id)

@injected
def result(calculator, /, input):  # ❌ Noun form
    return calculator.compute(input)

@injected
def configuration(loader, /):  # ❌ Noun form
    return loader.load_config()

@injected
def response(api_client, /, endpoint):  # ❌ Noun form
    return api_client.call(endpoint)

@injected
def user_manager(db, /):  # ❌ Noun suffix
    return UserManager(db)
```

✅ **Good:** Verb forms in @injected functions
```python
@injected
def fetch_user_data(db, /, user_id):  # ✅ Verb form
    return db.query(user_id)

@injected
def calculate_result(calculator, /, input):  # ✅ Verb form
    return calculator.compute(input)

@injected
def load_configuration(loader, /):  # ✅ Verb form
    return loader.load_config()

@injected
def get_response(api_client, /, endpoint):  # ✅ Verb form
    return api_client.call(endpoint)

@injected
def create_user_manager(db, /):  # ✅ Verb form
    return UserManager(db)
```

### Async Functions

For async `@injected` functions with the `a_` prefix, the rule checks the part after the prefix:

```python
# ❌ Bad - noun form after a_ prefix
@injected
async def a_user_data(db, /, user_id):
    return await db.query_async(user_id)

# ✅ Good - verb form after a_ prefix
@injected
async def a_fetch_user_data(db, /, user_id):
    return await db.query_async(user_id)
```

## Common Verb Prefixes

The rule recognizes these common verb prefixes:

- **Data operations:** get_, fetch_, load_, save_, store_
- **Creation:** create_, build_, make_, generate_, produce_
- **Modification:** update_, modify_, change_, set_, configure_
- **Deletion:** delete_, remove_, clear_, reset_
- **Processing:** process_, handle_, execute_, run_, perform_
- **Validation:** validate_, verify_, check_, ensure_
- **Transformation:** convert_, transform_, parse_, format_, serialize_
- **Connection:** connect_, disconnect_, bind_, attach_
- **Authentication:** authenticate_, authorize_, sign_, verify_

## Common Patterns and Best Practices

### 1. Be specific about the action
```python
# ❌ Too generic
@injected
def data(db, /):
    return db.all_users()

# ✅ Specific action
@injected
def fetch_all_users(db, /):
    return db.all_users()
```

### 2. Use consistent verb patterns
```python
# ❌ Inconsistent naming
@injected
def user_getter(db, /, id):  # Noun with -er suffix
    return db.get_user(id)

# ✅ Consistent verb pattern
@injected
def get_user(db, /, id):
    return db.get_user(id)
```

### 3. Match the verb to the action
```python
# ❌ Misleading verb
@injected
def get_user(db, /, user_data):  # 'get' implies retrieval, not creation
    return db.create_user(user_data)

# ✅ Accurate verb
@injected
def create_user(db, /, user_data):
    return db.create_user(user_data)
```

## Auto-fix Behavior

The rule can automatically fix violations by adding appropriate verb prefixes:

- `user_data` → `get_user_data`
- `configuration` → `load_configuration`
- `result` → `calculate_result`
- `response` → `get_response`

The auto-fix uses contextual hints from the noun to suggest appropriate verbs.

## Configuration

This rule's severity can be configured:

```toml
[tool.pinjected-linter]
rules.PINJ005.severity = "error"  # Change from warning to error
```

## When to Disable

You might disable this rule when:
- Working with legacy code during migration
- Following different naming conventions in your team

To disable for a specific function:
```python
# noqa: PINJ005
@injected
def legacy_data(db, /):
    return db.get_legacy_data()
```

To disable in configuration:
```toml
[tool.pinjected-linter]
disable = ["PINJ005"]
```

## Related Rules

- **PINJ001:** Instance function naming (opposite convention for `@instance`)
- **PINJ009:** Injected async function prefix

## See Also

- [Pinjected Documentation - @injected decorator](https://pinjected.readthedocs.io/injected)
- [Clean Code - Meaningful Names](https://www.oreilly.com/library/view/clean-code-a/9780136083238/)

## Version History

- **1.0.0:** Initial implementation matching Linear issue ARC-288
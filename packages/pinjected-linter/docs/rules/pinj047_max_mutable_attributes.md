# PINJ047: Maximum Mutable Attributes

## Summary

Limits the number of mutable attributes (those assigned outside `__init__` or `__post_init__`) in a class to a configurable maximum (default: 1).

## Rationale

Classes with multiple mutable attributes are harder to reason about and test. Each mutable attribute represents a dimension of state that can change independently, leading to exponential growth in possible state combinations.

By limiting mutable attributes, we:
1. Encourage more functional, immutable designs
2. Make classes easier to understand and test
3. Reduce bugs related to unexpected state changes
4. Promote the use of composition and dependency injection over stateful classes

## Examples

### ❌ Incorrect

```python
class GameState:
    def __init__(self):
        self.mut_score = 0
        self.mut_level = 1
        self.mut_lives = 3
    
    def update_score(self, points):
        self.mut_score += points  # PINJ047: 3 mutable attributes exceed limit of 1
    
    def next_level(self):
        self.mut_level += 1
    
    def lose_life(self):
        self.mut_lives -= 1
```

```python
class UserSession:
    def __init__(self):
        self.user_id = None
        self.auth_token = None
    
    def login(self, user_id, token):
        self.user_id = user_id      # First mutable attribute
        self.auth_token = token     # Second mutable attribute (exceeds default limit)
    
    def refresh_token(self, new_token):
        self.auth_token = new_token
```

### ✅ Correct

```python
# Option 1: Single mutable attribute
class Counter:
    def __init__(self):
        self.mut_count = 0
    
    def increment(self):
        self.mut_count += 1

# Option 2: Use immutable design with return values
@dataclass(frozen=True)
class GameState:
    score: int
    level: int
    lives: int
    
    def with_score(self, points: int) -> 'GameState':
        return GameState(self.score + points, self.level, self.lives)
    
    def next_level(self) -> 'GameState':
        return GameState(self.score, self.level + 1, self.lives)

# Option 3: Use composition to separate concerns
class ScoreTracker:
    def __init__(self):
        self.mut_score = 0
    
    def add_points(self, points):
        self.mut_score += points

class LevelTracker:
    def __init__(self):
        self.mut_level = 1
    
    def advance(self):
        self.mut_level += 1

# Option 4: Use dependency injection for state management
@injected
def game_logic(score_tracker: ScoreTracker, level_tracker: LevelTracker, /):
    # Use injected stateful components
    pass
```

## Configuration

You can configure the maximum number of allowed mutable attributes in your `pyproject.toml`:

```toml
[tool.pinjected-linter.rules.PINJ047]
max_mutable_attributes = 2  # Allow up to 2 mutable attributes per class
```

### Configuration Examples

```toml
# Strict: No mutable attributes allowed
[tool.pinjected-linter.rules.PINJ047]
max_mutable_attributes = 0

# Default: One mutable attribute allowed
# (No configuration needed, this is the default)

# Relaxed: Allow up to 3 mutable attributes
[tool.pinjected-linter.rules.PINJ047]
max_mutable_attributes = 3
```

## Special Cases

### Initialization Methods

Attributes assigned only in `__init__` or `__post_init__` are not considered mutable:

```python
class ImmutableConfig:
    def __init__(self, data):
        # These are only set during initialization
        self.host = data['host']
        self.port = data['port']
        self.timeout = data['timeout']
    
    def get_url(self):
        return f"{self.host}:{self.port}"  # Only reading, not mutating
```

### Refactoring Strategies

When you exceed the mutable attribute limit, consider these refactoring strategies:

1. **Immutable Objects**: Use `@dataclass(frozen=True)` or named tuples
2. **Composition**: Split the class into smaller, focused classes
3. **State Pattern**: Encapsulate state transitions in separate classes
4. **Event Sourcing**: Store state changes as events rather than mutable fields
5. **Dependency Injection**: Inject state managers rather than managing state directly

## Suppression

If you need to suppress this rule for a specific class, use the `# noqa: PINJ047` comment:

```python
class LegacyStatefulClass:  # noqa: PINJ047
    def __init__(self):
        self.mut_state1 = 0
        self.mut_state2 = 0
        self.mut_state3 = 0
```

However, it's strongly recommended to refactor your code to reduce mutable state rather than suppressing the rule.

## See Also

- PINJ046: Mutable Attribute Naming - Enforces naming conventions for mutable attributes
- The concept of immutability in functional programming
- State pattern in object-oriented design
- Event sourcing architectural pattern
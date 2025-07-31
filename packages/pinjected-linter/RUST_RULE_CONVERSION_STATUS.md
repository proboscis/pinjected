# Rust Rule Conversion Status

## Conversion Progress

| Rule ID | Description | Python Status | Rust Status | Priority | Notes |
|---------|-------------|---------------|-------------|----------|-------|
| PINJ001 | Instance naming convention | ✅ Implemented | ✅ Implemented | High | Completed - checks @instance functions are nouns |
| PINJ002 | Instance defaults | ✅ Implemented | ✅ Implemented | High | Check default parameter usage |
| PINJ003 | Async instance naming | ✅ Implemented | ✅ Implemented | Medium | a_ prefix for async @instance |
| PINJ004 | Direct instance call | ✅ Implemented | ⏳ TODO | High | Avoid calling @instance directly |
| PINJ005 | Injected function naming | ✅ Implemented | ⏳ TODO | Low | Should be verbs/actions (currently disabled) |
| PINJ006 | Async injected naming | ✅ Implemented | ⏳ TODO | Medium | a_ prefix for async @injected |
| PINJ007 | Slash separator position | ✅ Implemented | ⏳ TODO | Medium | Proper / placement |
| PINJ008 | Injected dependency declaration | ✅ Implemented | ⏳ TODO | High | Dependencies before / |
| PINJ009 | No await in injected | ✅ Implemented | ⏳ TODO | High | Except for declared dependencies |
| PINJ010 | Design usage | ✅ Implemented | ⏳ TODO | Medium | Proper design() function usage |
| PINJ011 | IProxy annotations | ✅ Implemented | ⏳ TODO | Medium | Not for injected dependencies |
| PINJ012 | Dependency cycles | ✅ Implemented | ⏳ TODO | High | Complex - needs graph analysis |
| PINJ013 | Builtin shadowing | ✅ Implemented | ⏳ TODO | Low | Avoid shadowing builtins |
| PINJ014 | Missing stub file | ✅ Implemented | ⏳ TODO | Low | .pyi for @injected functions |
| PINJ015 | Missing slash | ✅ Implemented | ⏳ TODO | High | Require / in @injected functions |

## Conversion Order (by priority and complexity)

### Phase 1: Simple Rules (Week 1)
1. **PINJ002** - Instance defaults ⭐ Next
2. **PINJ003** - Async instance naming
3. **PINJ006** - Async injected naming
4. **PINJ013** - Builtin shadowing

### Phase 2: Core Rules (Week 2)
5. **PINJ004** - Direct instance call
6. **PINJ008** - Injected dependency declaration
7. **PINJ015** - Missing slash
8. **PINJ007** - Slash separator position

### Phase 3: Complex Rules (Week 3)
9. **PINJ009** - No await in injected
10. **PINJ010** - Design usage
11. **PINJ011** - IProxy annotations

### Phase 4: Advanced Rules (Week 4)
12. **PINJ012** - Dependency cycles (requires graph analysis)
13. **PINJ014** - Missing stub file (requires file I/O)
14. **PINJ005** - Injected function naming (if re-enabled)

## Implementation Checklist for Each Rule

When implementing each rule in Rust:

- [ ] Create `src/rules/pinj00X_rule_name.rs` file
- [ ] Port the rule logic from Python
- [ ] Add comprehensive tests
- [ ] Update `src/rules/mod.rs` to include the new rule
- [ ] Test against the same test cases as Python version
- [ ] Verify error messages match Python version
- [ ] Update this status document

## Helper Modules Needed

1. **AST Utilities** (`src/utils/ast_helpers.rs`)
   - Function decorator detection
   - Parameter analysis
   - Import resolution

2. **Pinjected Patterns** (`src/utils/pinjected_patterns.rs`)
   - @instance detection
   - @injected detection
   - slash separator detection
   - async function detection

3. **Symbol Table** (`src/utils/symbol_table.rs`)
   - For rules needing cross-reference (PINJ004, PINJ012)

## Testing Strategy

1. Port Python test cases to Rust
2. Create fixture files for each rule
3. Ensure 100% compatibility with Python version
4. Benchmark performance improvements
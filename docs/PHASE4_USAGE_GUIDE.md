# Phase 4: Advanced Features - Usage Guide

## Quick Start

```python
from typescript_extractor import get_typescript_dependencies

# Extract all features including Phase 4
code_file = await get_typescript_dependencies(
    repo_path="/path/to/repo",
    script_path="/path/to/file.ts",
    detailed_extraction=True
)
```

## New Features Access

### 1. Export Tracking

Access all exports from a file:

```python
for export in code_file.exports:
    print(f"Export: {export.name}")

    # Check export type
    if export.is_default:
        print("  → Default export")
    if export.is_type_only:
        print("  → Type-only export")
    if export.local_name:
        print(f"  → Aliased from: {export.local_name}")

    # Access metadata
    print(f"  Source: {export.source_code}")
    print(f"  Location: {export.start_point} - {export.end_point}")
```

**Export Types Captured:**

```typescript
// Named export
export { foo };  // → ExportStatement(name='foo')

// Aliased export
export { bar as baz };  // → ExportStatement(name='baz', local_name='bar')

// Default export
export default MyClass;  // → ExportStatement(name='default', is_default=True)

// Type-only export
export type { User };  // → ExportStatement(name='User', is_type_only=True)
```

### 2. Method Extraction

Access all methods from classes:

```python
for method in code_file.provides_method_definition:
    print(f"Method: {method.class_name}.{method.name}")

    # Check method flags
    if method.is_constructor:
        print("  → Constructor")
    if method.is_static:
        print("  → Static method")
    if method.is_async:
        print("  → Async method")
    if method.is_private:
        print("  → Private method")
    if method.is_getter:
        print("  → Getter")
    if method.is_setter:
        print("  → Setter")

    # Access metadata
    print(f"  Source: {method.source_code}")
```

**Method Types Captured:**

```typescript
class MyClass {
    // Constructor
    constructor() {}  // → is_constructor=True

    // Regular method
    doSomething() {}  // → name='doSomething'

    // Static method
    static create() {}  // → is_static=True

    // Async method
    async fetchData() {}  // → is_async=True

    // Private method
    private helper() {}  // → is_private=True

    // Getter
    get value() {}  // → is_getter=True

    // Setter
    set value(v) {}  // → is_setter=True
}
```

### 3. Function Expressions

Function expressions are now extracted alongside other functions:

```python
for func in code_file.provides_function_definition:
    print(f"Function: {func.name}")
```

**Function Types Captured:**

```typescript
// Function declaration (Phase 1)
function foo() {}  // → FunctionDefinition(name='foo')

// Arrow function (Phase 1)
const bar = () => {};  // → FunctionDefinition(name='bar')

// Function expression (Phase 4 NEW)
const baz = function() {};  // → FunctionDefinition(name='baz')

// Named function expression (Phase 4 NEW)
const qux = function named() {};  // → FunctionDefinition(name='qux')
```

## Complete Example

```python
import asyncio
from typescript_extractor import get_typescript_dependencies

async def analyze_typescript_file(file_path: str):
    """Analyze a TypeScript file and print all extracted information."""

    code_file = await get_typescript_dependencies(
        repo_path="/path/to/repo",
        script_path=file_path,
        detailed_extraction=True
    )

    print(f"File: {code_file.name}")
    print(f"Language: {code_file.language}")
    print()

    # Imports (Phase 1 & 2)
    print(f"Imports: {len(code_file.depends_on)}")
    for imp in code_file.depends_on:
        print(f"  - {imp.name} from '{imp.module}'")
    print()

    # Functions (Phase 1 & 4)
    print(f"Functions: {len(code_file.provides_function_definition)}")
    for func in code_file.provides_function_definition:
        print(f"  - {func.name}")
    print()

    # Classes (Phase 1)
    print(f"Classes: {len(code_file.provides_class_definition)}")
    for cls in code_file.provides_class_definition:
        print(f"  - {cls.name}")
    print()

    # Methods (Phase 4 NEW)
    print(f"Methods: {len(code_file.provides_method_definition)}")
    for method in code_file.provides_method_definition:
        flags = []
        if method.is_static: flags.append("static")
        if method.is_async: flags.append("async")
        if method.is_private: flags.append("private")
        flag_str = f" [{', '.join(flags)}]" if flags else ""
        print(f"  - {method.class_name}.{method.name}{flag_str}")
    print()

    # Interfaces (Phase 3)
    print(f"Interfaces: {len(code_file.provides_interface_definition)}")
    for interface in code_file.provides_interface_definition:
        print(f"  - {interface.name}")
    print()

    # Type Aliases (Phase 3)
    print(f"Type Aliases: {len(code_file.provides_type_alias)}")
    for type_alias in code_file.provides_type_alias:
        print(f"  - {type_alias.name}")
    print()

    # Enums (Phase 3)
    print(f"Enums: {len(code_file.provides_enum_definition)}")
    for enum in code_file.provides_enum_definition:
        print(f"  - {enum.name}")
    print()

    # Exports (Phase 4 NEW)
    print(f"Exports: {len(code_file.exports)}")
    for exp in code_file.exports:
        exp_type = []
        if exp.is_default: exp_type.append("default")
        if exp.is_type_only: exp_type.append("type")
        if exp.local_name: exp_type.append(f"as {exp.name}")
        type_str = f" ({', '.join(exp_type)})" if exp_type else ""
        name = exp.local_name if exp.local_name else exp.name
        print(f"  - {name}{type_str}")

# Run
asyncio.run(analyze_typescript_file("example.ts"))
```

## Data Model Reference

### ExportStatement

```python
class ExportStatement:
    name: str                    # Export name
    local_name: Optional[str]    # Original name if aliased
    is_default: bool             # True for default exports
    is_type_only: bool           # True for type-only exports
    start_point: tuple           # (line, column)
    end_point: tuple             # (line, column)
    source_code: str             # Original source
    file_path: Optional[str]     # File path
```

### MethodDefinition

```python
class MethodDefinition:
    name: str                    # Method name
    class_name: str              # Parent class name
    is_static: bool              # Static method flag
    is_async: bool               # Async method flag
    is_private: bool             # Private method flag
    is_getter: bool              # Getter flag
    is_setter: bool              # Setter flag
    is_constructor: bool         # Constructor flag
    start_point: tuple           # (line, column)
    end_point: tuple             # (line, column)
    source_code: str             # Original source
    file_path: Optional[str]     # File path
```

## Common Use Cases

### 1. Find All Exports from a Module

```python
def get_module_exports(code_file):
    """Get all exported names from a module."""
    exports = []
    for exp in code_file.exports:
        if exp.is_default:
            exports.append("default")
        else:
            exports.append(exp.name)
    return exports
```

### 2. Find All Public Methods in a Class

```python
def get_public_methods(code_file, class_name: str):
    """Get all public methods for a specific class."""
    return [
        method for method in code_file.provides_method_definition
        if method.class_name == class_name and not method.is_private
    ]
```

### 3. Find All Async Functions and Methods

```python
def get_async_operations(code_file):
    """Get all async functions and methods."""
    async_funcs = [
        f for f in code_file.provides_function_definition
        if 'async' in f.source_code
    ]
    async_methods = [
        m for m in code_file.provides_method_definition
        if m.is_async
    ]
    return async_funcs + async_methods
```

### 4. Check if Module Has Default Export

```python
def has_default_export(code_file):
    """Check if file has a default export."""
    return any(exp.is_default for exp in code_file.exports)
```

### 5. Get Type-Only Exports

```python
def get_type_exports(code_file):
    """Get all type-only exports."""
    return [
        exp.name for exp in code_file.exports
        if exp.is_type_only
    ]
```

## Backward Compatibility

All Phase 4 features are fully backward compatible. Existing code continues to work:

```python
# Phase 1-3 code still works exactly the same
code_file = await get_typescript_dependencies(
    repo_path="/path/to/repo",
    script_path="/path/to/file.ts",
    detailed_extraction=True
)

# Access existing features
imports = code_file.depends_on
functions = code_file.provides_function_definition
classes = code_file.provides_class_definition
interfaces = code_file.provides_interface_definition
types = code_file.provides_type_alias
enums = code_file.provides_enum_definition

# NEW Phase 4 features (won't break existing code)
exports = code_file.exports  # New field
methods = code_file.provides_method_definition  # New field
```

## Tips & Best Practices

1. **Always use detailed_extraction=True** for full feature access
2. **Check method flags** to understand method characteristics
3. **Use export tracking** to understand module public API
4. **Combine with existing data** for comprehensive code analysis
5. **Handle edge cases** - some exports/methods may have unusual patterns

## Testing

Run provided tests to verify functionality:

```bash
# Test backward compatibility
python test_typescript_extractor.py

# Test Phase 4 features
python test_phase4_features.py

# Test all features together
python test_comprehensive.py
```

All tests should pass with ✅ marks.

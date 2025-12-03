# TypeScript Extraction Implementation Requirements

## Overview

Implement full TypeScript/TSX extraction to match Python's capabilities in the cognee code graph pipeline. This enables structural queries (imports, functions, classes, dependencies) for TypeScript codebases.

## Goal

Create `get_typescript_dependencies()` function that:
- Parses `.ts` and `.tsx` files using tree-sitter-typescript
- Extracts imports, exports, functions, classes, interfaces, type aliases
- Returns `CodeFile` with populated relationship lists
- Integrates with existing pipeline (no changes to `add_data_points`)

## Scope

### In Scope
- ES module imports (`import x from 'y'`, `import { x } from 'y'`)
- CommonJS requires (`const x = require('y')`)
- Re-exports (`export { x } from 'y'`)
- Function declarations (named, arrow, async)
- Class declarations
- Interface declarations
- Type alias declarations
- JSX/TSX support

### Out of Scope (v1)
- Type inference/resolution
- Generic type parameter extraction
- Decorator metadata
- Module augmentation
- Namespace declarations
- Enum member extraction (enum itself extracted)

## Technical Design

### 1. File Structure

```
cognee-agent/
├── typescript_extractor/
│   ├── __init__.py
│   ├── parser.py              # Tree-sitter setup
│   ├── extractor.py           # Main extraction logic
│   ├── models.py              # TypeScript-specific models (if needed)
│   └── node_handlers.py       # AST node type handlers
```

### 2. Tree-sitter Setup

```python
# parser.py
from tree_sitter import Language, Parser
import tree_sitter_typescript as tstypescript

# typescript has two grammars: typescript and tsx
TS_LANGUAGE = Language(tstypescript.language_typescript())
TSX_LANGUAGE = Language(tstypescript.language_tsx())

def get_parser(file_path: str) -> Parser:
    """Return parser based on file extension."""
    if file_path.endswith('.tsx'):
        return Parser(TSX_LANGUAGE)
    return Parser(TS_LANGUAGE)
```

### 3. Main Extraction Function

**Signature**:
```python
async def get_typescript_dependencies(
    repo_path: str,
    script_path: str,
    detailed_extraction: bool = False
) -> CodeFile
```

**Returns**: `CodeFile` with:
- `depends_on`: List[ImportStatement] - all imports
- `provides_function_definition`: List[FunctionDefinition] - functions
- `provides_class_definition`: List[ClassDefinition] - classes

**Behavior**:
- Match Python's simple/detailed extraction modes
- Simple mode: return CodeFile with `source_code` only
- Detailed mode: return CodeFile with relationships, `source_code=None`

### 4. TypeScript AST Node Types

#### Import Statements

| Syntax | tree-sitter node type |
|--------|----------------------|
| `import x from 'y'` | `import_statement` |
| `import { x } from 'y'` | `import_statement` |
| `import * as x from 'y'` | `import_statement` |
| `import 'y'` (side-effect) | `import_statement` |
| `import type { X } from 'y'` | `import_statement` |
| `const x = require('y')` | `lexical_declaration` + `call_expression` |
| `export { x } from 'y'` | `export_statement` |

**Child nodes for `import_statement`**:
- `import_clause` → contains `identifier` or `named_imports`
- `string` → module specifier

**ImportStatement fields**:
```python
ImportStatement(
    name="x",                    # imported identifier
    module="y",                  # module specifier
    start_point=(line, col),
    end_point=(line, col),
    source_code="import x from 'y'",
    file_path="/path/to/file.ts"
)
```

#### Function Declarations

| Syntax | tree-sitter node type |
|--------|----------------------|
| `function foo() {}` | `function_declaration` |
| `async function foo() {}` | `function_declaration` |
| `const foo = () => {}` | `lexical_declaration` |
| `const foo = function() {}` | `lexical_declaration` |
| `export function foo() {}` | `export_statement` → `function_declaration` |
| `export default function() {}` | `export_statement` |

**Extraction rules**:
1. Top-level `function_declaration` → extract directly
2. `lexical_declaration` with `arrow_function` or `function_expression` → extract as function
3. `export_statement` containing function → extract the inner function

#### Class Declarations

| Syntax | tree-sitter node type |
|--------|----------------------|
| `class Foo {}` | `class_declaration` |
| `abstract class Foo {}` | `abstract_class_declaration` |
| `export class Foo {}` | `export_statement` → `class_declaration` |

#### Interface Declarations

| Syntax | tree-sitter node type |
|--------|----------------------|
| `interface Foo {}` | `interface_declaration` |
| `export interface Foo {}` | `export_statement` → `interface_declaration` |

**New model needed**:
```python
class InterfaceDefinition(DataPoint):
    name: str
    start_point: tuple
    end_point: tuple
    source_code: str
    file_path: Optional[str] = None
    metadata: dict = {"index_fields": ["source_code"]}
```

**CodeFile extension**:
```python
# Add to CodeFile or create TypeScriptFile subclass
provides_interface_definition: Optional[List["InterfaceDefinition"]] = []
provides_type_alias: Optional[List["TypeAliasDefinition"]] = []
```

#### Type Aliases

| Syntax | tree-sitter node type |
|--------|----------------------|
| `type Foo = {...}` | `type_alias_declaration` |
| `export type Foo = {...}` | `export_statement` → `type_alias_declaration` |

### 5. Integration Point

**Modify**: `cognee/tasks/repo_processor/get_repo_file_dependencies.py` (or local copy)

```python
# Current code (lines 213-252)
for file_path, lang in source_code_files[start_range : end_range + 1]:
    if lang == "python":
        tasks.append(
            get_local_script_dependencies(repo_path, file_path, detailed_extraction)
        )
    elif lang == "typescript":  # NEW
        tasks.append(
            get_typescript_dependencies(repo_path, file_path, detailed_extraction)
        )
    else:
        # Stub for other languages
        tasks.append(make_codefile_stub())
```

### 6. Implementation Phases

#### Phase 1: Basic Extraction (MVP)
- [ ] Tree-sitter setup for .ts/.tsx
- [ ] Import extraction (ES modules only)
- [ ] Function declaration extraction
- [ ] Class declaration extraction
- [ ] Integration with pipeline

#### Phase 2: Complete Import Support
- [ ] Named imports (`import { a, b } from 'x'`)
- [ ] Namespace imports (`import * as x from 'y'`)
- [ ] Type-only imports (`import type { X } from 'y'`)
- [ ] CommonJS requires (`require('x')`)
- [ ] Re-exports (`export { x } from 'y'`)

#### Phase 3: TypeScript-Specific Constructs
- [ ] Interface declarations
- [ ] Type alias declarations
- [ ] Enum declarations
- [ ] Arrow function variables
- [ ] Async functions

#### Phase 4: Advanced Features
- [ ] Export tracking (what does file export?)
- [ ] Method extraction from classes
- [ ] JSDoc comment preservation
- [ ] Default exports

### 7. Testing Requirements

#### Unit Tests
```python
# test_typescript_extractor.py

def test_es_module_import():
    """import x from 'y' → ImportStatement(name='x', module='y')"""

def test_named_import():
    """import { a, b } from 'y' → 2 ImportStatements"""

def test_function_declaration():
    """function foo() {} → FunctionDefinition(name='foo')"""

def test_arrow_function():
    """const foo = () => {} → FunctionDefinition(name='foo')"""

def test_class_declaration():
    """class Foo {} → ClassDefinition(name='Foo')"""

def test_interface_declaration():
    """interface Foo {} → InterfaceDefinition(name='Foo')"""

def test_tsx_jsx():
    """const X = () => <div/> → FunctionDefinition (JSX preserved)"""

def test_export_function():
    """export function foo() {} → FunctionDefinition with export flag"""
```

#### Integration Tests
```python
def test_full_pipeline():
    """Ingest TypeScript repo, verify graph relationships"""

def test_query_ts_imports():
    """Query 'what does file.ts import?' returns correct modules"""

def test_mixed_codebase():
    """Python + TypeScript repo processes both correctly"""
```

### 8. Data Model Decisions

**Option A: Extend CodeFile**
```python
class CodeFile(DataPoint):
    # existing fields...
    provides_interface_definition: Optional[List["InterfaceDefinition"]] = []
    provides_type_alias: Optional[List["TypeAliasDefinition"]] = []
```
- Pro: Single model for all languages
- Con: Python files have empty TypeScript-specific fields

**Option B: TypeScriptFile subclass**
```python
class TypeScriptFile(CodeFile):
    provides_interface_definition: Optional[List["InterfaceDefinition"]] = []
    provides_type_alias: Optional[List["TypeAliasDefinition"]] = []
```
- Pro: Clean separation
- Con: Query complexity (need to handle both types)

**Recommendation**: Option A (extend CodeFile) for simplicity

### 9. Edge Cases

| Case | Handling |
|------|----------|
| Dynamic imports `import('x')` | Skip (runtime-only) |
| Triple-slash directives `/// <reference>` | Skip (v1) |
| Ambient modules `declare module` | Skip (v1) |
| Re-exported types `export type { X }` | Extract as import + note re-export |
| Default + named `import x, { y }` | Two ImportStatements |
| Side-effect imports `import 'x'` | ImportStatement(name='', module='x') |
| Computed exports | Skip |

### 10. Performance Considerations

- **Async file I/O**: Use `aiofiles` for file reading
- **Parallel parsing**: Process files in batches with `asyncio.gather()`
- **Large files**: tree-sitter handles efficiently, no special handling needed
- **Memory**: Yield DataPoints, don't accumulate (match Python behavior)

### 11. Dependencies

**Already installed** (in cognee):
- `tree-sitter` (0.25.2)
- `tree-sitter-typescript` (0.23.2)

**No new dependencies required.**

### 12. Acceptance Criteria

1. ✅ `.ts` and `.tsx` files fully parsed (not just stub)
2. ✅ Imports extracted with correct module/name
3. ✅ Functions extracted (declarations + arrow functions)
4. ✅ Classes extracted
5. ✅ Graph queries work: "What does X import?", "What functions does Y provide?"
6. ✅ Mixed Python+TypeScript codebase works
7. ✅ Performance: < 2x Python extraction time for equivalent code

## Appendix: tree-sitter-typescript Node Types

Reference for common node types:

```
program
├── import_statement
│   ├── import_clause
│   │   ├── identifier (default import)
│   │   └── named_imports
│   │       └── import_specifier
│   │           └── identifier
│   └── string (module path)
├── export_statement
│   ├── export_clause
│   │   └── export_specifier
│   ├── declaration
│   └── string (for re-exports)
├── function_declaration
│   ├── identifier (name)
│   ├── formal_parameters
│   └── statement_block
├── lexical_declaration
│   └── variable_declarator
│       ├── identifier (name)
│       └── arrow_function / function_expression
├── class_declaration
│   ├── identifier (name)
│   └── class_body
├── interface_declaration
│   ├── identifier (name)
│   └── object_type
└── type_alias_declaration
    ├── identifier (name)
    └── type_annotation
```

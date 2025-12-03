# TypeScript Extractor - Phase 1 (MVP)

TypeScript/TSX code dependency extractor for the cognee-agent project.

## Module Structure

```
typescript_extractor/
├── __init__.py              # Exports get_typescript_dependencies
├── parser.py                # Tree-sitter setup for .ts/.tsx
├── extractor.py             # Main extraction logic
├── node_handlers.py         # AST node type handlers
└── README.md               # This file
```

## Installation

Required dependencies (already installed):
- `tree-sitter-typescript`
- `tree-sitter`
- `aiofiles`
- `cognee` (for CodeGraphEntities and logging)

## Usage

```python
from typescript_extractor import get_typescript_dependencies

# Basic extraction (just source code)
code_file = await get_typescript_dependencies(
    repo_path="/path/to/repo",
    script_path="/path/to/repo/src/file.ts",
    detailed_extraction=False
)

# Detailed extraction (imports, functions, classes)
code_file = await get_typescript_dependencies(
    repo_path="/path/to/repo",
    script_path="/path/to/repo/src/file.ts",
    detailed_extraction=True
)

# Access extracted data
print(f"Imports: {len(code_file.depends_on)}")
print(f"Functions: {len(code_file.provides_function_definition)}")
print(f"Classes: {len(code_file.provides_class_definition)}")
```

## Phase 1 Features

### Supported Imports
- ✅ Default imports: `import React from 'react'`
- ✅ Namespace imports: `import * as Utils from './utils'`
- ⏸️ Named imports: `import { foo, bar } from 'module'` (Phase 2)
- ⏸️ Side-effect imports: `import './styles.css'` (Phase 2)

### Supported Functions
- ✅ Function declarations: `function foo() {}`
- ✅ Async functions: `async function foo() {}`
- ✅ Arrow functions: `const foo = () => {}`
- ✅ Exported functions: `export function foo() {}`

### Supported Classes
- ✅ Class declarations: `class Foo {}`
- ✅ Abstract classes: `abstract class Foo {}`
- ✅ Exported classes: `export class Foo {}`

### File Types
- ✅ TypeScript files: `.ts`
- ✅ TSX files: `.tsx` (React components)

## API Reference

### `get_typescript_dependencies(repo_path, script_path, detailed_extraction=False)`

**Parameters:**
- `repo_path` (str): Path to repository root
- `script_path` (str): Absolute path to .ts/.tsx file
- `detailed_extraction` (bool): If True, extract imports/functions/classes. If False, just return source code.

**Returns:**
- `CodeFile`: Object with the following structure:
  - `id`: UUID generated from script_path
  - `name`: Relative path from repo root
  - `file_path`: Absolute file path
  - `language`: Always "typescript"
  - `source_code`: Full source (if detailed_extraction=False)
  - `depends_on`: List of ImportStatement objects
  - `provides_function_definition`: List of FunctionDefinition objects
  - `provides_class_definition`: List of ClassDefinition objects

## Examples

### Example 1: Extract from TypeScript file

```typescript
// src/utils.ts
import React from 'react';

export function formatDate(date: Date): string {
    return date.toISOString();
}

export class Logger {
    log(message: string) {
        console.log(message);
    }
}
```

```python
code_file = await get_typescript_dependencies(
    repo_path="/project",
    script_path="/project/src/utils.ts",
    detailed_extraction=True
)

# Results:
# code_file.depends_on = [ImportStatement(name='React', module='react')]
# code_file.provides_function_definition = [FunctionDefinition(name='formatDate')]
# code_file.provides_class_definition = [ClassDefinition(name='Logger')]
```

### Example 2: Extract from TSX file

```tsx
// src/Button.tsx
import React from 'react';

export const Button = ({ label }: { label: string }) => {
    return <button>{label}</button>;
};
```

```python
code_file = await get_typescript_dependencies(
    repo_path="/project",
    script_path="/project/src/Button.tsx",
    detailed_extraction=True
)

# Results:
# code_file.depends_on = [ImportStatement(name='React', module='react')]
# code_file.provides_function_definition = [FunctionDefinition(name='Button')]
```

## Testing

Run the test suite:

```bash
python test_typescript_extractor.py
```

Expected output:
```
✓ ✅ Can parse .ts files
✓ ✅ Default imports extracted
✓ ✅ Function declarations extracted
✓ ✅ Class declarations extracted
✓ ✅ CodeFile has proper fields
✓ ✅ detailed_extraction modes work
```

## Implementation Details

### Parser (`parser.py`)
- Uses `tree-sitter-typescript` for parsing
- Automatically selects TS or TSX parser based on file extension
- Caches parsed files to avoid re-parsing

### Node Handlers (`node_handlers.py`)
- `extract_import_from_node()`: Extracts import statements
- `extract_function_from_node()`: Extracts function definitions
- `extract_class_from_node()`: Extracts class definitions

### Extractor (`extractor.py`)
- Main entry point: `get_typescript_dependencies()`
- Handles both simple and detailed extraction modes
- Processes AST nodes and populates CodeFile object

## Future Phases

### Phase 2: Advanced Extraction
- Named imports and exports
- Default exports
- Re-exports
- Type imports/exports
- Interface and type definitions

### Phase 3: Advanced Analysis
- Function signatures
- Class methods and properties
- JSX component analysis
- Dependency resolution

## Error Handling

The module includes robust error handling:
- File read errors are logged and return None
- Node extraction errors are caught and logged
- Invalid AST nodes are skipped gracefully

## Logging

Uses cognee's logging infrastructure:
```python
from cognee.shared.logging_utils import get_logger
logger = get_logger()
```

All errors and warnings are logged with context.

# TypeScript Support Analysis

## Summary

TypeScript files are **detected but not fully parsed** by the cognee code graph pipeline. This is a cognee library limitation, not an issue with our implementation.

## Current Behavior

| Aspect | Python | TypeScript |
|--------|--------|------------|
| File Detection | `.py` | `.ts`, `.tsx` |
| Added to Graph | Yes | Yes |
| Source Code Stored | Yes | Yes |
| Import Extraction | Yes | **No** |
| Function Extraction | Yes | **No** |
| Class Extraction | Yes | **No** |
| Dependency Graph | Yes | **No** |

TypeScript files are ingested as `CodeFile` nodes containing only:
- `id`, `name`, `file_path`, `language`, `source_code`

Missing (empty) fields:
- `depends_on` (imports)
- `provides_function_definition`
- `provides_class_definition`

## Root Cause

### Location
`cognee/tasks/repo_processor/get_repo_file_dependencies.py` lines 213-233

### Code
```python
for file_path, lang in source_code_files[start_range : end_range + 1]:
    # For now, only Python is supported; extend with other languages
    if lang == "python":  # <-- Explicit gate
        tasks.append(
            get_local_script_dependencies(repo_path, file_path, detailed_extraction)
        )
    else:
        # Placeholder: create a minimal CodeFile for other languages
        async def make_codefile_stub(file_path=file_path, lang=lang):
            async with aiofiles.open(file_path, "r", ...) as f:
                source = await f.read()
            return CodeFile(
                id=uuid5(NAMESPACE_OID, file_path),
                name=os.path.relpath(file_path, repo_path),
                file_path=file_path,
                language=lang,
                source_code=source,  # <-- Only source code
            )
        tasks.append(make_codefile_stub())
```

### Comments in Source
- Line 213: `"For now, only Python is supported; extend with other languages"`
- Line 208: `"# TODO: Add other language extractors here"`

## Tree-Sitter Status

| Package | Installed | Used |
|---------|-----------|------|
| `tree-sitter` | Yes (0.25.2) | Yes |
| `tree-sitter-python` | Yes (0.25.0) | Yes |
| `tree-sitter-typescript` | Yes (0.23.2) | **No** |

The TypeScript tree-sitter library is installed as a dependency but never imported or used in cognee's extraction logic.

## Language Configuration

Cognee correctly maps TypeScript extensions:

```python
language_config = {
    "python": [".py"],
    "javascript": [".js", ".jsx"],
    "typescript": [".ts", ".tsx"],  # Correctly includes .tsx
    "java": [".java"],
    "csharp": [".cs"],
    "go": [".go"],
    "rust": [".rs"],
    "cpp": [".cpp", ".c", ".h", ".hpp"],
}
```

## Workarounds

### Option 1: Accept Limitation
TypeScript files are indexed with source code content. Graph queries can find files but won't have structural relationships.

### Option 2: Use `--include-docs` Flag
```bash
uv run python main.py ingest --include-docs
```

This enables the docs pipeline which:
1. Processes files through `get_non_py_files` (includes .ts, .tsx)
2. Chunks text content
3. Uses LLM to extract entities and relationships
4. Generates summaries

Trade-offs:
- Slower (LLM calls per chunk)
- Uses API tokens
- Extracts semantic entities, not AST-based imports/functions

### Option 3: Implement TypeScript Extraction
Would require:
1. Creating `get_typescript_dependencies()` function
2. Using `tree-sitter-typescript` for AST parsing
3. Extracting TypeScript-specific constructs (imports, exports, interfaces, types)
4. Modifying cognee's task or creating custom pipeline

Complexity: High - TypeScript has different import syntax (`import`, `require`, `export`), interfaces, type definitions, etc.

## Query Implications

### What Works
- Finding TypeScript files by name
- Searching within TypeScript source code content
- Graph queries that don't rely on dependency relationships

### What Doesn't Work
- "What does X import?"
- "What functions does Y provide?"
- Dependency graph traversal for TypeScript files
- Cross-file relationship queries

## Recommendation

For now, use Python-only ingestion for structural queries:
```bash
uv run python main.py ingest --languages python
```

For TypeScript content search, either:
1. Accept stub-level indexing (source code searchable, no structure)
2. Enable `--include-docs` for LLM-based entity extraction

Monitor cognee releases for TypeScript support improvements.

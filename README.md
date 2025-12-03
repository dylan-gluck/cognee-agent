# Cognee Agent - Codebase Knowledge Graph

Build and query a knowledge graph from your codebase using [Cognee](https://github.com/topoteretes/cognee).

## Setup

```bash
uv sync
cp .env.example .env  # configure your settings
```

## Configuration (.env)

```
LLM_API_KEY="your-openai-key"
DB_PROVIDER="sqlite"
DB_NAME="project-name"
SYSTEM_ROOT_DIRECTORY="/path/to/store/db"
PROJECT_ROOT_DIRECTORY="/path/to/codebase"

BATCH_SIZE="5"                    # Lower = less memory, slower
GRAPH_OUTPUT_PATH="./codebase_graph.html"
LOG_FILE="./cognee.log"           # All library logs go here
EXCLUDED_PATHS="**/node_modules/**,.venv/**,..."
SUPPORTED_LANGUAGES=""            # Empty = all languages
INCLUDE_DOCS="false"
```

## Usage

```bash
# Ingest codebase into knowledge graph
uv run python main.py ingest

# With CLI overrides
uv run python main.py ingest --batch-size 3 --path /some/repo
uv run python main.py ingest --languages python,typescript  # Filter languages
uv run python main.py ingest --include-docs  # Process docs with LLM extraction

# Query - natural language answer (default)
uv run python main.py query "What are the main API endpoints?"

# Query - different search types
uv run python main.py query -t code "authentication"    # File matches
uv run python main.py query -t graph "How does auth work?"  # NL answer
uv run python main.py query -t rag "user validation"    # RAG-based
uv run python main.py query -t chunks "error handling"  # Raw chunks

# Clear all data
uv run python main.py prune
```

## Dev

```bash
uv run ruff check main.py
uv run ruff format main.py
uv run ty check main.py
```

## Search Types

| Type | Returns | Use Case |
|------|---------|----------|
| `graph` | Natural language answer | Complex questions, analysis (default) |
| `rag` | RAG-based answer | Direct document retrieval |
| `code` | File matches | Find functions, classes |
| `chunks` | Raw text passages | Finding specific content |
| `cypher` | Graph query results | Advanced graph traversal |

## Supported Languages

| Language | AST Extraction | Features |
|----------|----------------|----------|
| Python | Full | imports, classes, functions, dependencies |
| TypeScript | Full | imports, exports, classes, functions, interfaces, types, enums, methods |
| JavaScript | File-level | source code indexing only |
| Java, C#, Go, Rust, C/C++ | File-level | source code indexing only |

### TypeScript Support

Full AST extraction via `typescript_extractor` module using tree-sitter:

- **Imports**: default, namespace, named, side-effect, type-only
- **Exports**: named, default, re-exports, type-only
- **Functions**: declarations, arrow functions, function expressions, async
- **Classes**: declarations, abstract, methods (static/async/private/getters/setters)
- **Types**: interfaces, type aliases, enums

```python
from typescript_extractor import get_typescript_dependencies

code_file = await get_typescript_dependencies(
    repo_path="/path/to/repo",
    script_path="/path/to/file.ts",
    detailed_extraction=True
)
```

## Pipelines

**Code pipeline** (default): Parses source files → extracts dependencies → stores in graph

**Docs pipeline** (`--include-docs`): Processes non-code files (md, txt, json, yaml...) → chunks → LLM entity extraction → summarization

## Notes

Data persists between runs. Use `prune` command to reset.
Logs written to `LOG_FILE` (default: `./cognee.log`).

### Cognee Concepts
- **Dataset**: Project-level containers for organization, permissions, processing
- **DataPoint**: Atomic unit of knowledge with content and context
- **Task**: Building blocks that transform data in pipelines
- **Pipeline**: Orchestrated workflow of tasks

Docs: https://docs.cognee.ai/core-concepts/main-operations/add

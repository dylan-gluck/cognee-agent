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
EXCLUDED_PATHS="**/node_modules/**,.venv/**,..."
SUPPORTED_LANGUAGES="python,typescript"
INCLUDE_DOCS="false"
```

## Usage

```bash
# Ingest codebase into knowledge graph
uv run python main.py ingest

# With CLI overrides
uv run python main.py ingest --batch-size 3 --path /some/repo --include-docs

# Query the graph
uv run python main.py query "What are the main API endpoints?"

# Clear all data
uv run python main.py prune
```

## Dev

```bash
uv run ruff check main.py
uv run ruff format main.py
uv run ty check main.py
```

## Notes

Data persists between runs. Use `prune` command to reset.

### Cognee Concepts
- **Dataset**: Project-level containers for organization, permissions, processing
- **DataPoint**: Atomic unit of knowledge with content and context
- **Task**: Building blocks that transform data in pipelines
- **Pipeline**: Orchestrated workflow of tasks

Docs: https://docs.cognee.ai/core-concepts/main-operations/add

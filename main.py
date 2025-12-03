import argparse
import asyncio
import logging
import os
import sys
from typing import Optional

from dotenv import load_dotenv

load_dotenv()

# Configure structlog BEFORE any cognee imports
import structlog  # noqa: E402

LOG_FILE = os.getenv("LOG_FILE", "./cognee.log")
_log_file = open(LOG_FILE, "a")  # noqa: SIM115

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
    logger_factory=structlog.PrintLoggerFactory(file=_log_file),
    cache_logger_on_first_use=True,
)

# Config from ENV
REPO_PATH = os.getenv("PROJECT_ROOT_DIRECTORY", ".")
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "10"))
GRAPH_OUTPUT_PATH = os.getenv("GRAPH_OUTPUT_PATH", "./codebase_graph.html")
_default_excludes = ",".join(
    [
        "**/node_modules/**",
        "**/.venv/**",
        "**/.git/**",
        "**/dist/**",
        "**/build/**",
        "**/.next/**",
        "**/.sst/**",
        "**/coverage/**",
        "**/__pycache__/**",
    ]
)
EXCLUDED_PATHS = [
    p for p in os.getenv("EXCLUDED_PATHS", _default_excludes).split(",") if p
]
# None = all languages, list = filter to specific languages
_langs = os.getenv("SUPPORTED_LANGUAGES", "").strip()
SUPPORTED_LANGUAGES: list[str] | None = _langs.split(",") if _langs else None
INCLUDE_DOCS = os.getenv("INCLUDE_DOCS", "false").lower() == "true"

# Search type mapping
SEARCH_TYPES = {
    "code": "CODE",  # File matches with code context
    "graph": "GRAPH_COMPLETION",  # Natural language answers (default)
    "rag": "RAG_COMPLETION",  # RAG-based answers
    "chunks": "CHUNKS",  # Raw text chunks
    "cypher": "CYPHER",  # Direct graph queries
}


def setup_logging():
    """Route stdlib logs to file, keep stdout clean."""
    logging.basicConfig(
        level=logging.WARNING,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        handlers=[logging.FileHandler(LOG_FILE, mode="a")],
        force=True,
    )


def log(msg: str):
    """Print to stdout intentionally."""
    print(msg, file=sys.stdout)


async def ingest_codebase(
    repo_path: str = REPO_PATH,
    batch_size: int = BATCH_SIZE,
    include_docs: bool = INCLUDE_DOCS,
    excluded_paths: Optional[list[str]] = None,
    supported_languages: Optional[list[str]] = None,
    graph_output_path: str = GRAPH_OUTPUT_PATH,
):
    """Ingest codebase into knowledge graph. Data persists between runs."""
    from cognee.api.v1.visualize.visualize import visualize_graph
    from cognee.infrastructure.databases.relational import get_relational_engine
    from cognee.infrastructure.llm import get_max_chunk_tokens
    from cognee.low_level import setup
    from cognee.modules.cognify.config import get_cognify_config
    from cognee.modules.data.methods import create_dataset
    from cognee.modules.pipelines import run_tasks
    from cognee.modules.pipelines.tasks.task import Task
    from cognee.modules.users.methods import get_default_user
    from cognee.shared.data_models import KnowledgeGraph
    from cognee.tasks.documents import classify_documents, extract_chunks_from_documents
    from cognee.tasks.graph import extract_graph_from_data
    from cognee.tasks.ingestion import ingest_data
    from repo_processor import get_non_py_files, get_repo_file_dependencies
    from cognee.tasks.storage import add_data_points
    from cognee.tasks.summarization import summarize_text

    excluded_paths = excluded_paths if excluded_paths is not None else EXCLUDED_PATHS
    supported_languages = (
        supported_languages if supported_languages is not None else SUPPORTED_LANGUAGES
    )

    await setup()

    cognee_config = get_cognify_config()
    user = await get_default_user()

    tasks = [
        Task(
            get_repo_file_dependencies,
            detailed_extraction=True,
            supported_languages=supported_languages,
            excluded_paths=excluded_paths,
        ),
        Task(add_data_points, task_config={"batch_size": batch_size}),
    ]

    if include_docs:
        non_code_tasks = [
            Task(get_non_py_files, task_config={"batch_size": batch_size}),
            Task(ingest_data, dataset_name="repo_docs", user=user),
            Task(classify_documents),
            Task(extract_chunks_from_documents, max_chunk_size=get_max_chunk_tokens()),
            Task(
                extract_graph_from_data,
                graph_model=KnowledgeGraph,
                task_config={"batch_size": batch_size},
            ),
            Task(
                summarize_text,
                summarization_model=cognee_config.summarization_model,
                task_config={"batch_size": batch_size},
            ),
        ]

    dataset_name = "codebase"
    db_engine = get_relational_engine()
    async with db_engine.get_async_session() as session:
        dataset = await create_dataset(dataset_name, user, session)  # type: ignore[arg-type]

    if include_docs:
        log("Processing non-code files...")
        async for status in run_tasks(
            non_code_tasks, dataset.id, repo_path, user, "cognify_pipeline"
        ):
            log(f"  {status.pipeline_run_id}: {status.status}")

    log("Processing code files...")
    async for status in run_tasks(
        tasks,
        dataset.id,
        repo_path,
        user,
        "cognify_code_pipeline",
        incremental_loading=False,
    ):
        log(f"  {status.pipeline_run_id}: {status.status}")

    log(f"Generating graph: {graph_output_path}")
    await visualize_graph(graph_output_path)
    log("Done.")


async def query_codebase(query: str, search_type: str = "graph"):
    """Query the knowledge graph."""
    import cognee
    from cognee import SearchType
    from cognee.low_level import setup

    await setup()

    st = getattr(SearchType, SEARCH_TYPES.get(search_type, "GRAPH_COMPLETION"))
    results = await cognee.search(query_type=st, query_text=query)
    return results, search_type


def format_results(results, search_type: str):
    """Format results based on search type."""
    if not results:
        log("No results found.")
        return

    if search_type in ("graph", "rag"):
        # Natural language answer
        for r in results:
            if hasattr(r, "search_result"):
                log(r.search_result)
            elif isinstance(r, dict) and "search_result" in r:
                log(r["search_result"])
            else:
                log(str(r))
    elif search_type == "code":
        # File matches
        for r in results:
            name = r.get("name", "") if isinstance(r, dict) else getattr(r, "name", "")
            log(f"- {name}")
    elif search_type == "chunks":
        # Text chunks
        for i, r in enumerate(results, 1):
            text = r.get("text", str(r)) if isinstance(r, dict) else str(r)
            log(f"[{i}] {text[:200]}...")
    else:
        # Default: dump as-is
        for r in results:
            log(str(r))


async def prune_data():
    """Clear all data (use with caution)."""
    import cognee

    await cognee.prune.prune_data()
    await cognee.prune.prune_system(metadata=True)
    log("Data pruned.")


def main():
    setup_logging()

    parser = argparse.ArgumentParser(description="Codebase Knowledge Graph")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # ingest
    ingest_parser = subparsers.add_parser("ingest", help="Ingest codebase into graph")
    ingest_parser.add_argument("--path", default=REPO_PATH, help="Repo path")
    ingest_parser.add_argument("--batch-size", type=int, default=BATCH_SIZE)
    ingest_parser.add_argument(
        "--include-docs", action="store_true", default=INCLUDE_DOCS
    )
    ingest_parser.add_argument(
        "--output", default=GRAPH_OUTPUT_PATH, help="Graph HTML path"
    )
    ingest_parser.add_argument(
        "--languages",
        default=None,
        help="Comma-sep languages (python,typescript,...). Empty=all",
    )

    # query
    query_parser = subparsers.add_parser("query", help="Query the knowledge graph")
    query_parser.add_argument("query", help="Query text")
    query_parser.add_argument(
        "-t",
        "--type",
        choices=list(SEARCH_TYPES.keys()),
        default="graph",
        help="Search type: graph (NL answer), code (files), rag, chunks, cypher",
    )

    # prune
    subparsers.add_parser("prune", help="Clear all data")

    args = parser.parse_args()

    if args.command == "ingest":
        langs = args.languages.split(",") if args.languages else None
        asyncio.run(
            ingest_codebase(
                repo_path=args.path,
                batch_size=args.batch_size,
                include_docs=args.include_docs,
                graph_output_path=args.output,
                supported_languages=langs,
            )
        )
    elif args.command == "query":
        results, st = asyncio.run(query_codebase(args.query, args.type))
        format_results(results, st)
    elif args.command == "prune":
        asyncio.run(prune_data())


if __name__ == "__main__":
    main()

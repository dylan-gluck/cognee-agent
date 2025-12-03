import os
import argparse
import asyncio
from typing import Optional

from dotenv import load_dotenv

load_dotenv()

# Config from ENV
REPO_PATH = os.getenv("PROJECT_ROOT_DIRECTORY", ".")
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "10"))
GRAPH_OUTPUT_PATH = os.getenv("GRAPH_OUTPUT_PATH", "./codebase_graph.html")
EXCLUDED_PATHS = os.getenv(
    "EXCLUDED_PATHS",
    "**/node_modules/**,.sst/**,.next/**,.devenv/**,.claude/**,.cursor/**,.ruff_cache/**,.venv/**,**.egg-info",
).split(",")
SUPPORTED_LANGUAGES = os.getenv("SUPPORTED_LANGUAGES", "python,typescript").split(",")
INCLUDE_DOCS = os.getenv("INCLUDE_DOCS", "false").lower() == "true"


async def ingest_codebase(
    repo_path: str = REPO_PATH,
    batch_size: int = BATCH_SIZE,
    include_docs: bool = INCLUDE_DOCS,
    excluded_paths: Optional[list[str]] = None,
    supported_languages: Optional[list[str]] = None,
    graph_output_path: str = GRAPH_OUTPUT_PATH,
):
    """Ingest codebase into knowledge graph. Data persists between runs."""
    from cognee.low_level import setup
    from cognee.api.v1.visualize.visualize import visualize_graph
    from cognee.modules.cognify.config import get_cognify_config
    from cognee.modules.pipelines import run_tasks
    from cognee.modules.pipelines.tasks.task import Task
    from cognee.modules.users.methods import get_default_user
    from cognee.shared.data_models import KnowledgeGraph
    from cognee.modules.data.methods import create_dataset
    from cognee.tasks.documents import classify_documents, extract_chunks_from_documents
    from cognee.tasks.graph import extract_graph_from_data
    from cognee.tasks.ingestion import ingest_data
    from cognee.tasks.repo_processor import get_non_py_files, get_repo_file_dependencies
    from cognee.tasks.storage import add_data_points
    from cognee.tasks.summarization import summarize_text
    from cognee.infrastructure.llm import get_max_chunk_tokens
    from cognee.infrastructure.databases.relational import get_relational_engine

    excluded_paths = excluded_paths or EXCLUDED_PATHS
    supported_languages = supported_languages or SUPPORTED_LANGUAGES

    # Setup without pruning - data persists
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
        print("Processing non-code files...")
        async for status in run_tasks(
            non_code_tasks, dataset.id, repo_path, user, "cognify_pipeline"
        ):
            print(f"  {status.pipeline_run_id}: {status.status}")

    print("Processing code files...")
    async for status in run_tasks(
        tasks,
        dataset.id,
        repo_path,
        user,
        "cognify_code_pipeline",
        incremental_loading=False,
    ):
        print(f"  {status.pipeline_run_id}: {status.status}")

    # Visualization at end of ingest
    print(f"Generating graph visualization: {graph_output_path}")
    await visualize_graph(graph_output_path)
    print("Ingest complete.")


async def query_codebase(query: str):
    """Query the knowledge graph."""
    import cognee
    from cognee import SearchType
    from cognee.low_level import setup

    await setup()

    results = await cognee.search(
        query_type=SearchType.CODE,
        query_text=query,
    )
    return results


async def prune_data():
    """Clear all data (use with caution)."""
    import cognee

    await cognee.prune.prune_data()
    await cognee.prune.prune_system(metadata=True)
    print("Data pruned.")


def main():
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

    # query
    query_parser = subparsers.add_parser("query", help="Query the knowledge graph")
    query_parser.add_argument("query", help="Query text")

    # prune
    subparsers.add_parser("prune", help="Clear all data")

    args = parser.parse_args()

    if args.command == "ingest":
        asyncio.run(
            ingest_codebase(
                repo_path=args.path,
                batch_size=args.batch_size,
                include_docs=args.include_docs,
                graph_output_path=args.output,
            )
        )
    elif args.command == "query":
        results = asyncio.run(query_codebase(args.query))
        for r in results:
            print(f"- {r.get('name', r)}")
    elif args.command == "prune":
        asyncio.run(prune_data())


if __name__ == "__main__":
    main()

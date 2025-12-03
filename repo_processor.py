"""
Local repo processor that extends cognee's processing with TypeScript support.

This module provides a drop-in replacement for cognee.tasks.repo_processor.get_repo_file_dependencies
that adds full TypeScript/TSX extraction using our typescript_extractor module.
"""
import os
import aiofiles
from typing import AsyncGenerator, Optional, List
from uuid import NAMESPACE_OID, uuid5

from cognee.low_level import DataPoint
from cognee.shared.CodeGraphEntities import Repository, CodeFile
from cognee.tasks.repo_processor.get_local_dependencies import get_local_script_dependencies

from typescript_extractor import get_typescript_dependencies

# Re-export for convenience
from cognee.tasks.repo_processor import get_non_py_files  # noqa: F401


# Constants from cognee
EXCLUDED_DIRS = {
    ".venv", "venv", "env", ".env",
    "site-packages", "node_modules",
    "dist", "build", ".git",
    "__pycache__", ".next", ".sst",
}

DEFAULT_LANGUAGE_CONFIG = {
    "python": [".py"],
    "javascript": [".js", ".jsx"],
    "typescript": [".ts", ".tsx"],
    "java": [".java"],
    "csharp": [".cs"],
    "go": [".go"],
    "rust": [".rs"],
    "cpp": [".cpp", ".c", ".h", ".hpp"],
    "c": [".c", ".h"],
}


def is_test_file(file_path: str) -> bool:
    """Check if file is a test file."""
    name = os.path.basename(file_path)
    return (
        name.startswith("test_") or
        name.endswith("_test.py") or
        name.endswith("_test.ts") or
        name.endswith("_test.tsx") or
        name.endswith("_test.js") or
        ".test." in name or
        ".spec." in name
    )


async def get_source_code_files(
    repo_path: str,
    language_config: dict = DEFAULT_LANGUAGE_CONFIG,
    supported_languages: Optional[List[str]] = None,
    excluded_paths: Optional[List[str]] = None,
) -> List[tuple[str, str]]:
    """
    Get all source code files in the repository.

    Returns list of (file_path, language) tuples.
    """
    import fnmatch

    excluded_paths = excluded_paths or []
    files = []

    # Build extension to language map
    ext_to_lang = {}
    for lang, exts in language_config.items():
        if supported_languages is None or lang in supported_languages:
            for ext in exts:
                ext_to_lang[ext] = lang

    for root, dirs, filenames in os.walk(repo_path):
        # Filter out excluded directories
        dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS]

        for filename in filenames:
            file_path = os.path.join(root, filename)
            relative_path = os.path.relpath(file_path, repo_path)

            # Check excluded paths (glob patterns)
            excluded = False
            for pattern in excluded_paths:
                if fnmatch.fnmatch(relative_path, pattern):
                    excluded = True
                    break

            if excluded:
                continue

            # Check if it's a test file
            if is_test_file(file_path):
                continue

            # Check extension
            _, ext = os.path.splitext(filename)
            if ext in ext_to_lang:
                files.append((file_path, ext_to_lang[ext]))

    return files


async def make_codefile_stub(
    repo_path: str,
    file_path: str,
    language: str
) -> CodeFile:
    """Create a CodeFile stub for unsupported languages."""
    try:
        async with aiofiles.open(file_path, "r", encoding="utf-8") as f:
            source_code = await f.read()
    except Exception:
        source_code = ""

    relative_path = file_path[len(repo_path) + 1:]
    return CodeFile(
        id=uuid5(NAMESPACE_OID, file_path),
        name=relative_path,
        file_path=file_path,
        language=language,
        source_code=source_code,
    )


async def get_repo_file_dependencies(
    repo_path: str,
    detailed_extraction: bool = False,
    supported_languages: Optional[List[str]] = None,
    excluded_paths: Optional[List[str]] = None,
) -> AsyncGenerator[DataPoint, None]:
    """
    Process repository and extract code dependencies.

    This is a drop-in replacement for cognee.tasks.repo_processor.get_repo_file_dependencies
    that adds TypeScript support via our local typescript_extractor.

    Args:
        repo_path: Path to repository root
        detailed_extraction: If True, extract imports/functions/classes
        supported_languages: List of languages to process (None = all)
        excluded_paths: Glob patterns to exclude

    Yields:
        Repository node, then CodeFile nodes for each source file
    """
    import asyncio

    # Yield repository first
    repo = Repository(
        id=uuid5(NAMESPACE_OID, repo_path),
        path=repo_path,
    )
    yield repo

    # Get all source files
    source_files = await get_source_code_files(
        repo_path,
        supported_languages=supported_languages,
        excluded_paths=excluded_paths,
    )

    # Process in chunks of 100
    chunk_size = 100
    for i in range(0, len(source_files), chunk_size):
        chunk = source_files[i:i + chunk_size]
        tasks = []

        for file_path, language in chunk:
            if language == "python":
                # Use cognee's Python extractor
                tasks.append(
                    get_local_script_dependencies(repo_path, file_path, detailed_extraction)
                )
            elif language == "typescript":
                # Use our TypeScript extractor!
                tasks.append(
                    get_typescript_dependencies(repo_path, file_path, detailed_extraction)
                )
            else:
                # Stub for other languages
                tasks.append(
                    make_codefile_stub(repo_path, file_path, language)
                )

        # Execute chunk concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, BaseException):
                continue  # Skip failed files
            code_file = result  # type: CodeFile
            code_file.part_of = repo
            yield code_file

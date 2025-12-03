import os
import aiofiles
import tree_sitter_typescript as tstypescript
from tree_sitter import Language, Parser, Tree
from cognee.shared.logging_utils import get_logger

logger = get_logger()

TS_LANGUAGE = Language(tstypescript.language_typescript())
TSX_LANGUAGE = Language(tstypescript.language_tsx())


class TypeScriptFileParser:
    """
    Handles the parsing of TypeScript/TSX files into source code and an abstract syntax tree
    representation. Public methods include:

    - parse_file: Parses a .ts or .tsx file and returns its source code and syntax tree representation.
    """

    def __init__(self):
        self.parsed_files = {}

    async def parse_file(self, file_path: str) -> tuple[str, Tree]:
        """
        Parse a TypeScript/TSX file and return its source code along with its syntax tree representation.

        If the file has already been parsed, retrieve the result from memory instead of reading
        the file again. Uses TSX parser for .tsx files, TS parser for .ts files.

        Parameters:
        -----------

            - file_path (str): The path of the file to parse.

        Returns:
        --------

            - tuple[str, Tree]: A tuple containing the source code of the file and its
              corresponding syntax tree representation.
        """
        if file_path not in self.parsed_files:
            # Determine which parser to use based on file extension
            is_tsx = file_path.endswith('.tsx')
            language = TSX_LANGUAGE if is_tsx else TS_LANGUAGE
            source_code_parser = Parser(language)

            source_code = await get_source_code(file_path)
            if source_code is None:
                raise ValueError(f"Failed to read source code from {file_path}")

            source_code_tree = source_code_parser.parse(bytes(source_code, "utf-8"))
            self.parsed_files[file_path] = (source_code, source_code_tree)

        return self.parsed_files[file_path]


async def get_source_code(file_path: str) -> str | None:
    """
    Read source code from a file asynchronously.

    This function attempts to open a file specified by the given file path, read its
    contents, and return the source code. In case of any errors during the file reading
    process, it logs an error message and returns None.

    Parameters:
    -----------

        - file_path (str): The path to the file from which to read the source code.

    Returns:
    --------

        Returns the contents of the file as a string if successful, or None if an error
        occurs.
    """
    try:
        async with aiofiles.open(file_path, "r", encoding="utf-8") as f:
            source_code = await f.read()
            return source_code
    except Exception as error:
        logger.error(f"Error reading file {file_path}: {str(error)}")
        return None

from uuid import NAMESPACE_OID, uuid5
from tree_sitter import Node
from cognee.shared.CodeGraphEntities import (
    CodeFile,
    ImportStatement,
    FunctionDefinition,
    ClassDefinition,
)
from cognee.shared.logging_utils import get_logger

from .parser import TypeScriptFileParser
from .node_handlers import (
    extract_import_from_node,
    extract_function_from_node,
    extract_class_from_node,
)

logger = get_logger()


async def get_typescript_dependencies(
    repo_path: str,
    script_path: str,
    detailed_extraction: bool = False
) -> CodeFile:
    """
    Extract dependencies from TypeScript/TSX file.

    This function parses a TypeScript or TSX file and extracts its dependencies,
    including imports, function definitions, and class definitions. It mirrors the
    behavior of get_local_script_dependencies for Python files.

    Parameters:
    -----------

        - repo_path (str): Path to repository root
        - script_path (str): Absolute path to .ts/.tsx file
        - detailed_extraction (bool): If True, extract imports/functions/classes
                                    If False, just return CodeFile with source_code

    Returns:
    --------

        - CodeFile: CodeFile with populated depends_on, provides_function_definition,
                   provides_class_definition lists (if detailed_extraction=True)
    """
    code_file_parser = TypeScriptFileParser()
    source_code, source_code_tree = await code_file_parser.parse_file(script_path)

    # Calculate relative path
    file_path_relative_to_repo = script_path[len(repo_path) + 1:]

    if not detailed_extraction:
        # Simple mode: just return the file with source code
        code_file_node = CodeFile(
            id=uuid5(NAMESPACE_OID, script_path),
            name=file_path_relative_to_repo,
            source_code=source_code,
            file_path=script_path,
            language="typescript",
        )
        return code_file_node

    # Detailed mode: extract all code parts
    code_file_node = CodeFile(
        id=uuid5(NAMESPACE_OID, script_path),
        name=file_path_relative_to_repo,
        source_code=None,  # Don't duplicate source code when extracting parts
        file_path=script_path,
        language="typescript",
    )

    # Extract code parts from AST
    root_node = source_code_tree.root_node
    await _extract_code_parts(root_node, script_path, code_file_node)

    return code_file_node


async def _extract_code_parts(
    tree_root: Node,
    script_path: str,
    code_file: CodeFile
) -> None:
    """
    Extract code parts from a given AST node tree and populate the CodeFile.

    Iterates through children of the tree root and extracts import statements,
    function definitions, and class definitions. For export statements, it
    recursively extracts the exported declarations.

    Parameters:
    -----------

        - tree_root (Node): The root node of the AST tree containing code parts to extract
        - script_path (str): The file path of the script from which the AST was generated
        - code_file (CodeFile): The CodeFile object to populate with extracted parts
    """
    for child_node in tree_root.children:
        try:
            # Handle import statements
            if child_node.type == "import_statement":
                imports = extract_import_from_node(child_node, script_path)
                for import_stmt in imports:
                    import_stmt.file_path = script_path
                    code_file.depends_on.append(import_stmt)

            # Handle function declarations
            elif child_node.type == "function_declaration":
                function_def = extract_function_from_node(child_node, script_path)
                if function_def:
                    function_def.file_path = script_path
                    code_file.provides_function_definition.append(function_def)

            # Handle lexical declarations (const, let, var) that might contain arrow functions
            elif child_node.type == "lexical_declaration":
                function_def = extract_function_from_node(child_node, script_path)
                if function_def:
                    function_def.file_path = script_path
                    code_file.provides_function_definition.append(function_def)

            # Handle class declarations
            elif child_node.type == "class_declaration":
                class_def = extract_class_from_node(child_node, script_path)
                if class_def:
                    class_def.file_path = script_path
                    code_file.provides_class_definition.append(class_def)

            # Handle abstract class declarations (TypeScript specific)
            elif child_node.type == "abstract_class_declaration":
                class_def = extract_class_from_node(child_node, script_path)
                if class_def:
                    class_def.file_path = script_path
                    code_file.provides_class_definition.append(class_def)

            # Handle export statements - recursively extract from the exported declaration
            elif child_node.type == "export_statement":
                # Look for function or class declarations within the export
                for export_child in child_node.children:
                    if export_child.type == "function_declaration":
                        function_def = extract_function_from_node(export_child, script_path)
                        if function_def:
                            function_def.file_path = script_path
                            code_file.provides_function_definition.append(function_def)

                    elif export_child.type == "class_declaration":
                        class_def = extract_class_from_node(export_child, script_path)
                        if class_def:
                            class_def.file_path = script_path
                            code_file.provides_class_definition.append(class_def)

                    elif export_child.type == "abstract_class_declaration":
                        class_def = extract_class_from_node(export_child, script_path)
                        if class_def:
                            class_def.file_path = script_path
                            code_file.provides_class_definition.append(class_def)

                    elif export_child.type == "lexical_declaration":
                        function_def = extract_function_from_node(export_child, script_path)
                        if function_def:
                            function_def.file_path = script_path
                            code_file.provides_function_definition.append(function_def)

        except Exception as e:
            logger.error(f"Error processing node type {child_node.type} at {script_path}: {str(e)}")
            continue

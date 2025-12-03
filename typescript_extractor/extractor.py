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
from .models import TypeScriptCodeFile
from .node_handlers import (
    extract_import_from_node,
    extract_function_from_node,
    extract_class_from_node,
    extract_require_from_node,
    extract_reexport_from_node,
    extract_interface_from_node,
    extract_type_alias_from_node,
    extract_enum_from_node,
    extract_export_from_node,
    extract_methods_from_class,
)

logger = get_logger()


async def get_typescript_dependencies(
    repo_path: str,
    script_path: str,
    detailed_extraction: bool = False
) -> TypeScriptCodeFile:
    """
    Extract dependencies from TypeScript/TSX file.

    This function parses a TypeScript or TSX file and extracts its dependencies,
    including imports, function definitions, class definitions, interfaces, type aliases,
    and enums. It mirrors the behavior of get_local_script_dependencies for Python files.

    Parameters:
    -----------

        - repo_path (str): Path to repository root
        - script_path (str): Absolute path to .ts/.tsx file
        - detailed_extraction (bool): If True, extract imports/functions/classes/interfaces/types/enums
                                    If False, just return TypeScriptCodeFile with source_code

    Returns:
    --------

        - TypeScriptCodeFile: TypeScriptCodeFile with populated depends_on, provides_function_definition,
                             provides_class_definition, provides_interface_definition,
                             provides_type_alias, provides_enum_definition lists
                             (if detailed_extraction=True)
    """
    code_file_parser = TypeScriptFileParser()
    source_code, source_code_tree = await code_file_parser.parse_file(script_path)

    # Calculate relative path
    file_path_relative_to_repo = script_path[len(repo_path) + 1:]

    if not detailed_extraction:
        # Simple mode: just return the file with source code
        code_file_node = TypeScriptCodeFile(
            id=uuid5(NAMESPACE_OID, script_path),
            name=file_path_relative_to_repo,
            source_code=source_code,
            file_path=script_path,
            language="typescript",
        )
        return code_file_node

    # Detailed mode: extract all code parts
    code_file_node = TypeScriptCodeFile(
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
    code_file: TypeScriptCodeFile
) -> None:
    """
    Extract code parts from a given AST node tree and populate the TypeScriptCodeFile.

    Iterates through children of the tree root and extracts import statements,
    function definitions, class definitions, interfaces, type aliases, and enums.
    For export statements, it recursively extracts the exported declarations.

    Parameters:
    -----------

        - tree_root (Node): The root node of the AST tree containing code parts to extract
        - script_path (str): The file path of the script from which the AST was generated
        - code_file (TypeScriptCodeFile): The TypeScriptCodeFile object to populate with extracted parts
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

            # Handle lexical declarations (const, let, var) that might contain arrow functions or require()
            elif child_node.type == "lexical_declaration":
                # First check if it's a require() call (Phase 2)
                require_imports = extract_require_from_node(child_node, script_path)
                if require_imports:
                    for import_stmt in require_imports:
                        import_stmt.file_path = script_path
                        code_file.depends_on.append(import_stmt)
                else:
                    # If not a require, check for arrow function
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

                    # Phase 4: Extract methods from the class
                    methods = extract_methods_from_class(child_node, class_def.name, script_path)
                    for method in methods:
                        method.file_path = script_path
                        code_file.provides_method_definition.append(method)

            # Handle abstract class declarations (TypeScript specific)
            elif child_node.type == "abstract_class_declaration":
                class_def = extract_class_from_node(child_node, script_path)
                if class_def:
                    class_def.file_path = script_path
                    code_file.provides_class_definition.append(class_def)

                    # Phase 4: Extract methods from the class
                    methods = extract_methods_from_class(child_node, class_def.name, script_path)
                    for method in methods:
                        method.file_path = script_path
                        code_file.provides_method_definition.append(method)

            # Handle interface declarations (TypeScript specific)
            elif child_node.type == "interface_declaration":
                interface_def = extract_interface_from_node(child_node, script_path)
                if interface_def:
                    interface_def.file_path = script_path
                    code_file.provides_interface_definition.append(interface_def)

            # Handle type alias declarations (TypeScript specific)
            elif child_node.type == "type_alias_declaration":
                type_alias_def = extract_type_alias_from_node(child_node, script_path)
                if type_alias_def:
                    type_alias_def.file_path = script_path
                    code_file.provides_type_alias.append(type_alias_def)

            # Handle enum declarations (TypeScript specific)
            elif child_node.type == "enum_declaration":
                enum_def = extract_enum_from_node(child_node, script_path)
                if enum_def:
                    enum_def.file_path = script_path
                    code_file.provides_enum_definition.append(enum_def)

            # Handle export statements - recursively extract from the exported declaration
            elif child_node.type == "export_statement":
                # Phase 2: First check if this is a re-export (has module path)
                reexport_imports = extract_reexport_from_node(child_node, script_path)
                if reexport_imports:
                    for import_stmt in reexport_imports:
                        import_stmt.file_path = script_path
                        code_file.depends_on.append(import_stmt)
                else:
                    # Phase 4: Extract export statements (named, default, type-only)
                    export_stmts = extract_export_from_node(child_node, script_path)
                    for export_stmt in export_stmts:
                        export_stmt.file_path = script_path
                        code_file.exports.append(export_stmt)

                    # Not a re-export, look for function or class declarations within the export
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

                                # Phase 4: Extract methods from exported class
                                methods = extract_methods_from_class(export_child, class_def.name, script_path)
                                for method in methods:
                                    method.file_path = script_path
                                    code_file.provides_method_definition.append(method)

                        elif export_child.type == "abstract_class_declaration":
                            class_def = extract_class_from_node(export_child, script_path)
                            if class_def:
                                class_def.file_path = script_path
                                code_file.provides_class_definition.append(class_def)

                                # Phase 4: Extract methods from exported abstract class
                                methods = extract_methods_from_class(export_child, class_def.name, script_path)
                                for method in methods:
                                    method.file_path = script_path
                                    code_file.provides_method_definition.append(method)

                        elif export_child.type == "lexical_declaration":
                            function_def = extract_function_from_node(export_child, script_path)
                            if function_def:
                                function_def.file_path = script_path
                                code_file.provides_function_definition.append(function_def)

                        # Phase 3: Handle exported TypeScript-specific constructs
                        elif export_child.type == "interface_declaration":
                            interface_def = extract_interface_from_node(export_child, script_path)
                            if interface_def:
                                interface_def.file_path = script_path
                                code_file.provides_interface_definition.append(interface_def)

                        elif export_child.type == "type_alias_declaration":
                            type_alias_def = extract_type_alias_from_node(export_child, script_path)
                            if type_alias_def:
                                type_alias_def.file_path = script_path
                                code_file.provides_type_alias.append(type_alias_def)

                        elif export_child.type == "enum_declaration":
                            enum_def = extract_enum_from_node(export_child, script_path)
                            if enum_def:
                                enum_def.file_path = script_path
                                code_file.provides_enum_definition.append(enum_def)

        except Exception as e:
            logger.error(f"Error processing node type {child_node.type} at {script_path}: {str(e)}")
            continue

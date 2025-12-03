from tree_sitter import Node
from cognee.shared.CodeGraphEntities import (
    ImportStatement,
    FunctionDefinition,
    ClassDefinition,
)
from cognee.shared.logging_utils import get_logger

logger = get_logger()


def find_node(nodes: list[Node], condition: callable) -> Node | None:
    """
    Find and return the first node that satisfies the given condition.

    Iterate through the provided list of nodes and return the first node for which the
    condition callable returns True. If no such node is found, return None.

    Parameters:
    -----------

        - nodes (list[Node]): A list of Node objects to search through.
        - condition (callable): A callable that takes a Node and returns a boolean
          indicating if the node meets specified criteria.

    Returns:
    --------

        - Node | None: The first Node that matches the condition, or None if no such node exists.
    """
    for node in nodes:
        if condition(node):
            return node
    return None


def extract_import_from_node(node: Node, script_path: str) -> list[ImportStatement]:
    """
    Extract ImportStatement(s) from import_statement node.

    For Phase 1, handles default imports:
    - import React from 'react' → ImportStatement(name='React', module='react')

    Parameters:
    -----------

        - node (Node): The import_statement AST node
        - script_path (str): The path to the file being parsed

    Returns:
    --------

        - list[ImportStatement]: List of extracted import statements
    """
    imports = []

    try:
        # Find the module path (string literal)
        module_node = find_node(node.children, lambda n: n.type == "string")
        if not module_node:
            logger.warning(f"No module string found in import statement at {script_path}")
            return imports

        # Remove quotes from module path
        module_path = module_node.text.decode("utf-8").strip('"\'')

        # Find the import_clause which contains the imported names
        import_clause = find_node(node.children, lambda n: n.type == "import_clause")
        if not import_clause:
            # Import with no clause (e.g., import 'module')
            return imports

        # Phase 1: Handle default imports only
        # Look for direct identifier child (default import)
        identifier_node = find_node(import_clause.children, lambda n: n.type == "identifier")

        if identifier_node:
            import_name = identifier_node.text.decode("utf-8")
            import_statement = ImportStatement(
                name=import_name,
                module=module_path,
                start_point=node.start_point,
                end_point=node.end_point,
                source_code=node.text.decode("utf-8"),
                file_path=script_path,
            )
            imports.append(import_statement)

        # Phase 1: Also handle namespace imports (import * as React from 'react')
        namespace_import = find_node(import_clause.children, lambda n: n.type == "namespace_import")
        if namespace_import:
            namespace_identifier = find_node(namespace_import.children, lambda n: n.type == "identifier")
            if namespace_identifier:
                import_name = namespace_identifier.text.decode("utf-8")
                import_statement = ImportStatement(
                    name=import_name,
                    module=module_path,
                    start_point=node.start_point,
                    end_point=node.end_point,
                    source_code=node.text.decode("utf-8"),
                    file_path=script_path,
                )
                imports.append(import_statement)

    except Exception as e:
        logger.error(f"Error extracting import from node at {script_path}: {str(e)}")

    return imports


def extract_function_from_node(node: Node, script_path: str) -> FunctionDefinition | None:
    """
    Extract FunctionDefinition from function_declaration or lexical_declaration.

    Handles:
    - function foo() {} → FunctionDefinition(name='foo')
    - async function foo() {} → FunctionDefinition(name='foo')
    - const foo = () => {} → FunctionDefinition(name='foo')

    Parameters:
    -----------

        - node (Node): The function_declaration or lexical_declaration AST node
        - script_path (str): The path to the file being parsed

    Returns:
    --------

        - FunctionDefinition | None: Extracted function definition or None if extraction fails
    """
    try:
        function_name = None

        if node.type == "function_declaration":
            # Direct function declaration: function foo() {}
            name_node = node.child_by_field_name("name")
            if name_node:
                function_name = name_node.text.decode("utf-8")

        elif node.type == "lexical_declaration":
            # Variable declaration that might contain an arrow function
            # const foo = () => {}
            # Look for variable_declarator
            declarator = find_node(node.children, lambda n: n.type == "variable_declarator")
            if declarator:
                # Check if the value is an arrow_function
                arrow_function = find_node(declarator.children, lambda n: n.type == "arrow_function")
                if arrow_function:
                    # Get the name from the variable declarator
                    name_node = declarator.child_by_field_name("name")
                    if name_node:
                        function_name = name_node.text.decode("utf-8")

        if function_name:
            function_definition = FunctionDefinition(
                name=function_name,
                start_point=node.start_point,
                end_point=node.end_point,
                source_code=node.text.decode("utf-8"),
                file_path=script_path,
            )
            return function_definition

    except Exception as e:
        logger.error(f"Error extracting function from node at {script_path}: {str(e)}")

    return None


def extract_class_from_node(node: Node, script_path: str) -> ClassDefinition | None:
    """
    Extract ClassDefinition from class_declaration or abstract_class_declaration.

    Handles:
    - class Foo {} → ClassDefinition(name='Foo')
    - abstract class Foo {} → ClassDefinition(name='Foo')

    Parameters:
    -----------

        - node (Node): The class_declaration or abstract_class_declaration AST node
        - script_path (str): The path to the file being parsed

    Returns:
    --------

        - ClassDefinition | None: Extracted class definition or None if extraction fails
    """
    try:
        # Get the class name
        name_node = node.child_by_field_name("name")
        if name_node:
            class_name = name_node.text.decode("utf-8")

            class_definition = ClassDefinition(
                name=class_name,
                start_point=node.start_point,
                end_point=node.end_point,
                source_code=node.text.decode("utf-8"),
                file_path=script_path,
            )
            return class_definition

    except Exception as e:
        logger.error(f"Error extracting class from node at {script_path}: {str(e)}")

    return None

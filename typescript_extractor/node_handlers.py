from tree_sitter import Node
from cognee.shared.CodeGraphEntities import (
    ImportStatement,
    FunctionDefinition,
    ClassDefinition,
)
from cognee.shared.logging_utils import get_logger
from .models import InterfaceDefinition, TypeAliasDefinition, EnumDefinition, ExportStatement, MethodDefinition

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

        # Phase 2: Handle named imports: import { useState, useEffect } from 'react'
        named_imports = find_node(import_clause.children, lambda n: n.type == "named_imports")
        if named_imports:
            for child in named_imports.children:
                if child.type == "import_specifier":
                    # Get all identifier children
                    identifiers = [c for c in child.children if c.type == "identifier"]
                    if len(identifiers) == 2:
                        # Has alias: import { foo as bar } - use bar (the alias)
                        import_name = identifiers[1].text.decode("utf-8")
                    elif len(identifiers) == 1:
                        # No alias: import { foo } - use foo
                        import_name = identifiers[0].text.decode("utf-8")
                    else:
                        continue

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


def extract_require_from_node(node: Node, script_path: str) -> list[ImportStatement]:
    """
    Extract ImportStatement(s) from CommonJS require() calls.

    Handles:
    - const fs = require('fs') → ImportStatement(name='fs', module='fs')
    - const { readFile } = require('fs') → ImportStatement(name='readFile', module='fs')
    - const { foo, bar } = require('./utils') → 2 ImportStatements

    Parameters:
    -----------

        - node (Node): The lexical_declaration AST node containing a require call
        - script_path (str): The path to the file being parsed

    Returns:
    --------

        - list[ImportStatement]: List of extracted import statements from require()
    """
    imports = []

    try:
        # Look for variable_declarator child
        declarator = find_node(node.children, lambda n: n.type == "variable_declarator")
        if not declarator:
            return imports

        # Find call_expression (should be require())
        call_expr = find_node(declarator.children, lambda n: n.type == "call_expression")
        if not call_expr:
            return imports

        # Check if it's actually a require() call
        function_node = find_node(call_expr.children, lambda n: n.type == "identifier")
        if not function_node or function_node.text.decode("utf-8") != "require":
            return imports

        # Get the module path from arguments
        arguments = find_node(call_expr.children, lambda n: n.type == "arguments")
        if not arguments:
            return imports

        module_node = find_node(arguments.children, lambda n: n.type == "string")
        if not module_node:
            return imports

        module_path = module_node.text.decode("utf-8").strip('"\'')

        # Get the variable name(s) being assigned
        name_node = declarator.child_by_field_name("name")
        if not name_node:
            return imports

        # Handle destructured imports: const { a, b } = require('x')
        if name_node.type == "object_pattern":
            for child in name_node.children:
                if child.type == "shorthand_property_identifier_pattern":
                    import_name = child.text.decode("utf-8")
                    import_statement = ImportStatement(
                        name=import_name,
                        module=module_path,
                        start_point=node.start_point,
                        end_point=node.end_point,
                        source_code=node.text.decode("utf-8"),
                        file_path=script_path,
                    )
                    imports.append(import_statement)
                elif child.type == "pair_pattern":
                    # Handle aliased destructuring: const { foo: bar } = require('x')
                    identifiers = [c for c in child.children if c.type == "identifier" or c.type == "shorthand_property_identifier"]
                    if len(identifiers) >= 1:
                        # Use the last identifier (the alias if present)
                        import_name = identifiers[-1].text.decode("utf-8")
                        import_statement = ImportStatement(
                            name=import_name,
                            module=module_path,
                            start_point=node.start_point,
                            end_point=node.end_point,
                            source_code=node.text.decode("utf-8"),
                            file_path=script_path,
                        )
                        imports.append(import_statement)
        # Handle simple assignment: const fs = require('fs')
        elif name_node.type == "identifier":
            import_name = name_node.text.decode("utf-8")
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
        logger.error(f"Error extracting require from node at {script_path}: {str(e)}")

    return imports


def extract_reexport_from_node(node: Node, script_path: str) -> list[ImportStatement]:
    """
    Extract ImportStatement(s) from re-export statements.

    Handles:
    - export { foo } from './foo' → ImportStatement(name='foo', module='./foo')
    - export { foo as bar } from './foo' → ImportStatement(name='bar', module='./foo')
    - export * from './utils' → ImportStatement(name='*', module='./utils')

    Parameters:
    -----------

        - node (Node): The export_statement AST node with a module path
        - script_path (str): The path to the file being parsed

    Returns:
    --------

        - list[ImportStatement]: List of extracted import statements from re-exports
    """
    imports = []

    try:
        # Check if this is a re-export (has a string child indicating module path)
        module_node = find_node(node.children, lambda n: n.type == "string")
        if not module_node:
            return imports

        module_path = module_node.text.decode("utf-8").strip('"\'')

        # Check for wildcard re-export: export * from './utils'
        has_wildcard = any(child.type == "*" or child.text.decode("utf-8") == "*" for child in node.children)
        if has_wildcard:
            import_statement = ImportStatement(
                name="*",
                module=module_path,
                start_point=node.start_point,
                end_point=node.end_point,
                source_code=node.text.decode("utf-8"),
                file_path=script_path,
            )
            imports.append(import_statement)
            return imports

        # Handle named re-exports: export { foo, bar } from './utils'
        export_clause = find_node(node.children, lambda n: n.type == "export_clause")
        if export_clause:
            for child in export_clause.children:
                if child.type == "export_specifier":
                    # Get all identifier children
                    identifiers = [c for c in child.children if c.type == "identifier"]
                    if len(identifiers) == 2:
                        # Has alias: export { foo as bar } - use bar (the alias)
                        import_name = identifiers[1].text.decode("utf-8")
                    elif len(identifiers) == 1:
                        # No alias: export { foo } - use foo
                        import_name = identifiers[0].text.decode("utf-8")
                    else:
                        continue

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
        logger.error(f"Error extracting re-export from node at {script_path}: {str(e)}")

    return imports


def extract_function_from_node(node: Node, script_path: str) -> FunctionDefinition | None:
    """
    Extract FunctionDefinition from function_declaration or lexical_declaration.

    Handles:
    - function foo() {} → FunctionDefinition(name='foo')
    - async function foo() {} → FunctionDefinition(name='foo')
    - const foo = () => {} → FunctionDefinition(name='foo')
    - const foo = function() {} → FunctionDefinition(name='foo')
    - const foo = function named() {} → FunctionDefinition(name='foo')

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
            # Variable declaration that might contain an arrow function or function expression
            # const foo = () => {}
            # const foo = function() {}
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
                else:
                    # Check if the value is a function_expression
                    function_expression = find_node(declarator.children, lambda n: n.type == "function_expression")
                    if function_expression:
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


def extract_interface_from_node(node: Node, script_path: str) -> InterfaceDefinition | None:
    """
    Extract InterfaceDefinition from interface_declaration node.

    Handles:
    - interface User { name: string; } → InterfaceDefinition(name='User')

    Parameters:
    -----------

        - node (Node): The interface_declaration AST node
        - script_path (str): The path to the file being parsed

    Returns:
    --------

        - InterfaceDefinition | None: Extracted interface definition or None if extraction fails
    """
    try:
        # Get the interface name
        name_node = node.child_by_field_name("name")
        if name_node:
            interface_name = name_node.text.decode("utf-8")

            interface_definition = InterfaceDefinition(
                name=interface_name,
                start_point=node.start_point,
                end_point=node.end_point,
                source_code=node.text.decode("utf-8"),
                file_path=script_path,
            )
            return interface_definition

    except Exception as e:
        logger.error(f"Error extracting interface from node at {script_path}: {str(e)}")

    return None


def extract_type_alias_from_node(node: Node, script_path: str) -> TypeAliasDefinition | None:
    """
    Extract TypeAliasDefinition from type_alias_declaration node.

    Handles:
    - type ID = string | number → TypeAliasDefinition(name='ID')
    - type UserMap = Map<string, User> → TypeAliasDefinition(name='UserMap')

    Parameters:
    -----------

        - node (Node): The type_alias_declaration AST node
        - script_path (str): The path to the file being parsed

    Returns:
    --------

        - TypeAliasDefinition | None: Extracted type alias definition or None if extraction fails
    """
    try:
        # Get the type alias name
        name_node = node.child_by_field_name("name")
        if name_node:
            type_alias_name = name_node.text.decode("utf-8")

            type_alias_definition = TypeAliasDefinition(
                name=type_alias_name,
                start_point=node.start_point,
                end_point=node.end_point,
                source_code=node.text.decode("utf-8"),
                file_path=script_path,
            )
            return type_alias_definition

    except Exception as e:
        logger.error(f"Error extracting type alias from node at {script_path}: {str(e)}")

    return None


def extract_enum_from_node(node: Node, script_path: str) -> EnumDefinition | None:
    """
    Extract EnumDefinition from enum_declaration node.

    Handles:
    - enum Color { Red, Green, Blue } → EnumDefinition(name='Color')

    Parameters:
    -----------

        - node (Node): The enum_declaration AST node
        - script_path (str): The path to the file being parsed

    Returns:
    --------

        - EnumDefinition | None: Extracted enum definition or None if extraction fails
    """
    try:
        # Get the enum name
        name_node = node.child_by_field_name("name")
        if name_node:
            enum_name = name_node.text.decode("utf-8")

            enum_definition = EnumDefinition(
                name=enum_name,
                start_point=node.start_point,
                end_point=node.end_point,
                source_code=node.text.decode("utf-8"),
                file_path=script_path,
            )
            return enum_definition

    except Exception as e:
        logger.error(f"Error extracting enum from node at {script_path}: {str(e)}")

    return None


def extract_export_from_node(node: Node, script_path: str) -> list[ExportStatement]:
    """
    Extract export statements from export_statement node.

    Handles:
    - export { foo } → ExportStatement(name='foo')
    - export { foo as bar } → ExportStatement(name='bar', local_name='foo')
    - export default X → ExportStatement(name='default', is_default=True)
    - export type { Foo } → ExportStatement(name='Foo', is_type_only=True)

    Parameters:
    -----------

        - node (Node): The export_statement AST node
        - script_path (str): The path to the file being parsed

    Returns:
    --------

        - list[ExportStatement]: List of extracted export statements
    """
    exports = []

    try:
        # Check for 'default' keyword - indicates default export
        has_default = any(
            child.type == "default" or (hasattr(child, 'text') and child.text.decode("utf-8") == "default")
            for child in node.children
        )

        if has_default:
            # Default export: export default X
            export_stmt = ExportStatement(
                name="default",
                is_default=True,
                start_point=node.start_point,
                end_point=node.end_point,
                source_code=node.text.decode("utf-8"),
                file_path=script_path,
            )
            exports.append(export_stmt)
            return exports

        # Check for 'type' keyword before export_clause - indicates type-only export
        is_type_only = False
        for i, child in enumerate(node.children):
            if child.type == "type_identifier" or (hasattr(child, 'text') and child.text.decode("utf-8") == "type"):
                # Check if next node is export_clause
                if i + 1 < len(node.children) and node.children[i + 1].type == "export_clause":
                    is_type_only = True
                    break

        # Handle named exports: export { foo, bar }
        export_clause = find_node(node.children, lambda n: n.type == "export_clause")
        if export_clause:
            for child in export_clause.children:
                if child.type == "export_specifier":
                    # Get all identifier children
                    identifiers = [c for c in child.children if c.type == "identifier"]

                    local_name = None
                    export_name = None

                    if len(identifiers) == 2:
                        # Has alias: export { foo as bar }
                        local_name = identifiers[0].text.decode("utf-8")
                        export_name = identifiers[1].text.decode("utf-8")
                    elif len(identifiers) == 1:
                        # No alias: export { foo }
                        export_name = identifiers[0].text.decode("utf-8")
                    else:
                        continue

                    export_stmt = ExportStatement(
                        name=export_name,
                        local_name=local_name,
                        is_type_only=is_type_only,
                        start_point=node.start_point,
                        end_point=node.end_point,
                        source_code=node.text.decode("utf-8"),
                        file_path=script_path,
                    )
                    exports.append(export_stmt)

    except Exception as e:
        logger.error(f"Error extracting export from node at {script_path}: {str(e)}")

    return exports


def extract_methods_from_class(node: Node, class_name: str, script_path: str) -> list[MethodDefinition]:
    """
    Extract methods from a class_declaration's class_body.

    Handles:
    - constructor() {} → MethodDefinition(name='constructor', is_constructor=True)
    - publicMethod() {} → MethodDefinition(name='publicMethod')
    - private privateMethod() {} → MethodDefinition(name='privateMethod', is_private=True)
    - static staticMethod() {} → MethodDefinition(name='staticMethod', is_static=True)
    - async asyncMethod() {} → MethodDefinition(name='asyncMethod', is_async=True)
    - get getter() {} → MethodDefinition(name='getter', is_getter=True)
    - set setter(v) {} → MethodDefinition(name='setter', is_setter=True)

    Parameters:
    -----------

        - node (Node): The class_declaration or abstract_class_declaration AST node
        - class_name (str): The name of the parent class
        - script_path (str): The path to the file being parsed

    Returns:
    --------

        - list[MethodDefinition]: List of extracted method definitions
    """
    methods = []

    try:
        # Find the class_body
        class_body = find_node(node.children, lambda n: n.type == "class_body")
        if not class_body:
            return methods

        # Iterate through class body members
        for child in class_body.children:
            if child.type == "method_definition":
                # Extract method details
                is_static = False
                is_async = False
                is_private = False
                is_getter = False
                is_setter = False
                is_constructor = False
                method_name = None

                # Check for modifiers and keywords
                for method_child in child.children:
                    if method_child.type == "accessibility_modifier":
                        modifier_text = method_child.text.decode("utf-8")
                        if modifier_text == "private":
                            is_private = True
                    elif hasattr(method_child, 'text'):
                        text = method_child.text.decode("utf-8")
                        if text == "static":
                            is_static = True
                        elif text == "async":
                            is_async = True
                        elif text == "get":
                            is_getter = True
                        elif text == "set":
                            is_setter = True

                    # Get method name
                    if method_child.type == "property_identifier":
                        method_name = method_child.text.decode("utf-8")
                        if method_name == "constructor":
                            is_constructor = True
                    elif method_child.type == "private_property_identifier":
                        # TypeScript # private fields
                        method_name = method_child.text.decode("utf-8")
                        is_private = True

                if method_name:
                    method_def = MethodDefinition(
                        name=method_name,
                        class_name=class_name,
                        is_static=is_static,
                        is_async=is_async,
                        is_private=is_private,
                        is_getter=is_getter,
                        is_setter=is_setter,
                        is_constructor=is_constructor,
                        start_point=child.start_point,
                        end_point=child.end_point,
                        source_code=child.text.decode("utf-8"),
                        file_path=script_path,
                    )
                    methods.append(method_def)

    except Exception as e:
        logger.error(f"Error extracting methods from class {class_name} at {script_path}: {str(e)}")

    return methods

"""
Validation script for TypeScript extraction support.
Tests the full pipeline with a mixed Python/TypeScript monorepo.
"""
import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from repo_processor import get_repo_file_dependencies


async def validate():
    """Run validation against test monorepo."""
    repo_path = str(Path(__file__).parent / "test_monorepo")

    print("=" * 60)
    print("TypeScript Support Validation")
    print("=" * 60)
    print(f"\nRepo path: {repo_path}")

    # Counters
    stats = {
        "total_files": 0,
        "python_files": 0,
        "typescript_files": 0,
        "imports": 0,
        "functions": 0,
        "classes": 0,
        "interfaces": 0,
        "type_aliases": 0,
        "enums": 0,
        "methods": 0,
        "exports": 0,
    }

    print("\n--- Processing Files ---\n")

    async for node in get_repo_file_dependencies(
        repo_path,
        detailed_extraction=True
    ):
        node_type = type(node).__name__

        if node_type == "Repository":
            print(f"Repository: {getattr(node, 'path', '')}")
            continue

        # It's a CodeFile
        stats["total_files"] += 1
        lang: str = getattr(node, "language", "unknown") or "unknown"
        name: str = getattr(node, "name", "") or ""

        if lang == "python":
            stats["python_files"] += 1
        elif lang == "typescript":
            stats["typescript_files"] += 1

        print(f"\n[{lang.upper()}] {name}")

        # Count extractions - use getattr with empty list default
        depends_on: list = getattr(node, "depends_on", None) or []
        if depends_on:
            count = len(depends_on)
            stats["imports"] += count
            print(f"  Imports: {count}")
            for imp in depends_on[:3]:  # Show first 3
                print(f"    - {imp.name} from {imp.module}")
            if count > 3:
                print(f"    ... and {count - 3} more")

        functions: list = getattr(node, "provides_function_definition", None) or []
        if functions:
            count = len(functions)
            stats["functions"] += count
            print(f"  Functions: {count}")
            for func in functions[:3]:
                print(f"    - {func.name}")

        classes: list = getattr(node, "provides_class_definition", None) or []
        if classes:
            count = len(classes)
            stats["classes"] += count
            print(f"  Classes: {count}")
            for cls in classes[:3]:
                print(f"    - {cls.name}")

        # TypeScript-specific
        interfaces: list = getattr(node, "provides_interface_definition", None) or []
        if interfaces:
            count = len(interfaces)
            stats["interfaces"] += count
            print(f"  Interfaces: {count}")
            for iface in interfaces[:3]:
                print(f"    - {iface.name}")

        type_aliases: list = getattr(node, "provides_type_alias", None) or []
        if type_aliases:
            count = len(type_aliases)
            stats["type_aliases"] += count
            print(f"  Type Aliases: {count}")
            for ta in type_aliases[:3]:
                print(f"    - {ta.name}")

        enums: list = getattr(node, "provides_enum_definition", None) or []
        if enums:
            count = len(enums)
            stats["enums"] += count
            print(f"  Enums: {count}")
            for enum in enums[:3]:
                print(f"    - {enum.name}")

        methods: list = getattr(node, "provides_method_definition", None) or []
        if methods:
            count = len(methods)
            stats["methods"] += count
            print(f"  Methods: {count}")

        exports: list = getattr(node, "exports", None) or []
        if exports:
            count = len(exports)
            stats["exports"] += count
            print(f"  Exports: {count}")

    # Summary
    print("\n" + "=" * 60)
    print("VALIDATION SUMMARY")
    print("=" * 60)
    print("\nFiles processed:")
    print(f"  Total:      {stats['total_files']}")
    print(f"  Python:     {stats['python_files']}")
    print(f"  TypeScript: {stats['typescript_files']}")

    print("\nExtractions:")
    print(f"  Imports:     {stats['imports']}")
    print(f"  Functions:   {stats['functions']}")
    print(f"  Classes:     {stats['classes']}")
    print(f"  Interfaces:  {stats['interfaces']}")
    print(f"  Type Aliases:{stats['type_aliases']}")
    print(f"  Enums:       {stats['enums']}")
    print(f"  Methods:     {stats['methods']}")
    print(f"  Exports:     {stats['exports']}")

    # Validation checks
    print("\n" + "=" * 60)
    print("VALIDATION CHECKS")
    print("=" * 60)

    checks = [
        ("Python files found", stats["python_files"] > 0),
        ("TypeScript files found", stats["typescript_files"] > 0),
        ("Imports extracted", stats["imports"] > 0),
        ("Functions extracted", stats["functions"] > 0),
        ("Classes extracted", stats["classes"] > 0),
        ("Interfaces extracted (TS)", stats["interfaces"] > 0),
        ("Type aliases extracted (TS)", stats["type_aliases"] > 0),
        ("Enums extracted (TS)", stats["enums"] > 0),
    ]

    all_pass = True
    for name, passed in checks:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {status}: {name}")
        if not passed:
            all_pass = False

    print("\n" + "=" * 60)
    if all_pass:
        print("ALL VALIDATION CHECKS PASSED ✓")
    else:
        print("SOME CHECKS FAILED ✗")
    print("=" * 60)

    return all_pass


if __name__ == "__main__":
    success = asyncio.run(validate())
    sys.exit(0 if success else 1)

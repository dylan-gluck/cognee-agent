"""
Test script for Phase 4 advanced features.
Tests export tracking, method extraction, and function expressions.
"""
import asyncio
import os
import sys
import tempfile
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from typescript_extractor import get_typescript_dependencies


async def test_export_tracking():
    """Test export statement extraction."""

    test_code = """
export { foo };
export { bar as baz };
export default class MyClass {}
export type { User };
export default function myFunc() {}
const exported = 42;
export { exported };
"""

    with tempfile.TemporaryDirectory() as temp_dir:
        test_file = os.path.join(temp_dir, "exports.ts")

        with open(test_file, 'w') as f:
            f.write(test_code)

        print("\n1. Testing Export Tracking")
        print("=" * 60)

        code_file = await get_typescript_dependencies(
            repo_path=temp_dir,
            script_path=test_file,
            detailed_extraction=True
        )

        exports = code_file.exports or []
        print(f"Exports extracted: {len(exports)}")
        for exp in exports:
            flags = []
            if exp.is_default:
                flags.append("default")
            if exp.is_type_only:
                flags.append("type-only")
            if exp.local_name:
                flags.append(f"aliased from {exp.local_name}")
            flag_str = f" ({', '.join(flags)})" if flags else ""
            print(f"  - {exp.name}{flag_str}")

        # Verify criteria
        has_named = any(e.name == "foo" and not e.is_default for e in exports)
        has_aliased = any(e.name == "baz" and e.local_name == "bar" for e in exports)
        has_default = any(e.name == "default" and e.is_default for e in exports)
        has_type = any(e.is_type_only for e in exports)

        print(f"\n  ✅ Named exports: {has_named}")
        print(f"  ✅ Aliased exports: {has_aliased}")
        print(f"  ✅ Default exports: {has_default}")
        print(f"  ✅ Type-only exports: {has_type}")

        return has_named and has_aliased and has_default and has_type


async def test_method_extraction():
    """Test class method extraction."""

    test_code = """
class Calculator {
    constructor() {
        this.value = 0;
    }

    add(x: number): number {
        return this.value + x;
    }

    static create(): Calculator {
        return new Calculator();
    }

    async fetchValue(): Promise<number> {
        return await fetch('/value');
    }

    private privateMethod(): void {
        console.log('private');
    }

    get currentValue(): number {
        return this.value;
    }

    set currentValue(val: number) {
        this.value = val;
    }
}
"""

    with tempfile.TemporaryDirectory() as temp_dir:
        test_file = os.path.join(temp_dir, "methods.ts")

        with open(test_file, 'w') as f:
            f.write(test_code)

        print("\n2. Testing Method Extraction")
        print("=" * 60)

        code_file = await get_typescript_dependencies(
            repo_path=temp_dir,
            script_path=test_file,
            detailed_extraction=True
        )

        classes = code_file.provides_class_definition or []
        methods = code_file.provides_method_definition or []
        print(f"Classes extracted: {len(classes)}")
        print(f"Methods extracted: {len(methods)}")

        for method in methods:
            flags = []
            if method.is_constructor:
                flags.append("constructor")
            if method.is_static:
                flags.append("static")
            if method.is_async:
                flags.append("async")
            if method.is_private:
                flags.append("private")
            if method.is_getter:
                flags.append("getter")
            if method.is_setter:
                flags.append("setter")
            flag_str = f" [{', '.join(flags)}]" if flags else ""
            print(f"  - {method.class_name}.{method.name}{flag_str}")

        # Verify criteria
        has_constructor = any(m.is_constructor for m in methods)
        has_static = any(m.is_static for m in methods)
        has_async = any(m.is_async for m in methods)
        has_private = any(m.is_private for m in methods)
        has_getter = any(m.is_getter for m in methods)
        has_setter = any(m.is_setter for m in methods)

        print(f"\n  ✅ Constructor: {has_constructor}")
        print(f"  ✅ Static methods: {has_static}")
        print(f"  ✅ Async methods: {has_async}")
        print(f"  ✅ Private methods: {has_private}")
        print(f"  ✅ Getters: {has_getter}")
        print(f"  ✅ Setters: {has_setter}")

        return all([has_constructor, has_static, has_async, has_private, has_getter, has_setter])


async def test_function_expressions():
    """Test function expression extraction."""

    test_code = """
const foo = function() {
    return 42;
};

const bar = function named() {
    return 'hello';
};

const baz = async function() {
    return await fetch('/data');
};

const arrow = () => {
    return 'arrow';
};
"""

    with tempfile.TemporaryDirectory() as temp_dir:
        test_file = os.path.join(temp_dir, "functions.ts")

        with open(test_file, 'w') as f:
            f.write(test_code)

        print("\n3. Testing Function Expression Support")
        print("=" * 60)

        code_file = await get_typescript_dependencies(
            repo_path=temp_dir,
            script_path=test_file,
            detailed_extraction=True
        )

        functions = code_file.provides_function_definition or []
        print(f"Functions extracted: {len(functions)}")
        for func in functions:
            print(f"  - {func.name}")

        # Verify all function types are extracted
        has_function_expr = any(f.name == "foo" for f in functions)
        has_named_expr = any(f.name == "bar" for f in functions)
        has_async_expr = any(f.name == "baz" for f in functions)
        has_arrow = any(f.name == "arrow" for f in functions)

        print(f"\n  ✅ Function expressions: {has_function_expr}")
        print(f"  ✅ Named function expressions: {has_named_expr}")
        print(f"  ✅ Async function expressions: {has_async_expr}")
        print(f"  ✅ Arrow functions: {has_arrow}")

        return all([has_function_expr, has_named_expr, has_async_expr, has_arrow])


async def test_default_export_handling():
    """Test default export with declarations."""

    test_code = """
export default function myFunc() {
    return 42;
}

export default class MyClass {
    method() {
        return 'hello';
    }
}
"""

    with tempfile.TemporaryDirectory() as temp_dir:
        test_file = os.path.join(temp_dir, "default_exports.ts")

        with open(test_file, 'w') as f:
            f.write(test_code)

        print("\n4. Testing Default Export Handling")
        print("=" * 60)

        code_file = await get_typescript_dependencies(
            repo_path=temp_dir,
            script_path=test_file,
            detailed_extraction=True
        )

        functions = code_file.provides_function_definition or []
        classes = code_file.provides_class_definition or []
        exports = code_file.exports or []
        print(f"Functions extracted: {len(functions)}")
        print(f"Classes extracted: {len(classes)}")
        print(f"Exports extracted: {len(exports)}")

        # Verify both declaration and export are extracted
        has_func = any(f.name == "myFunc" for f in functions)
        has_class = any(c.name == "MyClass" for c in classes)
        has_default_exports = any(e.name == "default" and e.is_default for e in exports)

        print(f"\n  ✅ Function declaration: {has_func}")
        print(f"  ✅ Class declaration: {has_class}")
        print(f"  ✅ Default export statements: {has_default_exports}")

        return all([has_func, has_class, has_default_exports])


async def main():
    """Run all Phase 4 tests."""
    try:
        print("\nPhase 4: Advanced Features Tests")
        print("=" * 60)

        export_test = await test_export_tracking()
        method_test = await test_method_extraction()
        function_test = await test_function_expressions()
        default_test = await test_default_export_handling()

        print("\n" + "=" * 60)
        print("Phase 4 Test Results:")
        print("=" * 60)
        print(f"  {'✅' if export_test else '❌'} Export tracking")
        print(f"  {'✅' if method_test else '❌'} Method extraction")
        print(f"  {'✅' if function_test else '❌'} Function expressions")
        print(f"  {'✅' if default_test else '❌'} Default export handling")

        all_passed = all([export_test, method_test, function_test, default_test])

        print("\n" + "=" * 60)
        if all_passed:
            print("✅ All Phase 4 tests passed!")
            print("🎉 Phase 4: Advanced Features implementation complete!")
        else:
            print("❌ Some Phase 4 tests failed")
        print("=" * 60)

        return all_passed

    except Exception as e:
        print(f"\n❌ Error during testing: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    asyncio.run(main())

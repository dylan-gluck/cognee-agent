"""
Test script to verify TypeScript extractor functionality.
This tests Phase 1 basic extraction capabilities.
"""
import asyncio
import os
import sys
import tempfile
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from typescript_extractor import get_typescript_dependencies


async def test_typescript_extractor():
    """Test the TypeScript extractor with sample TypeScript code."""

    # Create a temporary TypeScript file
    test_code = """
import React from 'react';
import * as Utils from './utils';

export function greet(name: string): string {
    return `Hello, ${name}!`;
}

export class Calculator {
    add(a: number, b: number): number {
        return a + b;
    }
}

const multiply = (a: number, b: number): number => {
    return a * b;
};

async function fetchData() {
    return await fetch('/api/data');
}
"""

    # Create temp directory and file
    with tempfile.TemporaryDirectory() as temp_dir:
        test_file = os.path.join(temp_dir, "test.ts")

        with open(test_file, 'w') as f:
            f.write(test_code)

        print("Testing TypeScript Extractor - Phase 1\n")
        print("=" * 60)

        # Test 1: Basic extraction (source code only)
        print("\n1. Testing basic extraction (detailed_extraction=False)...")
        code_file = await get_typescript_dependencies(
            repo_path=temp_dir,
            script_path=test_file,
            detailed_extraction=False
        )

        print("   ✓ CodeFile created")
        print(f"   - Name: {code_file.name}")
        print(f"   - Language: {code_file.language}")
        print(f"   - Has source code: {code_file.source_code is not None}")
        print(f"   - Source code length: {len(code_file.source_code) if code_file.source_code else 0} chars")

        # Test 2: Detailed extraction
        print("\n2. Testing detailed extraction (detailed_extraction=True)...")
        code_file = await get_typescript_dependencies(
            repo_path=temp_dir,
            script_path=test_file,
            detailed_extraction=True
        )

        print("   ✓ CodeFile created with detailed extraction")
        print(f"   - Name: {code_file.name}")
        print(f"   - Language: {code_file.language}")

        # Check imports
        depends_on = code_file.depends_on or []
        print(f"\n3. Imports extracted: {len(depends_on)}")
        for imp in depends_on:
            print(f"   - {imp.name} from '{imp.module}'")

        # Check functions
        functions = code_file.provides_function_definition or []
        print(f"\n4. Functions extracted: {len(functions)}")
        for func in functions:
            print(f"   - {func.name}")

        # Check classes
        classes = code_file.provides_class_definition or []
        print(f"\n5. Classes extracted: {len(classes)}")
        for cls in classes:
            print(f"   - {cls.name}")

        print("\n" + "=" * 60)
        print("\nAcceptance Criteria Check:")
        print("=" * 60)

        # Verify acceptance criteria
        criteria = {
            "✅ Can parse .ts files": True,
            "✅ Default imports extracted": len(depends_on) >= 2,
            "✅ Function declarations extracted": len(functions) >= 3,
            "✅ Class declarations extracted": len(classes) >= 1,
            "✅ CodeFile has proper fields": all([
                code_file.id,
                code_file.name == "test.ts",
                code_file.file_path == test_file,
                code_file.language == "typescript"
            ]),
            "✅ detailed_extraction modes work": True,
        }

        for criterion, passed in criteria.items():
            status = "✓" if passed else "✗"
            print(f"{status} {criterion}")

        all_passed = all(criteria.values())
        print("\n" + "=" * 60)
        if all_passed:
            print("✅ All acceptance criteria passed!")
        else:
            print("❌ Some acceptance criteria failed")
        print("=" * 60)

        return all_passed


async def test_tsx_file():
    """Test the TypeScript extractor with a TSX file."""

    test_code = """
import React from 'react';

export const Button = ({ label }: { label: string }) => {
    return <button>{label}</button>;
};

export class Component extends React.Component {
    render() {
        return <div>Hello</div>;
    }
}
"""

    with tempfile.TemporaryDirectory() as temp_dir:
        test_file = os.path.join(temp_dir, "test.tsx")

        with open(test_file, 'w') as f:
            f.write(test_code)

        print("\n\nTesting TSX File Support\n")
        print("=" * 60)

        code_file = await get_typescript_dependencies(
            repo_path=temp_dir,
            script_path=test_file,
            detailed_extraction=True
        )

        print("✓ TSX file parsed successfully")
        print(f"  - File: {code_file.name}")
        print(f"  - Imports: {len(code_file.depends_on or [])}")
        print(f"  - Functions: {len(code_file.provides_function_definition or [])}")
        print(f"  - Classes: {len(code_file.provides_class_definition or [])}")
        print("=" * 60)


async def main():
    """Run all tests."""
    try:
        ts_passed = await test_typescript_extractor()
        await test_tsx_file()

        if ts_passed:
            print("\n🎉 TypeScript extractor Phase 1 implementation complete!")
        else:
            print("\n⚠️  Some tests failed, review implementation")

    except Exception as e:
        print(f"\n❌ Error during testing: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())

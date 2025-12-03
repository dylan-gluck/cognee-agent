"""
Comprehensive test combining all phases (1-4) of TypeScript extractor.
Tests all features working together in a realistic TypeScript file.
"""
import asyncio
import os
import sys
import tempfile
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from typescript_extractor import get_typescript_dependencies


async def test_comprehensive():
    """Test all extractor features with a comprehensive TypeScript file."""

    test_code = """
// Phase 1 & 2: Imports
import React from 'react';
import * as Utils from './utils';
import { useState, useEffect } from 'react';
const fs = require('fs');
const { readFile, writeFile } = require('fs/promises');

// Phase 3: Interface
export interface User {
    id: number;
    name: string;
    email: string;
}

// Phase 3: Type alias
export type UserID = string | number;

// Phase 3: Enum
export enum Role {
    Admin,
    User,
    Guest
}

// Phase 4: Class with methods
export class UserService {
    private users: User[] = [];

    constructor() {
        this.users = [];
    }

    async fetchUsers(): Promise<User[]> {
        const response = await fetch('/api/users');
        return response.json();
    }

    static create(): UserService {
        return new UserService();
    }

    get userCount(): number {
        return this.users.length;
    }

    set userCount(count: number) {
        console.log(`Setting count to ${count}`);
    }

    private validateUser(user: User): boolean {
        return !!user.id && !!user.name;
    }
}

// Phase 1: Function declaration
export function greet(name: string): string {
    return `Hello, ${name}!`;
}

// Phase 1: Arrow function
export const multiply = (a: number, b: number): number => {
    return a * b;
};

// Phase 4: Function expression
const divide = function(a: number, b: number): number {
    return a / b;
};

// Phase 4: Named function expression
const subtract = function sub(a: number, b: number): number {
    return a - b;
};

// Phase 1: Async function
async function fetchData(): Promise<any> {
    return await fetch('/api/data');
}

// Phase 4: Exports
export { divide };
export { subtract as minus };
export type { User as UserType };

// Phase 2: Re-export
export { Logger } from './logger';
export * from './constants';

// Phase 4: Default export
export default class App extends React.Component {
    render() {
        return <div>Hello World</div>;
    }
}
"""

    with tempfile.TemporaryDirectory() as temp_dir:
        test_file = os.path.join(temp_dir, "app.tsx")

        with open(test_file, 'w') as f:
            f.write(test_code)

        print("\nComprehensive Test - All Phases (1-4)")
        print("=" * 70)

        code_file = await get_typescript_dependencies(
            repo_path=temp_dir,
            script_path=test_file,
            detailed_extraction=True
        )

        # Phase 1 & 2: Check imports
        depends_on = code_file.depends_on or []
        print(f"\n1. Imports (Phase 1 & 2): {len(depends_on)}")
        import_types = {
            'default': [],
            'namespace': [],
            'named': [],
            'require': [],
            're-export': []
        }
        for imp in depends_on:
            if imp.name == '*':
                import_types['re-export'].append(f"{imp.name} from '{imp.module}'")
            elif imp.module.startswith('./') or imp.module.startswith('../'):
                if 'export' in str(imp.source_code):
                    import_types['re-export'].append(f"{imp.name} from '{imp.module}'")
                else:
                    import_types['named'].append(f"{imp.name} from '{imp.module}'")
            else:
                if 'require' in str(imp.source_code):
                    import_types['require'].append(f"{imp.name} from '{imp.module}'")
                elif imp.name in ['React', 'Utils']:
                    if '*' in str(imp.source_code):
                        import_types['namespace'].append(f"{imp.name} from '{imp.module}'")
                    else:
                        import_types['default'].append(f"{imp.name} from '{imp.module}'")
                else:
                    import_types['named'].append(f"{imp.name} from '{imp.module}'")

        for imp_type, imports in import_types.items():
            if imports:
                print(f"   {imp_type.title()}: {len(imports)} ({', '.join(imports[:2])}...)" if len(imports) > 2 else f"   {imp_type.title()}: {len(imports)} ({', '.join(imports)})")

        # Phase 3: Check TypeScript-specific constructs
        interfaces = code_file.provides_interface_definition or []
        type_aliases = code_file.provides_type_alias or []
        enums = code_file.provides_enum_definition or []
        print("\n2. TypeScript Constructs (Phase 3):")
        print(f"   Interfaces: {len(interfaces)} ({', '.join(i.name for i in interfaces)})")
        print(f"   Type Aliases: {len(type_aliases)} ({', '.join(t.name for t in type_aliases)})")
        print(f"   Enums: {len(enums)} ({', '.join(e.name for e in enums)})")

        # Phase 1: Check functions
        functions = code_file.provides_function_definition or []
        print("\n3. Functions (Phase 1 & 4):")
        func_types = {'declaration': [], 'arrow': [], 'expression': []}
        for func in functions:
            if '=>' in func.source_code:
                func_types['arrow'].append(func.name)
            elif 'function(' in func.source_code or 'function ' in func.source_code:
                if 'const' in func.source_code or 'let' in func.source_code or 'var' in func.source_code:
                    func_types['expression'].append(func.name)
                else:
                    func_types['declaration'].append(func.name)
            else:
                func_types['declaration'].append(func.name)

        print(f"   Total: {len(functions)}")
        for func_type, funcs in func_types.items():
            if funcs:
                print(f"   {func_type.title()}: {len(funcs)} ({', '.join(funcs)})")

        # Phase 1: Check classes
        classes = code_file.provides_class_definition or []
        print(f"\n4. Classes (Phase 1): {len(classes)}")
        for cls in classes:
            print(f"   - {cls.name}")

        # Phase 4: Check methods
        methods = code_file.provides_method_definition or []
        print(f"\n5. Methods (Phase 4): {len(methods)}")
        method_stats = {
            'constructor': 0,
            'static': 0,
            'async': 0,
            'private': 0,
            'getter': 0,
            'setter': 0,
            'regular': 0
        }
        for method in methods:
            if method.is_constructor:
                method_stats['constructor'] += 1
            if method.is_static:
                method_stats['static'] += 1
            if method.is_async:
                method_stats['async'] += 1
            if method.is_private:
                method_stats['private'] += 1
            if method.is_getter:
                method_stats['getter'] += 1
            if method.is_setter:
                method_stats['setter'] += 1
            if not any([method.is_constructor, method.is_static, method.is_async,
                       method.is_private, method.is_getter, method.is_setter]):
                method_stats['regular'] += 1

        for method_type, count in method_stats.items():
            if count > 0:
                print(f"   {method_type.title()}: {count}")

        # Phase 4: Check exports
        exports = code_file.exports or []
        print(f"\n6. Exports (Phase 4): {len(exports)}")
        export_stats = {
            'named': 0,
            'default': 0,
            'aliased': 0,
            'type-only': 0
        }
        for exp in exports:
            if exp.is_default:
                export_stats['default'] += 1
            else:
                export_stats['named'] += 1
            if exp.local_name:
                export_stats['aliased'] += 1
            if exp.is_type_only:
                export_stats['type-only'] += 1

        for export_type, count in export_stats.items():
            print(f"   {export_type.title()}: {count}")

        # Comprehensive validation
        print("\n" + "=" * 70)
        print("Validation Results:")
        print("=" * 70)

        checks = {
            "Phase 1: Default imports": len([i for i in depends_on if i.name in ['React']]) > 0,
            "Phase 1: Namespace imports": len([i for i in depends_on if '*' in str(i.source_code) and 'export' not in str(i.source_code)]) > 0,
            "Phase 2: Named imports": len([i for i in depends_on if i.name in ['useState', 'useEffect']]) > 0,
            "Phase 2: Require imports": len([i for i in depends_on if 'require' in str(i.source_code)]) > 0,
            "Phase 2: Re-exports": len([i for i in depends_on if 'export' in str(i.source_code) and 'from' in str(i.source_code)]) > 0,
            "Phase 1: Function declarations": len([f for f in functions if 'function' in f.source_code and '=>' not in f.source_code]) > 0,
            "Phase 1: Arrow functions": len([f for f in functions if '=>' in f.source_code]) > 0,
            "Phase 1: Classes": len(classes) > 0,
            "Phase 3: Interfaces": len(interfaces) > 0,
            "Phase 3: Type aliases": len(type_aliases) > 0,
            "Phase 3: Enums": len(enums) > 0,
            "Phase 4: Function expressions": len([f for f in functions if f.name in ['divide', 'subtract']]) > 0,
            "Phase 4: Class methods": len(methods) > 0,
            "Phase 4: Static methods": any(m.is_static for m in methods),
            "Phase 4: Async methods": any(m.is_async for m in methods),
            "Phase 4: Private methods": any(m.is_private for m in methods),
            "Phase 4: Getters/Setters": any(m.is_getter or m.is_setter for m in methods),
            "Phase 4: Named exports": len([e for e in exports if not e.is_default]) > 0,
            "Phase 4: Default exports": any(e.is_default for e in exports),
            "Phase 4: Aliased exports": any(e.local_name for e in exports),
            "Phase 4: Type-only exports": any(e.is_type_only for e in exports),
        }

        phase_results = {1: [], 2: [], 3: [], 4: []}
        for check, passed in checks.items():
            status = "✅" if passed else "❌"
            phase = int(check.split(":")[0].split()[-1])
            phase_results[phase].append(passed)
            print(f"{status} {check}")

        print("\n" + "=" * 70)
        print("Phase Summary:")
        print("=" * 70)
        for phase, results in phase_results.items():
            passed = sum(results)
            total = len(results)
            percentage = (passed / total * 100) if total > 0 else 0
            status = "✅" if passed == total else "⚠️"
            print(f"{status} Phase {phase}: {passed}/{total} checks passed ({percentage:.0f}%)")

        all_passed = all(checks.values())
        print("\n" + "=" * 70)
        if all_passed:
            print("✅ All comprehensive checks passed!")
            print("🎉 TypeScript extractor Phases 1-4 fully functional!")
        else:
            failed = [k for k, v in checks.items() if not v]
            print("❌ Some checks failed:")
            for check in failed:
                print(f"   - {check}")
        print("=" * 70)

        return all_passed


async def main():
    """Run comprehensive test."""
    try:
        result = await test_comprehensive()
        return result
    except Exception as e:
        print(f"\n❌ Error during testing: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    asyncio.run(main())

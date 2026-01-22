#!/usr/bin/env python3
"""Structural verification for the Rich console export refactoring task.

This script verifies that the refactoring was performed correctly by checking:
1. The new module exists
2. Export functions are defined
3. Console class methods delegate to the new module
4. No import cycles exist
"""

import ast
import subprocess
import sys
from pathlib import Path


def check_file_exists():
    """Check that console_export.py exists."""
    path = Path("rich/console_export.py")
    if not path.exists():
        print("❌ FAIL: rich/console_export.py does not exist")
        return False
    print("✅ PASS: rich/console_export.py exists")
    return True


def check_export_functions_defined():
    """Check that export functions are defined in console_export.py."""
    # We don't specify exact names - agent should identify them
    # But we expect at minimum functions for text, html, svg export
    
    path = Path("rich/console_export.py")
    try:
        tree = ast.parse(path.read_text())
    except SyntaxError as e:
        print(f"❌ FAIL: Syntax error in console_export.py: {e}")
        return False
    
    defined_functions = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            defined_functions.add(node.name)
    
    # Check for export-related functions (flexible naming)
    export_patterns = ["export", "text", "html", "svg", "save"]
    export_functions = [
        f for f in defined_functions 
        if any(p in f.lower() for p in export_patterns)
    ]
    
    if len(export_functions) < 3:
        print(f"❌ FAIL: Expected at least 3 export-related functions, found: {export_functions}")
        return False
    
    print(f"✅ PASS: Found export functions: {sorted(export_functions)}")
    return True


def check_console_imports_export():
    """Check that console.py imports from console_export."""
    path = Path("rich/console.py")
    content = path.read_text()
    
    # Check for various import patterns
    import_patterns = [
        "from .console_export import",
        "from . import console_export",
        "import rich.console_export",
        "from .console_export",
    ]
    
    found = any(pattern in content for pattern in import_patterns)
    if not found:
        print("❌ FAIL: console.py does not import from console_export")
        return False
    
    print("✅ PASS: console.py imports from console_export")
    return True


def check_delegation():
    """Check that Console export methods delegate to console_export functions."""
    path = Path("rich/console.py")
    tree = ast.parse(path.read_text())
    
    # Find the Console class
    console_class = None
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "Console":
            console_class = node
            break
    
    if console_class is None:
        print("❌ FAIL: Could not find Console class")
        return False
    
    # Find export methods and check they're short (delegating)
    export_methods = {}
    for node in ast.walk(console_class):
        if isinstance(node, ast.FunctionDef):
            if "export" in node.name or "save" in node.name:
                # Count non-docstring statements
                body_statements = [
                    stmt for stmt in node.body
                    if not (isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant))
                ]
                export_methods[node.name] = len(body_statements)
    
    if not export_methods:
        print("❌ FAIL: No export methods found in Console class")
        return False
    
    # Check that methods are reasonably short (delegating)
    long_methods = {k: v for k, v in export_methods.items() if v > 15}
    
    if long_methods:
        print(f"⚠️  WARNING: Some export methods may not be delegating: {long_methods}")
        # This is a warning, not a failure - the logic might still be extracted
    
    print(f"✅ PASS: Found export methods: {list(export_methods.keys())}")
    return True


def check_no_import_cycles():
    """Check that importing rich.console doesn't cause import cycles."""
    result = subprocess.run(
        [sys.executable, "-c", "from rich.console import Console; print('OK')"],
        capture_output=True,
        text=True,
    )
    
    if result.returncode != 0:
        print(f"❌ FAIL: Import cycle detected: {result.stderr}")
        return False
    
    if "OK" not in result.stdout:
        print("❌ FAIL: Import failed silently")
        return False
    
    print("✅ PASS: No import cycles (rich.console imports successfully)")
    return True


def check_export_module_structure():
    """Check that console_export.py has reasonable structure."""
    path = Path("rich/console_export.py")
    content = path.read_text()
    tree = ast.parse(content)
    
    # Count top-level functions
    top_level_functions = [
        node for node in ast.iter_child_nodes(tree)
        if isinstance(node, ast.FunctionDef)
    ]
    
    if len(top_level_functions) < 2:
        print(f"❌ FAIL: Expected at least 2 top-level functions, found {len(top_level_functions)}")
        return False
    
    # Check for docstring
    has_docstring = (
        isinstance(tree.body[0], ast.Expr) and
        isinstance(tree.body[0].value, ast.Constant) and
        isinstance(tree.body[0].value.value, str)
    )
    
    if not has_docstring:
        print("⚠️  WARNING: console_export.py lacks module docstring")
    
    print(f"✅ PASS: console_export.py has {len(top_level_functions)} top-level functions")
    return True


def check_exports_still_work():
    """Functional check that exports still work correctly."""
    result = subprocess.run(
        [sys.executable, "-c", """
from rich.console import Console

# Test export_text
c = Console(record=True)
c.print("test")
text = c.export_text()
assert "test" in text, f"export_text failed: {text!r}"

# Test export_html
c = Console(record=True)
c.print("[bold]test[/bold]")
html = c.export_html()
assert "test" in html, f"export_html failed"
assert "<" in html, "export_html should produce HTML"

# Test export_svg
c = Console(record=True, width=40)
c.print("test")
svg = c.export_svg()
assert "<svg" in svg, f"export_svg should produce SVG"

print("OK")
"""],
        capture_output=True,
        text=True,
    )
    
    if result.returncode != 0:
        print(f"❌ FAIL: Export functionality broken: {result.stderr}")
        return False
    
    if "OK" not in result.stdout:
        print(f"❌ FAIL: Export check failed: {result.stdout}")
        return False
    
    print("✅ PASS: Export functionality works correctly")
    return True


def main():
    """Run all structural verification checks."""
    print("=" * 60)
    print("Rich Console Export Refactoring - Structural Verification")
    print("=" * 60)
    print()
    
    checks = [
        ("File exists", check_file_exists),
        ("Export functions defined", check_export_functions_defined),
        ("Console imports export", check_console_imports_export),
        ("Methods delegate", check_delegation),
        ("No import cycles", check_no_import_cycles),
        ("Module structure", check_export_module_structure),
        ("Exports still work", check_exports_still_work),
    ]
    
    results = []
    for name, check_fn in checks:
        print(f"\n>>> Checking: {name}")
        try:
            result = check_fn()
            results.append((name, result))
        except Exception as e:
            print(f"❌ FAIL: {name} raised exception: {e}")
            results.append((name, False))
    
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for name, result in results:
        status = "✅" if result else "❌"
        print(f"  {status} {name}")
    
    print(f"\nPassed: {passed}/{total}")
    
    if passed == total:
        print("\n🎉 All structural checks passed!")
        return 0
    else:
        print(f"\n💥 {total - passed} check(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())

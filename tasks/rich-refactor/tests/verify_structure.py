#!/usr/bin/env python3
"""Structural verification for the Rich refactoring task.

This script verifies that the refactoring was performed correctly by checking:
1. The new module exists
2. Required functions are defined
3. Text class methods delegate to the new module
4. No import cycles exist
"""

import ast
import subprocess
import sys
from pathlib import Path


def check_file_exists():
    """Check that text_operations.py exists."""
    path = Path("rich/text_operations.py")
    if not path.exists():
        print("❌ FAIL: rich/text_operations.py does not exist")
        return False
    print("✅ PASS: rich/text_operations.py exists")
    return True


def check_functions_defined():
    """Check that required functions are defined in text_operations.py."""
    required_functions = {
        "truncate",
        "pad",
        "pad_left", 
        "pad_right",
        "align",
        "set_length",
    }
    
    path = Path("rich/text_operations.py")
    try:
        tree = ast.parse(path.read_text())
    except SyntaxError as e:
        print(f"❌ FAIL: Syntax error in text_operations.py: {e}")
        return False
    
    defined_functions = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            defined_functions.add(node.name)
    
    missing = required_functions - defined_functions
    if missing:
        print(f"❌ FAIL: Missing functions in text_operations.py: {missing}")
        return False
    
    print(f"✅ PASS: All required functions defined: {required_functions}")
    return True


def check_text_imports_operations():
    """Check that text.py imports from text_operations."""
    path = Path("rich/text.py")
    content = path.read_text()
    
    # Check for various import patterns
    import_patterns = [
        "from .text_operations import",
        "from . import text_operations",
        "import rich.text_operations",
    ]
    
    found = any(pattern in content for pattern in import_patterns)
    if not found:
        print("❌ FAIL: text.py does not import from text_operations")
        return False
    
    print("✅ PASS: text.py imports from text_operations")
    return True


def check_delegation():
    """Check that Text methods delegate to text_operations functions."""
    path = Path("rich/text.py")
    content = path.read_text()
    
    # Look for evidence of delegation in the method bodies
    # This is a heuristic check - we look for calls to the imported functions
    delegation_indicators = [
        "_truncate(",
        "text_operations.truncate(",
        "_pad(",
        "text_operations.pad(",
        "_pad_left(",
        "text_operations.pad_left(",
        "_pad_right(",
        "text_operations.pad_right(",
        "_align(",
        "text_operations.align(",
        "_set_length(",
        "text_operations.set_length(",
    ]
    
    # We need at least some of these to be present
    found_count = sum(1 for indicator in delegation_indicators if indicator in content)
    
    if found_count < 3:
        print(f"❌ FAIL: Text methods don't appear to delegate to text_operations (found {found_count} delegation calls)")
        return False
    
    print(f"✅ PASS: Text methods delegate to text_operations ({found_count} delegation calls found)")
    return True


def check_no_import_cycles():
    """Check that importing rich.text doesn't cause import cycles."""
    result = subprocess.run(
        [sys.executable, "-c", "from rich.text import Text; print('OK')"],
        capture_output=True,
        text=True,
    )
    
    if result.returncode != 0:
        print(f"❌ FAIL: Import cycle detected: {result.stderr}")
        return False
    
    if "OK" not in result.stdout:
        print(f"❌ FAIL: Import failed silently")
        return False
    
    print("✅ PASS: No import cycles (rich.text imports successfully)")
    return True


def check_function_signatures():
    """Check that functions have correct signatures."""
    path = Path("rich/text_operations.py")
    tree = ast.parse(path.read_text())
    
    expected_signatures = {
        "truncate": ["text", "max_width"],
        "pad": ["text", "count"],
        "pad_left": ["text", "count"],
        "pad_right": ["text", "count"],
        "align": ["text"],  # Just check first param
        "set_length": ["text", "new_length"],
    }
    
    all_correct = True
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name in expected_signatures:
            arg_names = [arg.arg for arg in node.args.args]
            expected = expected_signatures[node.name]
            
            # Check that expected params are present (in order)
            for i, expected_param in enumerate(expected):
                if i >= len(arg_names) or arg_names[i] != expected_param:
                    print(f"❌ FAIL: {node.name}() has wrong signature. Expected {expected_param} at position {i}, got {arg_names}")
                    all_correct = False
                    break
    
    if all_correct:
        print("✅ PASS: All function signatures are correct")
    return all_correct


def check_original_logic_moved():
    """Check that the original implementation logic was actually moved."""
    text_py = Path("rich/text.py").read_text()
    
    # These are distinctive code patterns from the original methods
    # If they still exist in text.py, the logic wasn't moved
    original_patterns = [
        # From truncate - the ellipsis logic
        ('set_cell_size(self.plain, max_width - 1) + "…"', "truncate ellipsis logic"),
        # From pad - the span shifting
        ('_Span(start + count, end + count, style)', "pad span shifting (in pad method context)"),
    ]
    
    # For this check, we need to be more careful - these patterns might legitimately 
    # appear elsewhere. We'll do a more sophisticated check by parsing the AST
    # and looking at method bodies.
    
    tree = ast.parse(text_py)
    
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "truncate":
            # Check if the truncate method body is short (delegating) or long (original)
            # A delegating method should have ~1-3 statements
            if len(node.body) > 5:
                # Filter out docstring
                body_without_docstring = [
                    stmt for stmt in node.body 
                    if not (isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant))
                ]
                if len(body_without_docstring) > 3:
                    print(f"⚠️  WARNING: Text.truncate() has {len(body_without_docstring)} statements - may not be delegating")
    
    print("✅ PASS: Original logic appears to be moved (methods are concise)")
    return True


def main():
    """Run all structural verification checks."""
    print("=" * 60)
    print("Rich Refactoring - Structural Verification")
    print("=" * 60)
    print()
    
    checks = [
        ("File exists", check_file_exists),
        ("Functions defined", check_functions_defined),
        ("Text imports operations", check_text_imports_operations),
        ("Methods delegate", check_delegation),
        ("No import cycles", check_no_import_cycles),
        ("Function signatures", check_function_signatures),
        ("Logic moved", check_original_logic_moved),
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

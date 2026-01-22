"""Pre-flight checks for experiment environments."""

import argparse
import shutil
import subprocess
import sys
from dataclasses import dataclass


@dataclass
class CheckResult:
    language: str
    ok: bool
    message: str
    version: str | None = None


# Map language to (command, args) for version check
LANGUAGE_CHECKS: dict[str, tuple[str, list[str]]] = {
    "Python": ("python3", ["--version"]),
    "Go": ("go", ["version"]),
    "Rust": ("cargo", ["--version"]),
    "Clojure": ("java", ["-version"]),  # Clojure needs Java runtime
    "Elixir": ("elixir", ["--version"]),
    "Ruby": ("ruby", ["--version"]),
    "Lua": ("lua", ["-v"]),
    "Haskell": ("ghc", ["--version"]),
    "JavaScript": ("node", ["--version"]),
    "TypeScript": ("node", ["--version"]),  # TypeScript runs on Node
}

# Additional checks beyond the main runtime
EXTRA_CHECKS: dict[str, list[tuple[str, list[str], str]]] = {
    "Clojure": [("lein", ["version"], "leiningen required for Clojure projects")],
    "Lua": [("luarocks", ["--version"], "luarocks for package management")],
}


def check_language(lang: str) -> CheckResult:
    """Check if a language runtime is available."""
    check = LANGUAGE_CHECKS.get(lang)
    if not check:
        return CheckResult(lang, True, "no check defined", None)
    
    cmd, args = check
    
    # First check if command exists
    if not shutil.which(cmd):
        return CheckResult(lang, False, f"{cmd} not found in PATH", None)
    
    # Try to run it
    try:
        result = subprocess.run(
            [cmd] + args,
            capture_output=True,
            timeout=10,
        )
        # java -version writes to stderr and may exit non-zero on some systems
        output = result.stdout.decode().strip() or result.stderr.decode().strip()
        version = output.split("\n")[0][:60] if output else None
        
        # java -version can exit 1 but still work (check if we got version output)
        if result.returncode != 0 and not version:
            return CheckResult(lang, False, f"exited with code {result.returncode}", version)
        
        return CheckResult(lang, True, "ok", version)
    except subprocess.TimeoutExpired:
        return CheckResult(lang, False, "timeout", None)
    except Exception as e:
        return CheckResult(lang, False, str(e)[:60], None)


def check_extras(lang: str) -> list[CheckResult]:
    """Check additional dependencies for a language."""
    extras = EXTRA_CHECKS.get(lang, [])
    results = []
    
    for cmd, args, desc in extras:
        if not shutil.which(cmd):
            results.append(CheckResult(f"{lang}/{cmd}", False, f"{cmd} not found ({desc})", None))
            continue
        
        try:
            result = subprocess.run([cmd] + args, capture_output=True, timeout=10)
            output = result.stdout.decode().strip() or result.stderr.decode().strip()
            version = output.split("\n")[0][:60] if output else None
            results.append(CheckResult(f"{lang}/{cmd}", True, "ok", version))
        except Exception as e:
            results.append(CheckResult(f"{lang}/{cmd}", False, str(e)[:60], None))
    
    return results


def run_preflight(languages: list[str], verbose: bool = False) -> bool:
    """Run preflight checks for given languages. Returns True if all pass."""
    all_ok = True
    
    for lang in languages:
        result = check_language(lang)
        
        if result.ok:
            symbol = "✓"
            detail = result.version if verbose and result.version else "ok"
        else:
            symbol = "✗"
            detail = result.message
            all_ok = False
        
        print(f"{symbol} {lang}: {detail}")
        
        # Check extras
        for extra in check_extras(lang):
            if extra.ok:
                symbol = "  ✓"
                detail = extra.version if verbose and extra.version else "ok"
            else:
                symbol = "  ✗"
                detail = extra.message
                all_ok = False
            
            name = extra.language.split("/")[1]  # e.g., "Clojure/lein" -> "lein"
            print(f"{symbol} {name}: {detail}")
    
    return all_ok


def main():
    parser = argparse.ArgumentParser(
        prog="speedway-preflight",
        description="Check if language runtimes are available for experiments"
    )
    parser.add_argument(
        "--languages", "-l",
        help="Comma-separated languages to check (default: all known)"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show version info"
    )
    parser.add_argument(
        "--all", "-a",
        action="store_true",
        help="Check all known languages"
    )
    
    args = parser.parse_args()
    
    if args.languages:
        languages = [l.strip() for l in args.languages.split(",")]
    elif args.all:
        languages = list(LANGUAGE_CHECKS.keys())
    else:
        # Default to commonly used ones
        languages = ["Python", "Go", "Rust", "Elixir", "Clojure"]
    
    ok = run_preflight(languages, verbose=args.verbose)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()

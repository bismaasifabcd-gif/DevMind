"""
readme_reader.py
────────────────
Reads the README (any common format) from a repo directory and returns
its content as plain text.  Also collects a lightweight "repo manifest" —
a list of all .py files with their first-docstring/comment — so the LLM
has a full picture of the codebase without needing to read every file.
"""
import os
import ast

# Common README filenames, in priority order
_README_NAMES = [
    "README.md", "README.MD", "readme.md",
    "README.rst", "readme.rst",
    "README.txt", "readme.txt",
    "README",
]

_SKIP_DIRS = {"venv", ".venv", "env", "node_modules", "__pycache__", ".git"}


def read_readme(repo_path: str) -> str:
    """
    Return the README content (up to 4000 chars) or an empty string if none found.
    Truncated to keep LLM context manageable.
    """
    for name in _README_NAMES:
        candidate = os.path.join(repo_path, name)
        if os.path.isfile(candidate):
            try:
                with open(candidate, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read(4000)
                print(f"[readme_reader] Found README: {name} ({len(content)} chars)")
                return content
            except Exception:
                pass
    return ""


def build_repo_manifest(repo_path: str) -> str:
    """
    Walk the repo and build a compact manifest:

        file.py — <first docstring or first comment, one line>

    This gives the LLM enough context to understand what every file does
    without reading all of them in full.  Capped at 3000 chars total.
    """
    lines = []
    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in _SKIP_DIRS]
        for fname in sorted(files):
            if not fname.endswith(".py"):
                continue
            if fname.startswith("test_") or fname.endswith("_test.py"):
                continue
            if fname.startswith("_agent_generated_"):
                continue
            rel = os.path.relpath(os.path.join(root, fname), repo_path)
            summary = _one_line_summary(os.path.join(root, fname))
            lines.append(f"  {rel} — {summary}")

    manifest = "Python files in this repo:\n" + "\n".join(lines)
    return manifest[:3000]


def _one_line_summary(path: str) -> str:
    """Extract the module docstring or first # comment as a one-liner."""
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            source = f.read(2000)

        # Try AST docstring first
        try:
            tree = ast.parse(source)
            docstring = ast.get_docstring(tree)
            if docstring:
                return docstring.split("\n")[0].strip()[:120]
        except SyntaxError:
            pass

        # Fall back to first # comment
        for line in source.splitlines():
            stripped = line.strip()
            if stripped.startswith("#") and len(stripped) > 2:
                return stripped[1:].strip()[:120]

        return "(no description)"
    except Exception:
        return "(unreadable)"

"""
issue_detector.py — Zero LLM calls, zero subprocesses for analysis
────────────────────────────────────────────────────────────────────
Detection priority:
  1. Run pytest (subprocess) → failure output becomes the issue text
  2. Pure AST syntax check (in-process) → SyntaxErrors become the issue
  3. Nothing found → no issue

pyflakes subprocess removed — it was spawning child Python processes
that triggered macOS memory-pressure kills on the parent uvicorn process.
"""
import ast
import os
import shutil
import subprocess
import sys


def detect_issue(repo_path: str) -> dict:
    # Step 1: pytest
    test_result = _run_pytest(repo_path)
    if not test_result["no_tests"]:
        if not test_result["passed"]:
            return {
                "has_issue": True,
                "issue_text": (
                    "The test suite is failing. Test output:\n\n"
                    + test_result["stdout"][-2000:]
                ),
            }
        return {"has_issue": False, "issue_text": ""}

    # Step 2: AST-only static analysis (no subprocess)
    errors = _ast_analysis(repo_path)
    if errors:
        return {
            "has_issue": True,
            "issue_text": "Static analysis errors:\n\n" + "\n\n".join(errors),
        }

    return {"has_issue": False, "issue_text": "", "reason": "no_issues_found"}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _run_pytest(repo_path: str) -> dict:
    import tempfile
    env = {
        **os.environ,
        "TOKENIZERS_PARALLELISM":            "false",
        "OBJC_DISABLE_INITIALIZE_FORK_SAFETY": "YES",
    }
    _clear_pycache(repo_path)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as o, \
         tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as e:
        out_path, err_path = o.name, e.name
    try:
        with open(out_path, "w") as out_f, open(err_path, "w") as err_f:
            proc = subprocess.Popen(
                [sys.executable, "-m", "pytest", "--tb=short", "-q",
                 "-p", "no:cacheprovider"],
                cwd=repo_path, stdout=out_f, stderr=err_f,
                env=env, start_new_session=True,
            )
        try:
            proc.wait(timeout=30)
        except subprocess.TimeoutExpired:
            proc.kill(); proc.wait()
            print("[issue_detector] pytest timed out — falling back to AST")
            return {"passed": False, "no_tests": True, "stdout": "", "stderr": "Timed out"}
        stdout   = open(out_path).read()
        no_tests = proc.returncode == 5
        return {"passed": proc.returncode == 0 or no_tests,
                "no_tests": no_tests, "stdout": stdout, "stderr": ""}
    except FileNotFoundError:
        return {"passed": False, "no_tests": True, "stdout": "", "stderr": "pytest not found"}
    finally:
        for p in (out_path, err_path):
            try: os.remove(p)
            except: pass


def _ast_analysis(repo_path: str) -> list:
    """
    Pure in-process AST syntax check — no subprocess, no memory spikes.
    Only reports SyntaxErrors and IndentationErrors.
    """
    skip = {"venv", ".venv", "env", "node_modules", "__pycache__", ".git"}
    errors = []
    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in skip]
        for f in files:
            if not f.endswith(".py"):
                continue
            path = os.path.join(root, f)
            rel  = os.path.relpath(path, repo_path)
            try:
                with open(path, "r", encoding="utf-8", errors="replace") as fh:
                    source = fh.read()
                ast.parse(source, filename=rel)
            except SyntaxError as e:
                errors.append(f"SyntaxError in {rel} line {e.lineno}: {e.msg}")
            except Exception as e:
                errors.append(f"Parse error in {rel}: {e}")
    return errors


def _clear_pycache(repo_path: str):
    skip = {"venv", ".venv", "env", "node_modules", ".git"}
    for root, dirs, _ in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in skip]
        cache = os.path.join(root, "__pycache__")
        if os.path.isdir(cache):
            shutil.rmtree(cache, ignore_errors=True)

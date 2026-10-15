"""
validator.py
────────────
apply-test-restore: backs up file, writes patch, runs pytest (30s hard limit),
restores original regardless. Real files never changed until Approve.
"""
import os
import sys
import shutil
import subprocess
import tempfile

_file_pick_cache: dict = {}


def validate(
    repo_path:     str,
    patched_file:  str = "",
    patch_content: str = "",
    hint:          str = "",
    issue_text:    str = "",
    readme:        str = "",
    manifest:      str = "",
) -> dict:
    _clear_pycache(repo_path)

    if _has_test_files(repo_path):
        if patch_content and patched_file:
            print("[validator] Path 1: apply-test-restore")
            return _apply_test_restore(repo_path, patched_file, patch_content)
        return _run_pytest(repo_path)

    if hint or patched_file:
        print("[validator] Path 2: syntax-check only")
        return _syntax_check(repo_path, patched_file or hint)

    print("[validator] Path 3: LLM-generated tests")
    return _run_with_generated_tests(
        repo_path=repo_path, patched_file=patched_file,
        issue_text=issue_text, readme=readme, manifest=manifest,
    )


def _apply_test_restore(repo_path: str, patched_file: str, patch_content: str) -> dict:
    """Write patch → run pytest (30s timeout) → restore original. Always."""
    target = (patched_file if os.path.isabs(patched_file)
              else os.path.join(repo_path, patched_file))

    original_content = None
    if os.path.isfile(target):
        with open(target, "r", encoding="utf-8", errors="replace") as f:
            original_content = f.read()

    try:
        os.makedirs(os.path.dirname(target) or ".", exist_ok=True)
        with open(target, "w", encoding="utf-8") as f:
            f.write(patch_content)

        return _run_pytest_safe(repo_path, timeout=30)

    finally:
        if original_content is not None:
            with open(target, "w", encoding="utf-8") as f:
                f.write(original_content)
        elif os.path.isfile(target):
            os.remove(target)


def _run_pytest_safe(repo_path: str, timeout: int = 30) -> dict:
    """Run pytest using temp files (no pipe deadlock) with a hard timeout."""
    _clear_pycache(repo_path)
    env = {
        **os.environ,
        "TOKENIZERS_PARALLELISM":            "false",
        "OBJC_DISABLE_INITIALIZE_FORK_SAFETY": "YES",
    }
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
            proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
            return _error(f"Tests timed out after {timeout}s")

        stdout   = open(out_path).read()
        no_tests = proc.returncode == 5
        return {
            "passed":          proc.returncode == 0 or no_tests,
            "no_tests":        no_tests,
            "generated":       False,
            "generated_tests": "",
            "stdout":          stdout,
            "stderr":          "",
            "returncode":      proc.returncode,
        }
    except FileNotFoundError as ex:
        return _error(str(ex))
    finally:
        for p in (out_path, err_path):
            try: os.remove(p)
            except: pass


# keep _run_pytest as alias used elsewhere
def _run_pytest(repo_path: str, extra_args: list = None) -> dict:
    return _run_pytest_safe(repo_path, timeout=60)


def _has_test_files(repo_path: str) -> bool:
    skip = {"venv", ".venv", "env", "node_modules", "__pycache__", ".git"}
    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in skip]
        for f in files:
            if f.startswith("_agent_generated_"):
                continue
            if f.startswith("test_") or f.endswith("_test.py"):
                return True
    return False


def _syntax_check(repo_path: str, file_hint: str) -> dict:
    target = (file_hint if os.path.isabs(file_hint)
              else os.path.join(repo_path, file_hint))
    if not os.path.isfile(target):
        return _ok("Target file not found — skipping syntax check")
    try:
        with open(target, "r", encoding="utf-8", errors="replace") as f:
            source = f.read()
        compile(source, file_hint, "exec")
    except SyntaxError as e:
        return _error(f"SyntaxError in {file_hint} line {e.lineno}: {e.msg}")
    return _ok("Syntax check passed")


def _run_with_generated_tests(
    repo_path: str, patched_file: str = "", issue_text: str = "",
    readme: str = "", manifest: str = "",
) -> dict:
    from agent.test_generator import (
        collect_importable_files, pick_file_with_llm, write_generated_tests,
    )
    cache_key = repo_path
    target = None
    if patched_file:
        abs_p = (patched_file if os.path.isabs(patched_file)
                 else os.path.join(repo_path, patched_file))
        if os.path.isfile(abs_p):
            target = abs_p
            _file_pick_cache[cache_key] = target
    if target is None and cache_key in _file_pick_cache:
        target = _file_pick_cache[cache_key]
    if target is None:
        importable = collect_importable_files(repo_path)
        if not importable:
            return _error("No importable source files found.")
        target = pick_file_with_llm(importable, repo_path, manifest, issue_text)
        if target:
            _file_pick_cache[cache_key] = target
    if not target:
        return _error("Could not determine which file to test.")

    generated_test_path = None
    generated_code = ""
    try:
        generated_test_path = write_generated_tests(
            source_path=target, repo_path=repo_path,
            readme=readme, manifest=manifest,
        )
        with open(generated_test_path) as f:
            generated_code = f.read()
        result = _run_pytest_safe(repo_path, timeout=60)
        result["generated"] = True
        result["generated_tests"] = generated_code
        result["no_tests"] = False
        return result
    except Exception as e:
        return {"passed": False, "no_tests": False, "generated": True,
                "generated_tests": generated_code, "stdout": "",
                "stderr": f"Test generation failed: {e}", "returncode": -1}
    finally:
        if generated_test_path and os.path.exists(generated_test_path):
            os.remove(generated_test_path)


def _ok(note: str = "") -> dict:
    return {"passed": True, "no_tests": True, "generated": False,
            "generated_tests": "", "stdout": note, "stderr": "", "returncode": 0}


def _error(msg: str) -> dict:
    return {"passed": False, "no_tests": False, "generated": False,
            "generated_tests": "", "stdout": "", "stderr": msg, "returncode": -1}


def _clear_pycache(repo_path: str):
    skip = {"venv", ".venv", "env", "node_modules", ".git"}
    for root, dirs, _ in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in skip]
        cache = os.path.join(root, "__pycache__")
        if os.path.isdir(cache):
            shutil.rmtree(cache, ignore_errors=True)

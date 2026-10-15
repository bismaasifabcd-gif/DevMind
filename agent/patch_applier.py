"""
patch_applier.py
────────────────
Two modes:

  parse_patch(executor_output, repo_path)
      → parses + validates the LLM output, returns
        {success, filename, content, ...} but does NOT write to disk.

  apply_patch_to_disk(filename, content, repo_path)
      → writes a previously-parsed patch to the real file on disk.
        Only called from /approve — never during validation.
"""
import os
import re


def parse_patch(executor_output: str, repo_path: str) -> dict:
    """
    Parse and validate executor output.
    Returns a result dict with 'content' and 'filename' but
    does NOT write anything to disk.
    """
    if not executor_output or not executor_output.strip():
        return {"success": False, "error": "Executor output was empty"}

    header_match = re.search(
        r"FILENAME:\s*(.+?)\s*\n+CODE:\s*\n",
        executor_output,
        re.IGNORECASE,
    )
    if not header_match:
        # Fallback: try to find a Python code block even without markers
        fence = re.search(r"```python\n(.*?)```", executor_output, re.DOTALL)
        if fence:
            # Try to guess filename from context
            fn_guess = re.search(r"([a-zA-Z_][a-zA-Z0-9_]*\.py)", executor_output)
            filename = fn_guess.group(1) if fn_guess else "fixed_file.py"
            code = fence.group(1).strip()
            # validate + write
            try:
                compile(code, filename, "exec")
            except SyntaxError as e:
                return {"success": False,
                        "error": f"Generated code has SyntaxError: {e}"}
            return {
                "success": True,
                "filename": filename,
                "content": code + "\n",
                "file_path": os.path.join(repo_path, filename),
            }
        return {
            "success": False,
            "error": "Could not parse executor output (missing FILENAME:/CODE: markers)",
            "raw_output": executor_output,
        }

    filename = header_match.group(1).strip()
    if not filename:
        return {"success": False, "error": "Parsed filename was empty"}

    rest = executor_output[header_match.end():]

    fence_match = re.match(r"^```[a-zA-Z]*\n(.*?)\n```", rest, re.DOTALL)
    if fence_match:
        code = fence_match.group(1).strip()
    else:
        next_marker = re.search(r"\n\s*FILENAME:\s*", rest, re.IGNORECASE)
        code = rest[:next_marker.start()] if next_marker else rest
        code = code.strip()

    if not code:
        return {"success": False, "error": "Parsed code was empty"}

    # Syntax validation
    try:
        compile(code, filename, "exec")
    except SyntaxError as e:
        return {
            "success": False,
            "error": f"Generated code has SyntaxError at line {e.lineno}: {e.msg}",
            "filename": filename,
        }

    # Size safety — reject if LLM truncated the file significantly
    real_path = os.path.join(repo_path, filename)
    if os.path.isfile(real_path):
        try:
            original_lines = sum(1 for _ in open(real_path))
            new_lines = len(code.splitlines())
            if original_lines > 30 and new_lines < original_lines * 0.4:
                return {
                    "success": False,
                    "error": (
                        f"Patch rejected: {new_lines} lines generated but original "
                        f"has {original_lines}. LLM likely truncated the file."
                    ),
                    "filename": filename,
                }
        except Exception:
            pass

    return {
        "success":   True,
        "filename":  filename,
        "content":   code + "\n",
        # real_path stored for convenience
        "file_path": real_path,
    }


def apply_patch_to_disk(filename: str, content: str, repo_path: str) -> dict:
    """
    Write the validated patch content to the real file on disk.
    Called ONLY from /approve — never during the agent run.
    """
    file_path = os.path.join(repo_path, filename)
    try:
        os.makedirs(os.path.dirname(file_path) or ".", exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"[patch_applier] Written to disk: {file_path}")
        return {"success": True, "filename": filename, "file_path": file_path}
    except Exception as e:
        return {"success": False, "error": str(e), "filename": filename}


# Keep old name as alias so existing imports don't break
def apply_patch(executor_output: str, repo_path: str) -> dict:
    """Alias kept for backward compatibility — calls parse_patch."""
    return parse_patch(executor_output, repo_path)

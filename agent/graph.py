"""
graph.py — Clean agent pipeline with GitHub remote support
─────────────────────────────────────────────────────────
Token budget per run (llama-3.1-8b-instant):
  planner  : ~3 000 tokens  (1 call)
  executor : ~3 000 tokens  (1 call)
  retry    : executor only, plan reused from cache
  TOTAL    : 2 LLM calls on first attempt, 1 per retry

Context slicing:
  - When file_name hint given → read ONLY that file, send lines
    around each detected error (±40 lines) instead of the whole file.
  - When no hint → vector-retrieved context (already small).

Plan caching:
  - Plan is computed once and stored in state.
  - On retry only executor is re-called with the previous plan.

GitHub Integration:
  - Supports both local paths and GitHub URLs
  - Automatically clones remote repositories
  - Can work with GitHub issues directly
"""
import os
import re
import time
from typing import TypedDict, Optional
from langgraph.graph import StateGraph, END

from agent.planner import run_planner
from agent.executor import run_executor
from agent.validator import validate
from agent.github_handler import create_branch, commit_file, create_pull_request
from agent.readme_reader import read_readme, build_repo_manifest
from agent.issue_detector import detect_issue
from agent.github_repo_manager import repo_manager
# retrieval imports are lazy — only loaded when no file hint given

MAX_RETRIES = 2


class AgentState(TypedDict):
    repo_path:           str
    repo_full_name:      str
    hint:                str
    issue_text:          str
    user_provided_issue: bool
    github_issue_number: Optional[int]  # For GitHub issue integration
    is_remote_repo:      bool          # True if repo was cloned from GitHub
    original_repo_input: str           # Original input (URL or path)
    readme:              str
    manifest:            str
    has_issue:           bool
    retrieved_context:   str
    plan:                str
    plan_locked:         bool   # True once plan is computed; retries skip planner
    patch:               str
    apply_result:        dict
    test_result:         dict
    patched_file:        Optional[str]
    generated_tests:     str
    retries:             int
    human_approved:      bool
    pr_result:           dict


# ── Nodes ─────────────────────────────────────────────────────────────────────

def github_setup_node(state: AgentState) -> dict:
    """
    Handle GitHub repository setup - clone if needed, extract issues if specified
    """
    original_input = state["original_repo_input"]
    repo_full_name = state.get("repo_full_name", "")
    github_issue_number = state.get("github_issue_number")
    
    # Check if input is a GitHub URL or repo name
    parsed_repo = repo_manager.parse_github_url(original_input)
    
    if parsed_repo:
        # This is a GitHub repository
        print(f"[github_setup] Detected GitHub repo: {parsed_repo}")
        
        # Clone the repository
        try:
            local_path = repo_manager.clone_repository(parsed_repo)
            print(f"[github_setup] Cloned to: {local_path}")
            
            updates = {
                "repo_path": local_path,
                "repo_full_name": parsed_repo,
                "is_remote_repo": True
            }
            
            # If GitHub issue number is provided, fetch issue details
            if github_issue_number:
                try:
                    issue_details = repo_manager.get_issue_details(parsed_repo, github_issue_number)
                    issue_text = f"GitHub Issue #{issue_details['number']}: {issue_details['title']}\n\n"
                    issue_text += f"Description:\n{issue_details['body']}\n\n"
                    
                    if issue_details['comments']:
                        issue_text += "Recent comments:\n"
                        for comment in issue_details['comments'][-3:]:  # Last 3 comments
                            issue_text += f"- {comment['user']}: {comment['body'][:200]}...\n"
                    
                    updates.update({
                        "issue_text": issue_text,
                        "user_provided_issue": True
                    })
                    print(f"[github_setup] Loaded GitHub issue #{github_issue_number}")
                except Exception as e:
                    print(f"[github_setup] Failed to load issue #{github_issue_number}: {e}")
            
            return updates
            
        except Exception as e:
            print(f"[github_setup] Failed to clone repository: {e}")
            return {"has_issue": False, "issue_text": f"Failed to access repository: {e}"}
    
    else:
        # This is a local path
        print(f"[github_setup] Using local repository: {original_input}")
        return {
            "repo_path": original_input,
            "is_remote_repo": False
        }


def bootstrap_node(state: AgentState) -> dict:
    readme   = read_readme(state["repo_path"])
    manifest = build_repo_manifest(state["repo_path"])
    print(f"[bootstrap] readme={len(readme)}ch  manifest={len(manifest)}ch")
    return {"readme": readme, "manifest": manifest}


def detect_issue_node(state: AgentState) -> dict:
    if state.get("user_provided_issue") and state.get("issue_text"):
        print("[detect] user-provided issue — skip auto-detect")
        return {"has_issue": True}
    r = detect_issue(state["repo_path"])
    print(f"[detect] has_issue={r['has_issue']}")
    return {"has_issue": r["has_issue"], "issue_text": r.get("issue_text", "")}


def route_after_detection(state: AgentState) -> str:
    return "retrieval" if state["has_issue"] else "cleanup"


def cleanup_node(state: AgentState) -> dict:
    """Clean up temporary directories if using remote repo"""
    if state.get("is_remote_repo") and state.get("repo_full_name"):
        repo_manager.cleanup_repository(state["repo_full_name"])
        print("[cleanup] Temporary repository cleaned up")
    return {"pr_result": {"message": "No issues detected"}}


def retrieval_node(state: AgentState) -> dict:
    hint      = state.get("hint", "")
    repo_path = state["repo_path"]
    issue     = state.get("issue_text", "")

    if hint:
        full_ctx = _read_full_file(repo_path, hint)
        context  = f"File: {hint}\n{full_ctx}\n\nIssue:\n{issue[:600]}"
        print(f"[retrieval] full file: {len(context)} chars")
    else:
        # Extract files from test output — also check what test files import
        mentioned = re.findall(r"(\w+\.py)", issue)
        py_files = [f for f in mentioned
                    if os.path.isfile(os.path.join(repo_path, f))
                    and not f.startswith("test_")]

        # If no source file found directly, scan test files for imports
        if not py_files:
            skip = {"venv", ".venv", "__pycache__", ".git"}
            for root, dirs, files in os.walk(repo_path):
                dirs[:] = [d for d in dirs if d not in skip]
                for fname in files:
                    if fname.startswith("test_") and fname.endswith(".py"):
                        try:
                            with open(os.path.join(root, fname)) as tf:
                                for line in tf:
                                    m = re.match(r"from (\w+) import|import (\w+)", line)
                                    if m:
                                        mod = m.group(1) or m.group(2)
                                        candidate = f"{mod}.py"
                                        if (os.path.isfile(os.path.join(repo_path, candidate))
                                                and not candidate.startswith("test_")):
                                            py_files.append(candidate)
                        except Exception:
                            pass
            py_files = list(dict.fromkeys(py_files))  # deduplicate

        if py_files:
            # Use the first non-test file mentioned
            target = py_files[0]
            full_ctx = _read_full_file(repo_path, target)
            context = f"File: {target}\n{full_ctx}\n\nTest failures:\n{issue[:1000]}"
            print(f"[retrieval] auto-detected file {target}: {len(context)} chars")
        else:
            # Fall back to vector search
            from retrieval.chunker import chunk_repo
            from retrieval.vector_store import index_chunks, retrieve_context
            repo_name = os.path.basename(repo_path)
            chunks    = chunk_repo(repo_path)
            index_chunks(repo_name, chunks)
            context = retrieve_context(repo_name, issue[:600])
            print(f"[retrieval] vector context: {len(context)} chars")

    return {"retrieved_context": context}


def planner_node(state: AgentState) -> dict:
    """LLM call #1 — always runs fresh (no cache, so retries get a better plan)."""
    issue = state["issue_text"]
    if state.get("hint"):
        issue = f"Focus on file: {state['hint']}\n\n{issue}"

    plan = run_planner(issue, state["retrieved_context"])
    print(f"[planner] plan ({len(plan)} chars)")
    return {"plan": plan, "plan_locked": True}


def executor_node(state: AgentState) -> dict:
    """LLM call #2 — reads the ACTUAL current file from disk before generating fix."""
    repo_path    = state["repo_path"]
    hint         = state.get("hint", "")
    patched_file = state.get("patched_file", "")

    # Resolve which file to fix from the plan or hint
    target_file = hint or patched_file or ""

    # If no hint, try to extract filename from the plan
    if not target_file and state.get("plan"):
        import re
        m = re.search(r"`?([a-zA-Z_][a-zA-Z0-9_/]*\.py)`?", state["plan"])
        if m:
            target_file = m.group(1)

    # Always read the current file from disk
    if target_file:
        file_path = (target_file if os.path.isabs(target_file)
                     else os.path.join(repo_path, target_file))
        if os.path.isfile(file_path):
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                current_content = f.read()
            context = (
                f"File: {target_file}\n"
                f"{current_content}\n\n"
                f"Test failures to fix:\n{state.get('issue_text','')[:800]}"
            )
        else:
            context = state["retrieved_context"]
    else:
        context = state["retrieved_context"]

    patch = run_executor(state["plan"], context)
    print(f"[executor] patch ({len(patch)} chars)")
    return {"patch": patch}


def apply_patch_node(state: AgentState) -> dict:
    """
    Parse and validate the patch output — does NOT write to disk.
    The real file is only written when the user clicks Approve.
    """
    from agent.patch_applier import parse_patch
    result = parse_patch(state["patch"], state["repo_path"])
    ok = result.get("success", False)
    print(f"[parse_patch] success={ok}  file={result.get('filename','?')}")
    return {
        "apply_result": result,
        "patched_file": result.get("filename", "") if ok else state.get("patched_file", ""),
    }


def validator_node(state: AgentState) -> dict:
    """
    Validate in a temp copy — real repo files are never touched.
    """
    apply_result = state.get("apply_result", {})
    result = validate(
        repo_path     = state["repo_path"],
        patched_file  = state.get("patched_file", ""),
        patch_content = apply_result.get("content", ""),
        hint          = state.get("hint", ""),
        issue_text    = state.get("issue_text", ""),
        readme        = state.get("readme", ""),
        manifest      = state.get("manifest", ""),
    )
    print(f"[validator] passed={result['passed']}  generated={result.get('generated',False)}")
    return {
        "test_result":     result,
        "generated_tests": result.get("generated_tests", ""),
    }


def should_retry(state: AgentState) -> str:
    if not state.get("apply_result", {}).get("success"):
        return "end" if state["retries"] >= MAX_RETRIES else "retry"
    if state["test_result"].get("passed"):
        return "end"
    return "end" if state["retries"] >= MAX_RETRIES else "retry"


def increment_retry(state: AgentState) -> dict:
    return {"retries": state["retries"] + 1}


# ── PR creation (called from /approve, not in graph) ─────────────────────────

def create_pr_from_state(state: dict) -> dict:
    """
    Called only when user clicks Approve.
    1. Writes the patch to the real file on disk.
    2. Creates the GitHub branch + commit + PR.
    """
    from agent.patch_applier import apply_patch_to_disk

    apply_result = state.get("apply_result") or {}
    if not apply_result.get("success"):
        raise RuntimeError("No valid patch in state — cannot apply or create PR.")

    repo_full_name = state.get("repo_full_name", "")
    if not repo_full_name:
        raise RuntimeError("repo_full_name missing.")

    filename = apply_result["filename"]
    content  = apply_result["content"]
    repo_path = state["repo_path"]

    # Step 1: write to local disk
    disk_result = apply_patch_to_disk(filename, content, repo_path)
    if not disk_result.get("success"):
        raise RuntimeError(f"Failed to write patch to disk: {disk_result.get('error')}")

    # Step 2: create GitHub PR
    branch = f"agent-fix-{int(time.time())}"
    create_branch(branch, repo_full_name=repo_full_name)
    commit_file(
        branch_name    = branch,
        file_path      = filename,
        new_content    = content,
        commit_message = "Automated fix by SWE agent",
        repo_full_name = repo_full_name,
    )
    pr = create_pull_request(
        branch_name    = branch,
        title          = "Automated fix from SWE agent",
        body           = f"**Issue:**\n{state['issue_text']}\n\n**Plan:**\n{state['plan']}",
        repo_full_name = repo_full_name,
    )
    return {"pr_url": pr.html_url}


# ── Context slicing helper ────────────────────────────────────────────────────

def _slice_file_context(repo_path: str, hint: str, issue: str,
                        window: int = 40) -> str:
    """Return lines ±window around error line numbers found in issue text."""
    import re

    file_path = hint if os.path.isabs(hint) else os.path.join(repo_path, hint)
    if not os.path.isfile(file_path):
        return ""

    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        lines = f.readlines()

    total = len(lines)
    nums = [int(m) for m in re.findall(r"\bline[s]?\s+(\d+)", issue, re.I)]
    nums += [int(m) for m in re.findall(r":\s*(\d+)\s*:", issue)]
    nums = sorted(set(n for n in nums if 1 <= n <= total))

    if not nums:
        snippet = "".join(lines[:80])
    else:
        segments = []
        for n in nums:
            start = max(0, n - window - 1)
            end   = min(total, n + window)
            if segments and start <= segments[-1][1]:
                segments[-1] = (segments[-1][0], end)
            else:
                segments.append((start, end))
        snippet = ""
        for s, e in segments:
            snippet += f"# --- lines {s+1}–{e} ---\n"
            snippet += "".join(lines[s:e])

    return f"File: {hint}\n{snippet}"


def _read_full_file(repo_path: str, hint: str) -> str:
    """Return the complete content of the hinted file."""
    file_path = hint if os.path.isabs(hint) else os.path.join(repo_path, hint)
    if not os.path.isfile(file_path):
        return ""
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


# ── Compile graph ─────────────────────────────────────────────────────────────

workflow = StateGraph(AgentState)
workflow.add_node("github_setup",    github_setup_node)
workflow.add_node("bootstrap",       bootstrap_node)
workflow.add_node("detect_issue",    detect_issue_node)
workflow.add_node("retrieval",       retrieval_node)
workflow.add_node("planner",         planner_node)
workflow.add_node("executor",        executor_node)
workflow.add_node("apply_patch",     apply_patch_node)
workflow.add_node("validator",       validator_node)
workflow.add_node("increment_retry", increment_retry)
workflow.add_node("cleanup",         cleanup_node)

workflow.set_entry_point("github_setup")
workflow.add_edge("github_setup",    "bootstrap")
workflow.add_edge("bootstrap",       "detect_issue")
workflow.add_conditional_edges("detect_issue", route_after_detection,
                               {"retrieval": "retrieval", "cleanup": "cleanup"})
workflow.add_edge("retrieval",       "planner")
workflow.add_edge("planner",         "executor")
workflow.add_edge("executor",        "apply_patch")
workflow.add_edge("apply_patch",     "validator")
workflow.add_conditional_edges("validator", should_retry,
                               {"retry": "increment_retry", "end": END})
workflow.add_edge("increment_retry", "executor")
workflow.add_edge("cleanup",         END)

app = workflow.compile()

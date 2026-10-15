import time
import uuid
import json
import asyncio
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from agent.graph import app as agent_app, create_pr_from_state
from llmops.tracing import setup_tracing
from fastapi.middleware.cors import CORSMiddleware

try:
    setup_tracing()
except Exception as e:
    print(f"[tracing] non-fatal: {e}")

app = FastAPI(title="Autonomous SWE Agent API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

_executor = ThreadPoolExecutor(max_workers=2)

# ── Persistent pending runs ───────────────────────────────────────────────────
# Stored on disk so they survive server restarts.
_RUNS_FILE = Path(__file__).parent.parent / "pending_runs.json"


def _load_runs() -> dict:
    try:
        if _RUNS_FILE.exists():
            return json.loads(_RUNS_FILE.read_text())
    except Exception:
        pass
    return {}


def _save_runs(runs: dict):
    try:
        _RUNS_FILE.write_text(json.dumps(runs, default=str))
    except Exception as e:
        print(f"[runs] Could not save pending runs: {e}")


# Load existing runs on startup
pending_runs: dict = _load_runs()
print(f"[runs] Loaded {len(pending_runs)} pending run(s) from disk")


class IssueRequest(BaseModel):
    repo_path: str  # Can now be a GitHub URL, owner/repo, or local path
    repo_full_name: str | None = None  # Optional - will be extracted from repo_path if GitHub
    issue_text: str | None = None
    issue_number: int | None = None  # GitHub issue number to load automatically
    file_name: str | None = None
    function_name: str | None = None


@app.get("/github/info/{owner}/{repo}")
async def get_github_repo_info(owner: str, repo: str):
    """Get GitHub repository information"""
    from agent.github_repo_manager import repo_manager
    try:
        repo_full_name = f"{owner}/{repo}"
        info = repo_manager.get_repository_info(repo_full_name)
        return {"success": True, "data": info}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/github/issues/{owner}/{repo}")
async def get_github_issues(owner: str, repo: str, limit: int = 10):
    """Get open issues from GitHub repository"""
    from agent.github_repo_manager import repo_manager
    try:
        repo_full_name = f"{owner}/{repo}"
        issues = repo_manager.get_open_issues(repo_full_name, limit)
        return {"success": True, "data": issues}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/github/issue/{owner}/{repo}/{issue_number}")
async def get_github_issue_details(owner: str, repo: str, issue_number: int):
    """Get detailed information about a specific GitHub issue"""
    from agent.github_repo_manager import repo_manager
    try:
        repo_full_name = f"{owner}/{repo}"
        issue = repo_manager.get_issue_details(repo_full_name, issue_number)
        return {"success": True, "data": issue}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/runs")
def get_runs(n: int = 10):
    """Return the last n MLflow runs for the LLMOps dashboard."""
    from llmops.metrics import get_recent_runs
    return {"runs": get_recent_runs(n)}


@app.get("/")
def root():
    return {"status": "Agent API running"}


@app.post("/run-agent")
async def run_agent(request: IssueRequest):
    from agent.github_repo_manager import repo_manager
    
    start_time = time.time()
    
    # Parse GitHub repo if provided
    parsed_repo = None
    if request.repo_path:
        parsed_repo = repo_manager.parse_github_url(request.repo_path)
    
    initial_state = {
        "has_issue":             False,
        "issue_text":            request.issue_text or "",
        "user_provided_issue":   request.issue_text is not None or request.issue_number is not None,
        "github_issue_number":   request.issue_number,
        "is_remote_repo":        False,
        "original_repo_input":   request.repo_path,
        "hint":                  request.file_name or request.function_name or "",
        "retrieved_context":     "",
        "plan":                  "",
        "patch":                 "",
        "apply_result":          {},
        "test_result":           {},
        "retries":               0,
        "repo_path":             "",  # Will be set by github_setup_node
        "repo_full_name":        request.repo_full_name or parsed_repo or "",
        "human_approved":        False,
        "pr_result":             {},
        "patched_file":          "",
        "generated_tests":       "",
        "plan_locked":           False,
        "readme":                "",
        "manifest":              "",
    }

    # Run the synchronous langgraph agent in a thread pool
    # so it doesn't block FastAPI's async event loop
    loop = asyncio.get_event_loop()
    try:
        result = await loop.run_in_executor(
            _executor,
            lambda: agent_app.invoke(initial_state)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent error: {str(e)}")

    latency      = time.time() - start_time
    test_result  = result.get("test_result", {})
    generated    = test_result.get("generated", False)
    gen_tests    = result.get("generated_tests", "")

    # Determine final status string
    if not result.get("has_issue"):
        run_status = "no_issue_found"
    elif not test_result.get("passed"):
        run_status = "failed"
    else:
        run_status = "awaiting_approval"

    # Log to MLflow in background thread
    def _log():
        from llmops.metrics import log_agent_run
        log_agent_run(
            issue_text  = result.get("issue_text", ""),
            plan        = result.get("plan", ""),
            patch       = result.get("patch", ""),
            test_result = test_result,
            retries     = result.get("retries", 0),
            latency     = latency,
            repo_path   = request.repo_path,
            status      = run_status,
        )
    import threading
    threading.Thread(target=_log, daemon=True).start()

    if not result.get("has_issue"):
        return {"status": "no_issue_found", "message": "No issues detected — all checks passed."}

    if not test_result.get("passed"):
        return {
            "status":               "failed",
            "message":              "Agent could not produce a passing fix.",
            "plan":                 result.get("plan", ""),
            "patch":                result.get("patch", ""),
            "test_output":          (test_result.get("stdout","") + "\n" + test_result.get("stderr","")).strip(),
            "retries":              result.get("retries", 0),
            "generated_tests_used": generated,
            "generated_tests":      gen_tests,
        }

    run_id = str(uuid.uuid4())
    pending_runs[run_id] = result
    _save_runs(pending_runs)
    print(f"[runs] Stored run {run_id} — pending: {list(pending_runs.keys())}")

    return {
        "status":               "awaiting_approval",
        "run_id":               run_id,
        "plan":                 result["plan"],
        "patch":                result["patch"],
        "test_result":          test_result,
        "generated_tests_used": generated,
        "generated_tests":      gen_tests,
        "message":              "Fix verified. Approve to create a PR or reject to discard.",
    }


@app.post("/approve/{run_id}")
async def approve_run(run_id: str):
    state = pending_runs.get(run_id)
    if not state:
        raise HTTPException(status_code=404, detail="Run not found or already handled.")
    loop = asyncio.get_event_loop()
    try:
        pr_result = await loop.run_in_executor(
            _executor,
            lambda: create_pr_from_state(state)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PR creation failed: {str(e)}")
    del pending_runs[run_id]
    _save_runs(pending_runs)
    return {"status": "pr_created", **pr_result}


@app.post("/reject/{run_id}")
def reject_run(run_id: str):
    if run_id not in pending_runs:
        raise HTTPException(status_code=404, detail="Run not found or already handled.")
    del pending_runs[run_id]
    _save_runs(pending_runs)
    return {"status": "rejected", "message": "Run discarded, no PR created."}

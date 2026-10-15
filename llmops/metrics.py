"""
metrics.py — MLflow experiment tracking (lazy imports, never blocks startup)
"""
import os

_TRACKING_URI = "sqlite:///" + os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "mlflow.db"
)
_EXPERIMENT   = "swe-agent-runs"
_setup_done   = False


def _setup():
    global _setup_done
    if _setup_done:
        return
    import mlflow
    mlflow.set_tracking_uri(_TRACKING_URI)
    mlflow.set_experiment(_EXPERIMENT)
    _setup_done = True


def log_agent_run(
    issue_text:  str,
    plan:        str,
    patch:       str,
    test_result: dict,
    retries:     int,
    latency:     float,
    repo_path:   str = "",
    status:      str = "",
):
    """Log one agent run to MLflow. Called in a background thread from api/main.py."""
    try:
        _setup()
        import mlflow
        import re

        passed = 1 if test_result.get("passed") else 0

        # Derive a short repo name for the tag
        repo_name = os.path.basename(repo_path.rstrip("/")) if repo_path else "unknown"

        # Count lines changed in the patch
        lines_changed = sum(
            1 for line in patch.splitlines()
            if line.startswith("+") or line.startswith("-")
        ) if patch else 0

        with mlflow.start_run():
            # ── Parameters (fixed per run) ───────────────────────────────
            mlflow.log_param("repo",         repo_name)
            mlflow.log_param("status",       status or ("passed" if passed else "failed"))
            mlflow.log_param("issue_snippet", issue_text[:120] if issue_text else "auto-detected")

            # ── Metrics (numeric, plottable) ─────────────────────────────
            mlflow.log_metric("test_passed",    passed)
            mlflow.log_metric("latency_seconds", round(latency, 2))
            mlflow.log_metric("retries",         retries)
            mlflow.log_metric("lines_changed",   lines_changed)

            # ── Artifacts (full text, viewable in UI) ────────────────────
            if plan:
                mlflow.log_text(plan,  "plan.txt")
            if patch:
                mlflow.log_text(patch, "patch.txt")
            if test_result:
                out = test_result.get("stdout", "") or test_result.get("stderr", "")
                mlflow.log_text(out[:5000], "test_output.txt")

        print(f"[metrics] Run logged — passed={passed}, latency={latency:.1f}s, repo={repo_name}")
    except Exception as e:
        print(f"[metrics] MLflow logging failed (non-fatal): {e}")


def get_recent_runs(n: int = 10) -> list[dict]:
    """Return the last n runs as a list of dicts for the /runs API endpoint."""
    try:
        _setup()
        import mlflow
        client = mlflow.tracking.MlflowClient()
        exp = client.get_experiment_by_name(_EXPERIMENT)
        if not exp:
            return []

        runs = client.search_runs(
            experiment_ids=[exp.experiment_id],
            order_by=["start_time DESC"],
            max_results=n,
        )

        result = []
        for r in runs:
            m = r.data.metrics
            p = r.data.params
            result.append({
                "run_id":          r.info.run_id,
                "start_time":      r.info.start_time,          # ms epoch
                "status":          p.get("status", "—"),
                "repo":            p.get("repo", "—"),
                "issue_snippet":   p.get("issue_snippet", "—"),
                "test_passed":     int(m.get("test_passed", -1)),
                "latency_seconds": round(m.get("latency_seconds", 0), 1),
                "retries":         int(m.get("retries", 0)),
                "lines_changed":   int(m.get("lines_changed", 0)),
                "artifact_uri":    r.info.artifact_uri,
            })
        return result
    except Exception as e:
        print(f"[metrics] get_recent_runs failed: {e}")
        return []

"""
planner.py — uses shared round-robin LLM client
"""
from agent.llm_client import invoke_with_backoff

SYSTEM = """You are a senior software engineer planning a bug fix.
Given an issue and relevant code, output a concise plan (max 150 words):
1. File to change (one file only)
2. Exact lines/functions to fix and how
3. Nothing else — no explanations, no preamble."""


def run_planner(issue_text: str, context: str = "") -> str:
    from langchain_core.messages import HumanMessage, SystemMessage
    messages = [
        SystemMessage(content=SYSTEM),
        HumanMessage(content=(
            f"Issue:\n{issue_text[:600]}\n\n"
            f"File content:\n{context[:3000]}"
        )),
    ]
    return invoke_with_backoff(messages, tag="planner")

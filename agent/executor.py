"""
executor.py — uses shared round-robin LLM client
"""
from agent.llm_client import invoke_with_backoff

SYSTEM = """You are a software engineer fixing a specific bug in an existing Python file.

You MUST output EXACTLY this format — no other text:

FILENAME: <relative_filename>
CODE:
<complete file content with ONLY the bug fixed>

STRICT rules:
- The VERY FIRST LINE must be: FILENAME: <filename>
- The SECOND LINE must be: CODE:
- Then the complete file — copy the entire original, change only the buggy lines.
- NO markdown fences (no ```), NO explanations, NO comments outside code.
- Preserve ALL existing methods exactly as they are unless they contain the bug."""


def run_executor(plan: str, context: str = "") -> str:
    from langchain_core.messages import HumanMessage, SystemMessage
    messages = [
        SystemMessage(content=SYSTEM),
        HumanMessage(content=(
            f"Plan:\n{plan[:300]}\n\n"
            f"Original file:\n{context[:3000]}"
        )),
    ]
    return invoke_with_backoff(messages, tag="executor")

"""
llm_client.py
─────────────
Single place that manages all LLM instances.

- Supports 1 or 2 Groq API keys (round-robin rotation).
- With 2 keys: effective TPM doubles (12k → 24k per minute).
- Falls back gracefully to 1 key if GROQ_API_KEY_2 is not set.
- Lazy-loaded so startup is instant.
"""
import os
import time
import itertools
from dotenv import load_dotenv

load_dotenv()

_clients    = []   # list of ChatGroq instances
_rotator    = None # infinite round-robin iterator
_lock_count = 0


def _build_clients():
    global _clients, _rotator
    from langchain_groq import ChatGroq

    keys = []
    k1 = os.getenv("GROQ_API_KEY", "")
    k2 = os.getenv("GROQ_API_KEY_2", "")
    if k1:
        keys.append(k1)
    if k2 and k2 != k1:
        keys.append(k2)

    if not keys:
        raise ValueError("No GROQ_API_KEY found in environment.")

    _clients = [
        ChatGroq(
            model="llama-3.1-8b-instant",
            api_key=k,
            temperature=0,
            max_tokens=4096,
        )
        for k in keys
    ]
    _rotator = itertools.cycle(_clients)
    print(f"[llm_client] {len(_clients)} API key(s) loaded — round-robin active")


def get_llm():
    """Return the next LLM client in the rotation."""
    if not _clients:
        _build_clients()
    return next(_rotator)


def invoke_with_backoff(messages, tag: str = "llm", attempts: int = 4) -> str:
    """
    Call the LLM with automatic key rotation on rate-limit.
    On a 429, rotates to the next key immediately instead of sleeping.
    Falls back to sleeping only if all keys are exhausted.
    """
    if not _clients:
        _build_clients()

    n_keys = len(_clients)

    for attempt in range(attempts):
        try:
            client = next(_rotator)
            return client.invoke(messages).content
        except Exception as e:
            msg = str(e).lower()
            if "rate limit" in msg or "429" in msg or "too many" in msg:
                if attempt < n_keys - 1:
                    # We have another key — rotate immediately, no sleep
                    print(f"[{tag}] rate-limit on key {attempt+1}, rotating to next key")
                else:
                    # All keys hit — wait before retrying
                    wait = 20 * (attempt - n_keys + 2)
                    print(f"[{tag}] all keys rate-limited, waiting {wait}s")
                    time.sleep(wait)
            else:
                raise

    raise RuntimeError(f"[{tag}] rate-limit persisted after {attempts} attempts")

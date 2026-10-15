"""
vector_store.py
───────────────
All heavy imports (chromadb, sentence-transformers) are deferred until the
first actual call. This means importing this module is instant and won't
block or OOM-kill the server on startup.
"""

_client = None
_embedding_fn = None


def _get_client():
    global _client
    if _client is None:
        import chromadb
        _client = chromadb.PersistentClient(path="./chroma_db")
    return _client


def _get_embedding_fn():
    global _embedding_fn
    if _embedding_fn is None:
        from chromadb.utils import embedding_functions
        _embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2"
        )
    return _embedding_fn


def _safe_name(repo_name: str) -> str:
    safe = "".join(c if c.isalnum() or c == "-" else "-" for c in repo_name)
    safe = safe.strip("-")[:63]
    return safe if len(safe) >= 3 else safe + "---"


def get_or_create_collection(repo_name: str):
    return _get_client().get_or_create_collection(
        name=_safe_name(repo_name),
        embedding_function=_get_embedding_fn(),
    )


def index_chunks(repo_name: str, chunks: list):
    if not chunks:
        return
    collection = get_or_create_collection(repo_name)
    collection.upsert(
        documents=[c["content"] for c in chunks],
        metadatas=[{"file": c["file"]} for c in chunks],
        ids=[f"{_safe_name(repo_name)}_{i}" for i in range(len(chunks))],
    )


def retrieve_context(repo_name: str, query: str, top_k: int = 3) -> str:
    collection = get_or_create_collection(repo_name)
    if collection.count() == 0:
        return ""
    results = collection.query(
        query_texts=[query],
        n_results=min(top_k, collection.count()),
    )
    parts = [
        f"# {meta['file']}\n{doc}"
        for doc, meta in zip(results["documents"][0], results["metadatas"][0])
    ]
    return "\n\n---\n\n".join(parts)[:3000]

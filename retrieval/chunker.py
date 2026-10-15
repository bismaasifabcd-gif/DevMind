import os

def chunk_repo(repo_path: str, extensions=(".py",)) -> list[dict]:
    """
    Walks through repo_path and splits each code file into chunks.
    Returns list of dicts: {"file": path, "content": chunk_text}
    """
    chunks = []
    for root, _, files in os.walk(repo_path):
        if any(skip in root for skip in [".git", "venv", "__pycache__", "node_modules"]):
            continue
        for file in files:
            if file.endswith(extensions):
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, repo_path)
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()
                    if content.strip():
                        chunks.append({"file": rel_path, "content": content})
                except Exception:
                    continue
    return chunks
import os
import time
from dotenv import load_dotenv
from github import Github, Auth, GithubException

load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

# Lazy per-repo cache so we never crash at import time
_g = None
_repo_cache: dict = {}


def _get_repo(repo_full_name: str):
    """Return a lazily-initialised PyGitHub repo object.
    repo_full_name comes from the frontend (e.g. 'username/repo').
    """
    global _g

    if not GITHUB_TOKEN:
        raise ValueError("GITHUB_TOKEN missing in .env — PR creation is unavailable.")
    if not repo_full_name:
        raise ValueError(
            "repo_full_name is required (e.g. 'username/repo'). Pass it from the frontend."
        )

    if repo_full_name not in _repo_cache:
        if _g is None:
            _g = Github(auth=Auth.Token(GITHUB_TOKEN))
        _repo_cache[repo_full_name] = _g.get_repo(repo_full_name)
        print(f"[github_handler] Connected to: {repo_full_name}")

    return _repo_cache[repo_full_name]


def create_branch(branch_name: str, repo_full_name: str, base_branch: str = "main"):
    repo = _get_repo(repo_full_name)
    source = repo.get_branch(base_branch)
    try:
        repo.create_git_ref(ref=f"refs/heads/{branch_name}", sha=source.commit.sha)
        print(f"Branch created: {branch_name}")
    except GithubException as e:
        if e.status == 422:
            print(f"Branch already exists, reusing: {branch_name}")
        else:
            raise


def commit_file(branch_name: str, file_path: str, new_content: str,
                commit_message: str, repo_full_name: str):
    repo = _get_repo(repo_full_name)
    try:
        contents = repo.get_contents(file_path, ref=branch_name)
        repo.update_file(
            path=contents.path,
            message=commit_message,
            content=new_content,
            sha=contents.sha,
            branch=branch_name,
        )
        print(f"File updated: {file_path}")
    except GithubException as e:
        if e.status == 404:
            repo.create_file(
                path=file_path,
                message=commit_message,
                content=new_content,
                branch=branch_name,
            )
            print(f"File created: {file_path}")
        else:
            raise


def create_pull_request(branch_name: str, title: str, body: str,
                        repo_full_name: str, base_branch: str = "main"):
    repo = _get_repo(repo_full_name)
    pr = repo.create_pull(
        title=title,
        body=body,
        head=branch_name,
        base=base_branch,
    )
    print(f"PR created: {pr.html_url}")
    return pr

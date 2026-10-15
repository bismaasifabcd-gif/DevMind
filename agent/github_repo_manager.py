"""
github_repo_manager.py — Remote GitHub repository operations
──────────────────────────────────────────────────────────

Handles:
- Cloning repositories from GitHub URLs
- Fetching repository content without local copies
- Managing temporary workspaces for remote repos
- Issue extraction from GitHub API
"""
import os
import tempfile
import shutil
import subprocess
from typing import Optional, Dict, List
from pathlib import Path
from github import Github, Auth, GithubException
from dotenv import load_dotenv

load_dotenv()

class GitHubRepoManager:
    def __init__(self):
        self.github_token = os.getenv("GITHUB_TOKEN")
        self.temp_dirs: Dict[str, str] = {}  # repo_name -> temp_path
        self._github = None
        
    @property
    def github(self):
        """Lazy GitHub client initialization"""
        if self._github is None:
            if not self.github_token:
                raise ValueError("GITHUB_TOKEN not found in environment variables")
            self._github = Github(auth=Auth.Token(self.github_token))
        return self._github
    
    def parse_github_url(self, url_or_path: str) -> Optional[str]:
        """
        Extract owner/repo from various GitHub URL formats:
        - https://github.com/owner/repo
        - https://github.com/owner/repo.git
        - git@github.com:owner/repo.git
        - owner/repo (direct format)
        """
        url_or_path = url_or_path.strip()
        
        # Direct format: owner/repo
        if '/' in url_or_path and not url_or_path.startswith(('http', 'git@', '/')):
            parts = url_or_path.split('/')
            if len(parts) == 2:
                return url_or_path
        
        # HTTPS format
        if url_or_path.startswith('https://github.com/'):
            path = url_or_path.replace('https://github.com/', '')
            path = path.rstrip('.git')
            parts = path.split('/')
            if len(parts) >= 2:
                return f"{parts[0]}/{parts[1]}"
        
        # SSH format
        if url_or_path.startswith('git@github.com:'):
            path = url_or_path.replace('git@github.com:', '')
            path = path.rstrip('.git')
            parts = path.split('/')
            if len(parts) >= 2:
                return f"{parts[0]}/{parts[1]}"
        
        return None
    
    def clone_repository(self, repo_full_name: str) -> str:
        """
        Clone repository to a temporary directory.
        Returns the local path to the cloned repository.
        """
        if repo_full_name in self.temp_dirs:
            # Already cloned
            return self.temp_dirs[repo_full_name]
        
        # Create temporary directory
        temp_dir = tempfile.mkdtemp(prefix=f"devmind_{repo_full_name.replace('/', '_')}_")
        clone_url = f"https://github.com/{repo_full_name}.git"
        
        try:
            # Use GitHub token for private repos
            if self.github_token:
                clone_url = f"https://{self.github_token}@github.com/{repo_full_name}.git"
            
            # Clone repository
            result = subprocess.run([
                "git", "clone", clone_url, temp_dir
            ], capture_output=True, text=True, timeout=300)
            
            if result.returncode != 0:
                shutil.rmtree(temp_dir, ignore_errors=True)
                raise RuntimeError(f"Failed to clone repository: {result.stderr}")
            
            self.temp_dirs[repo_full_name] = temp_dir
            print(f"[github_repo_manager] Cloned {repo_full_name} to {temp_dir}")
            return temp_dir
            
        except Exception as e:
            shutil.rmtree(temp_dir, ignore_errors=True)
            raise RuntimeError(f"Error cloning repository {repo_full_name}: {str(e)}")
    
    def get_repository_info(self, repo_full_name: str) -> Dict:
        """Get repository metadata from GitHub API"""
        try:
            repo = self.github.get_repo(repo_full_name)
            return {
                "name": repo.name,
                "full_name": repo.full_name,
                "description": repo.description,
                "language": repo.language,
                "default_branch": repo.default_branch,
                "private": repo.private,
                "clone_url": repo.clone_url,
                "ssh_url": repo.ssh_url,
                "html_url": repo.html_url,
                "size": repo.size,
                "open_issues": repo.open_issues_count,
                "stargazers": repo.stargazers_count,
            }
        except GithubException as e:
            raise RuntimeError(f"Failed to fetch repository info: {str(e)}")
    
    def get_open_issues(self, repo_full_name: str, limit: int = 10) -> List[Dict]:
        """Fetch open issues from the repository"""
        try:
            repo = self.github.get_repo(repo_full_name)
            issues = []
            
            for issue in repo.get_issues(state='open')[:limit]:
                # Skip pull requests (GitHub API includes PRs in issues)
                if issue.pull_request:
                    continue
                
                issues.append({
                    "number": issue.number,
                    "title": issue.title,
                    "body": issue.body or "",
                    "labels": [label.name for label in issue.labels],
                    "created_at": issue.created_at.isoformat(),
                    "updated_at": issue.updated_at.isoformat(),
                    "html_url": issue.html_url,
                    "user": issue.user.login if issue.user else "unknown",
                    "assignees": [assignee.login for assignee in issue.assignees],
                })
            
            return issues
        except GithubException as e:
            raise RuntimeError(f"Failed to fetch issues: {str(e)}")
    
    def get_issue_details(self, repo_full_name: str, issue_number: int) -> Dict:
        """Get detailed information about a specific issue"""
        try:
            repo = self.github.get_repo(repo_full_name)
            issue = repo.get_issue(issue_number)
            
            # Get comments
            comments = []
            for comment in issue.get_comments():
                comments.append({
                    "body": comment.body,
                    "user": comment.user.login if comment.user else "unknown",
                    "created_at": comment.created_at.isoformat(),
                })
            
            return {
                "number": issue.number,
                "title": issue.title,
                "body": issue.body or "",
                "labels": [label.name for label in issue.labels],
                "state": issue.state,
                "created_at": issue.created_at.isoformat(),
                "updated_at": issue.updated_at.isoformat(),
                "html_url": issue.html_url,
                "user": issue.user.login if issue.user else "unknown",
                "assignees": [assignee.login for assignee in issue.assignees],
                "comments": comments,
                "comments_count": issue.comments,
            }
        except GithubException as e:
            raise RuntimeError(f"Failed to fetch issue #{issue_number}: {str(e)}")
    
    def cleanup_repository(self, repo_full_name: str):
        """Remove temporary directory for a repository"""
        if repo_full_name in self.temp_dirs:
            temp_dir = self.temp_dirs[repo_full_name]
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)
            del self.temp_dirs[repo_full_name]
            print(f"[github_repo_manager] Cleaned up {repo_full_name}")
    
    def cleanup_all(self):
        """Clean up all temporary directories"""
        for repo_name in list(self.temp_dirs.keys()):
            self.cleanup_repository(repo_name)
    
    def __del__(self):
        """Cleanup on destruction"""
        self.cleanup_all()

# Global instance
repo_manager = GitHubRepoManager()
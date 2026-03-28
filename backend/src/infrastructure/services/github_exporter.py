import os
import json
import logging
import subprocess
from typing import List, Dict

logger = logging.getLogger(__name__)


class GithubExporterService:
    """Exports ML JSON predictions to a GitHub repository using GitOps."""
    def __init__(self):
        self.github_token = os.getenv("GITHUB_TOKEN")
        self.github_username = os.getenv("GITHUB_USERNAME", "Worker-Bot")
        self.github_email = os.getenv("GITHUB_EMAIL", "worker@bjj-betsports.local")
        # Format: username/repo
        self.github_repo = os.getenv("GITHUB_REPO")
        self.local_repo_path = "/tmp/github_data_export"
        
    def export_and_push(self, data: List[Dict], filename: str = "latest_predictions.json") -> bool:
        """Saves data to a JSON file and pushes it to GitHub."""
        if not self.github_token or not self.github_repo:
            logger.warning("⚠️ Github Export skipped: GITHUB_TOKEN or GITHUB_REPO not configured.")
            return False
            
        try:
            # 1. Ensure git is configured
            self._configure_git()
            
            # 2. Clone or pull repo
            self._sync_repo()
            
            # 3. Write latest data to file
            filepath = os.path.join(self.local_repo_path, filename)
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2, default=str)
                
            # 4. Commit and push
            return self._commit_and_push(filename)
            
        except Exception as e:
            logger.error(f"❌ Failed to push to GitHub: {e}")
            return False

    def _configure_git(self):
        """Sets global git config inside the container."""
        subprocess.run(["git", "config", "--global", "user.name", self.github_username], check=True, capture_output=True)
        subprocess.run(["git", "config", "--global", "user.email", self.github_email], check=True, capture_output=True)
        # Avoid prompt for credentials
        subprocess.run(["git", "config", "--global", "credential.helper", "store"], check=True, capture_output=True)

    def _sync_repo(self):
        """Clones the repo if it doesn't exist, else pulls latest changes."""
        repo_url = f"https://{self.github_token}@github.com/{self.github_repo}.git"
        
        if not os.path.exists(self.local_repo_path):
            logger.info(f"Cloning {self.github_repo} into {self.local_repo_path}...")
            subprocess.run(["git", "clone", repo_url, self.local_repo_path], check=True, capture_output=True)
        else:
            logger.info(f"Pulling latest from {self.github_repo}...")
            # Use 'git pull --rebase' to avoid ugly merge conflicts on auto-updates
            subprocess.run(["git", "-C", self.local_repo_path, "pull", "--rebase", "origin", "main"], check=False, capture_output=True)

    def _commit_and_push(self, filename: str) -> bool:
        """Commits the changed JSON and pushes it back up."""
        try:
            # Add changes
            subprocess.run(["git", "-C", self.local_repo_path, "add", filename], check=True, capture_output=True)
            
            # Check if there are actually changes
            status_res = subprocess.run(["git", "-C", self.local_repo_path, "status", "--porcelain"], capture_output=True, text=True)
            if not status_res.stdout.strip():
                logger.info("ℹ️ No new changes to push (JSON is identical).")
                return True
                
            # Commit
            commit_msg = f"Auto-update ml predictions on {filename}"
            subprocess.run(["git", "-C", self.local_repo_path, "commit", "-m", commit_msg], check=True, capture_output=True)
            
            # Push
            repo_url = f"https://{self.github_token}@github.com/{self.github_repo}.git"
            subprocess.run(["git", "-C", self.local_repo_path, "push", repo_url, "main"], check=True, capture_output=True)
            
            logger.info(f"✅ Successfully exported and pushed {filename} to {self.github_repo}")
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Git execution failed: {e.stderr.decode() if e.stderr else str(e)}")
            raise e

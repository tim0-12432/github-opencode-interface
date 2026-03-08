from .step import AbstractStep
import subprocess
import os

class GithubCloneRepoStep(AbstractStep):
    def __init__(self, repo: str, issue_number: int, branch: str = None):
        self.repo = repo
        self.issue_number = issue_number
        self.branch = branch
        super().__init__(name=f"Clone {repo} for issue #{issue_number}", retries=0)

    def run(self, env: dict):
        token = env.get("GITHUB_TOKEN")

        print(f"Setting up repository {self.repo}...")

        branch_name = self.branch or f"fix/issue-{self.issue_number}"
        workspace_path = "/workspace/repo"

        if os.path.exists(workspace_path):
            print("Removing existing repository directory...")
            try:
                subprocess.check_output(["rm", "-rf", workspace_path], stderr=subprocess.STDOUT)
            except subprocess.CalledProcessError as e:
                print(f"Failed to remove existing repository: {e.output}")
                raise

        try:
            subprocess.check_output([
                "git", "clone", "--depth", "100",
                f"https://x-access-token:{token}@github.com/{self.repo}.git",
                workspace_path
            ], text=True, stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as e:
            print(f"Failed to clone repository {self.repo}. Check your GITHUB_TOKEN and repository access: {e.output}")
            raise

        if not os.path.exists(f"{workspace_path}/.git"):
            raise NotADirectoryError(f"Repository cloned but no .git directory found in {workspace_path}.")

        default_branch = None
        try:
            default_branch = subprocess.check_output([
                "git",
                "symbolic-ref", "refs/remotes/origin/HEAD",
                "|", "sed", "'s@^refs/remotes/origin/@@'"
            ], text=True, stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as e:
            print(f"Getting default origin path failed: {e.output}")
            raise

        print(f"Checking for existing path: {branch_name}")
        try:
            subprocess.check_output([
                "git", "ls-remote",
                "--heads", "origin", branch_name,
                "2>/dev/null", "|",
                "grep", "-q", branch_name
            ], text=True, stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError:
            print(f"Creating new branch: {branch_name}")
            try:
                subprocess.check_output([
                    "git",
                    "checkout", "-b", branch_name
                ], text=True, stderr=subprocess.STDOUT)
            except subprocess.CalledProcessError as e:
                print(f"Failed creating new branch: {e.output}")
                raise
            print(f"Repository ready on branch: {branch_name}")
            return
        
        print(f"Continuing on existing branch: {branch_name}")
        try:
            subprocess.check_output([
                "git",
                "fetch", "origin",
                f"{branch_name}:{branch_name}"
            ], text=True, stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as e:
            print(f"Failed fetching origin: {e.output}")
            raise
        try:
            subprocess.check_output([
                "git",
                "checkout", branch_name
            ], text=True, stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as e:
            print(f"Failed checking out existing branch: {e.output}")
            raise

        commits_ahead = 0
        try:
            commits_ahead = subprocess.check_output([
                "git", "log", "--oneline",
                f"origin/{default_branch}..HEAD",
                "|", "wc", "-l"
            ], text=True, stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as e:
            print(f"Failed getting commit ahead count: {e.output}")

        print(f"Checked out existing branch with {commits_ahead} commit(s) ahead")
        print(f"Repository ready on branch: {branch_name}")

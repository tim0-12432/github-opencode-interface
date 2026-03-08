from .step import AbstractStep
import subprocess
import json

class GithubFetchIssueStep(AbstractStep):
    def __init__(self, repo: str, issue_number: int):
        self.repo = repo
        self.issue_number = issue_number
        super().__init__(name=f"Fetch issue #{issue_number} from {repo}", retries=0)

    def run(self, env: dict):
        print(f"Fetching issue #{self.issue_number} from {self.repo}...")
        issue_json = None
        try:
            issue_json = subprocess.check_output([
                "gh",
                "issue", "view", str(self.issue_number),
                "--repo", self.repo,
                "--json", "title,body,labels,comments"
            ], text=True, stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as e:
            print(f"Failed to fetch issue #{self.issue_number} from {self.repo}: {e.output}. Check your GITHUB_TOKEN, repo permissions, or issue number.")
            raise

        json_data = json.loads(issue_json)
        issue_title = json_data.get("title", "No title")
        issue_body = json_data.get("body", "No description provided.")
        issue_labels = ", ".join(label["name"] for label in json_data.get("labels", [])) or "None"
        issue_comments = "\n".join(comment["body"] for comment in json_data.get("comments", []))[:2000] or "No comments"

        issue_context = f"""
# Issue #{self.issue_number}: {issue_title}

## Labels
{issue_labels}

## Description
{issue_body}

## Comments
{issue_comments}
"""
        with open("/workspace/issue_context.md", "w") as f:
            f.write(issue_context)

        print(f"Issue fetched: {issue_title}")

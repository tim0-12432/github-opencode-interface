from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from github import Auth, Github, GithubException

from .exceptions import GitHubError


@dataclass
class IssueData:
    """Container for issue data returned by GitHubService."""

    title: str
    body: str
    labels: List[str]
    comments: List[str]


class GitHubService:
    """Provides GitHub API operations using PyGithub instead of gh CLI."""

    def __init__(self, token: str, repo_full_name: str) -> None:
        """Initialize the GitHub client and repository reference.

        Args:
            token: GitHub token used to authenticate API requests.
            repo_full_name: Full repository name in the form 'owner/name'.
        """
        try:
            auth = Auth.Token(token)
            self._client = Github(auth=auth)
            self._repo = self._client.get_repo(repo_full_name)
        except GithubException as exc:
            raise GitHubError(
                f'Failed to initialize GitHub client for {repo_full_name}: {exc}'
            ) from exc

    def get_issue(self, number: int) -> IssueData:
        """Fetch an issue and return its title, body, labels, and comments.

        Args:
            number: Issue number to retrieve.

        Returns:
            IssueData containing title, body, label names, and comment bodies.
        """
        try:
            issue = self._repo.get_issue(number=number)
            labels = [label.name for label in issue.labels]
            comments = [comment.body for comment in issue.get_comments()]
            body = issue.body or ''
            return IssueData(
                title=issue.title,
                body=body,
                labels=labels,
                comments=comments,
            )
        except GithubException as exc:
            raise GitHubError(f'Failed to fetch issue #{number}: {exc}') from exc

    def add_issue_comment(self, number: int, body: str) -> None:
        """Add a comment to an issue.

        Args:
            number: Issue number to comment on.
            body: Comment content.
        """
        try:
            issue = self._repo.get_issue(number=number)
            issue.create_comment(body=body)
        except GithubException as exc:
            raise GitHubError(
                f'Failed to add comment to issue #{number}: {exc}'
            ) from exc

    def create_issue(self, title: str, body: str, labels: List[str]) -> str:
        """Create an issue with a title, body, and labels.

        Args:
            title: Title of the issue.
            body: Body content for the issue.
            labels: List of label names to apply.

        Returns:
            URL of the created issue.
        """
        try:
            issue = self._repo.create_issue(title=title, body=body, labels=labels)
            return issue.html_url
        except GithubException as exc:
            raise GitHubError(f'Failed to create issue: {exc}') from exc

    def list_labels(self) -> List[str]:
        """List all label names for the repository.

        Returns:
            List of label names.
        """
        try:
            return [label.name for label in self._repo.get_labels()]
        except GithubException as exc:
            raise GitHubError('Failed to list labels.') from exc

    def ensure_label(self, name: str, color: str, description: str) -> None:
        """Ensure a label exists, creating it if it is missing.

        Args:
            name: Label name to ensure.
            color: Hex color for the label.
            description: Label description.
        """
        try:
            for label in self._repo.get_labels():
                if label.name == name:
                    return
            self._repo.create_label(name=name, color=color, description=description)
        except GithubException as exc:
            raise GitHubError(f'Failed to ensure label {name}: {exc}') from exc

    def find_pr_for_branch(self, branch: str) -> Optional[int]:
        """Find an open pull request for the specified branch.

        Args:
            branch: Branch name to search for.

        Returns:
            Pull request number if found, otherwise None.
        """
        try:
            owner = self._repo.owner.login
            head = f'{owner}:{branch}'
            pulls = self._repo.get_pulls(state='open', head=head)
            for pull in pulls:
                return pull.number
            return None
        except GithubException as exc:
            raise GitHubError(
                f'Failed to find pull request for branch {branch}: {exc}'
            ) from exc

    def create_pull_request(self, title: str, body: str, head: str, base: str) -> str:
        """Create a pull request from head to base.

        Args:
            title: Pull request title.
            body: Pull request body.
            head: Head branch name or owner:branch.
            base: Base branch name.

        Returns:
            URL of the created pull request.
        """
        try:
            pull_request = self._repo.create_pull(
                title=title,
                body=body,
                head=head,
                base=base,
            )
            return pull_request.html_url
        except GithubException as exc:
            raise GitHubError(f'Failed to create pull request: {exc}') from exc

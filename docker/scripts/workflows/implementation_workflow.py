from .workflow import AbstractWorkflow
from .steps import GithubLoginStep, GithubCloneRepoStep


class ImplementationWorkflow(AbstractWorkflow):
    def __init__(self, repo: str, issue_number: int, branch: str = None):
        steps = [
            GithubLoginStep(),
            GithubCloneRepoStep(repo, issue_number, branch)
        ]
        super().__init__("Implementation Workflow", steps)

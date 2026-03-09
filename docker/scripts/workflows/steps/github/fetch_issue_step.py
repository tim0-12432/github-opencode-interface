'''GitHub issue fetch step.'''

from __future__ import annotations

from pathlib import Path

from ..step import AbstractStep
from ....lib.context import WorkflowContext
from ....lib.exceptions import StepExecutionError


class GithubFetchIssueStep(AbstractStep):
    '''Fetch issue details and write issue context.'''

    def __init__(self) -> None:
        super().__init__(name='Fetch Issue', retries=0)

    def run(self, ctx: WorkflowContext) -> None:
        if ctx.github is None:
            raise StepExecutionError('GitHub service is not available on context.')
        if ctx.config.issue is None:
            raise StepExecutionError('Issue number is not configured.')

        ctx.logger.log(
            f'Fetching issue #{ctx.config.issue} from {ctx.config.repo}...',
        )
        try:
            issue = ctx.github.get_issue(ctx.config.issue)
        except Exception as exc:
            raise StepExecutionError(
                f'Failed to fetch issue #{ctx.config.issue}.',
            ) from exc

        ctx.issue_title = issue.title
        ctx.issue_body = issue.body or 'No description provided.'
        ctx.issue_labels = issue.labels
        ctx.issue_comments = issue.comments

        labels_text = ', '.join(issue.labels) or 'None'
        comments_text = '\n'.join(issue.comments)[:2000] or 'No comments'
        issue_context = (
            f'# Issue #{ctx.config.issue}: {issue.title}\n\n'
            f'## Labels\n{labels_text}\n\n'
            f'## Description\n{ctx.issue_body}\n\n'
            f'## Comments\n{comments_text}\n'
        )

        issue_path = ctx.config.issue_context_path
        try:
            Path(issue_path).write_text(issue_context, encoding='utf-8')
        except OSError as exc:
            raise StepExecutionError(
                f'Failed to write issue context to {issue_path}.',
            ) from exc

        if not Path(issue_path).exists() or Path(issue_path).stat().st_size == 0:
            raise StepExecutionError(
                f'Issue context file is empty: {issue_path}.',
            )

        ctx.logger.success(f'Issue fetched: {issue.title}')

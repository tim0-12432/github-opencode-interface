'''Create issue context step for suggest/review workflows.'''

from __future__ import annotations

from pathlib import Path

from ..step import AbstractStep
from ....lib.context import WorkflowContext
from ....lib.exceptions import StepExecutionError


class CreateIssueContextStep(AbstractStep):
    '''Write issue context file for suggest/review workflows.'''

    def __init__(self, mode: str) -> None:
        super().__init__(name='Create Issue Context', retries=0)
        self.mode = mode

    def run(self, ctx: WorkflowContext) -> None:
        if self.mode not in {'suggest', 'review'}:
            raise StepExecutionError('Invalid mode for issue context creation.')

        if self.mode == 'suggest':
            message = (
                '# Repository: {repo}\n\n'
                'No source issue was provided. Generate suggestions based on '
                'the current repository state.\n'
            )
        else:
            message = (
                '# Repository: {repo}\n\n'
                'No source issue was provided. Generate review report based '
                'on the current repository state.\n'
            )

        issue_path = Path(ctx.config.issue_context_path)
        try:
            issue_path.write_text(
                message.format(repo=ctx.config.repo),
                encoding='utf-8',
            )
        except OSError as exc:
            raise StepExecutionError(
                f'Failed to create issue context file: {issue_path}.',
            ) from exc

        if not issue_path.exists() or issue_path.stat().st_size == 0:
            raise StepExecutionError(
                f'Issue context file is empty: {issue_path}.',
            )

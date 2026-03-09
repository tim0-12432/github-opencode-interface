'''GitHub push step.'''

from __future__ import annotations

from ..step import AbstractStep
from ....lib.context import WorkflowContext
from ....lib.exceptions import StepExecutionError


class GithubPushStep(AbstractStep):
    '''Push working branch to origin.'''

    def __init__(self) -> None:
        super().__init__(name='Push Branch', retries=0)

    def run(self, ctx: WorkflowContext) -> None:
        if ctx.git_service is None:
            raise StepExecutionError('Git service is not available on context.')
        if not ctx.working_branch:
            raise StepExecutionError('Working branch is not set.')

        if ctx.config.dry_run:
            ctx.logger.log(f'[DRY RUN] Would push branch: {ctx.working_branch}')
            return

        ctx.logger.log('Pushing branch to remote...')
        try:
            ctx.git_service.push(ctx.working_branch)
        except Exception as exc:
            raise StepExecutionError('Failed to push branch to remote.') from exc

        ctx.logger.success(f'Branch pushed: {ctx.working_branch}')

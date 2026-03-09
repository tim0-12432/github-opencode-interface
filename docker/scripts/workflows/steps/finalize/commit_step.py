'''Commit step for workflow finalization.'''

from __future__ import annotations

from ..step import AbstractStep
from ....lib.context import WorkflowContext
from ....lib.exceptions import StepExecutionError


class CommitStep(AbstractStep):
    '''Commit repository changes with the provided message.'''

    def __init__(self, message: str, description: str = '') -> None:
        super().__init__(name='Commit Changes', retries=0)
        self.message = message
        self.description = description

    def run(self, ctx: WorkflowContext) -> None:
        if ctx.git_service is None:
            raise StepExecutionError('Git service is not available on context.')

        if ctx.config.dry_run:
            ctx.logger.log(f'[DRY RUN] Would commit: {self.message}')
            return

        ctx.logger.log('Committing changes...')
        try:
            committed = ctx.git_service.commit(self.message, self.description)
        except Exception as exc:
            raise StepExecutionError('Failed to commit changes.') from exc

        if not committed:
            ctx.logger.warn('No changes to commit')

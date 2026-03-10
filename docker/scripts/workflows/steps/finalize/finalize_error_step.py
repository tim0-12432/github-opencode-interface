'''Finalize error step.'''

from __future__ import annotations

from ..step import AbstractStep
from ....lib.context import WorkflowContext
from ....lib.exceptions import StepExecutionError
from ..github.push_step import GithubPushStep
from ..github.comment_step import GithubCommentStep
from .commit_step import CommitStep


class FinalizeErrorStep(AbstractStep):
    '''Finalize workflow with error status.'''

    def __init__(self, error_message: str) -> None:
        super().__init__(name='Finalize Error', retries=0)
        self.error_message = error_message

    def run(self, ctx: WorkflowContext) -> None:
        ctx.logger.phase('FINALIZING - ERROR')

        if ctx.config.issue is None:
            ctx.logger.warn('ISSUE not set; skipping error commit/push and issue comment')
            self._print_banner(ctx)
            return

        if ctx.git_service and ctx.git_service.work_dir.exists() and ctx.git_service.has_changes():
            try:
                CommitStep(
                    message=(
                        f'wip: attempted fix for issue #{ctx.config.issue} (error)'
                    ),
                    description=f'Error occurred: {self.error_message}',
                ).run(ctx)
            except StepExecutionError:
                ctx.logger.verbose('Failed to commit error state')
            try:
                GithubPushStep().run(ctx)
            except StepExecutionError:
                ctx.logger.verbose('Failed to push error state')

        try:
            GithubCommentStep('error', self.error_message).run(ctx)
        except StepExecutionError:
            ctx.logger.verbose('Failed to comment on issue about error')

        self._print_banner(ctx)

    def _print_banner(self, ctx: WorkflowContext) -> None:
        ctx.logger.banner('❌ ERROR')
        ctx.logger.log(f'  {self.error_message}')

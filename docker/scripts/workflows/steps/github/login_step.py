'''GitHub login step configuration.'''

from __future__ import annotations

from ..step import AbstractStep
from ....lib.context import WorkflowContext
from ....lib.exceptions import StepExecutionError


class GithubLoginStep(AbstractStep):
    '''Configure git identity using the git service.'''

    def __init__(self) -> None:
        super().__init__(name='GitHub Login', retries=0)

    def run(self, ctx: WorkflowContext) -> None:
        ctx.logger.log('Configuring git identity...')
        if ctx.git_service is None:
            raise StepExecutionError('Git service is not available on context.')
        try:
            ctx.git_service.configure_identity(
                ctx.config.git_author_name,
                ctx.config.git_author_email,
            )
        except Exception as exc:
            raise StepExecutionError('Failed to configure git identity.') from exc

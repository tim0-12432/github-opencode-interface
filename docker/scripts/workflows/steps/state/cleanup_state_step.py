'''Cleanup workflow state step.'''

from __future__ import annotations

from ..step import AbstractStep
from ....lib.context import WorkflowContext
from ....lib.exceptions import StepExecutionError


class CleanupStateStep(AbstractStep):
    '''Normalize state files by removing extensions.'''

    def __init__(self) -> None:
        super().__init__(name='Cleanup State', retries=0)

    def run(self, ctx: WorkflowContext) -> None:
        ctx.logger.log('Cleaning up state files...')
        try:
            ctx.state.cleanup()
        except Exception as exc:
            raise StepExecutionError('Failed to cleanup state files.') from exc

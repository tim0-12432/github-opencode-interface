'''OpenCode analyze step.'''

from __future__ import annotations

from ..step import AbstractStep
from ....lib.context import WorkflowContext
from ....lib.exceptions import StepExecutionError


class AnalyzeStep(AbstractStep):
    '''Run the analyze phase via OpenCode.'''

    def __init__(self) -> None:
        super().__init__(name='Analyze', retries=0)

    def run(self, ctx: WorkflowContext) -> None:
        if ctx.opencode_service is None:
            raise StepExecutionError('OpenCode service is not available on context.')

        ctx.logger.phase('ANALYSIS')
        success = ctx.opencode_service.run_phase('analyze', ctx)
        if not success:
            raise StepExecutionError('Analyze phase failed.')

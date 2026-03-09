'''OpenCode fix tests step.'''

from __future__ import annotations

from ..step import AbstractStep
from ....lib.context import WorkflowContext
from ....lib.exceptions import StepExecutionError


class FixTestsStep(AbstractStep):
    '''Run the fix-tests phase via OpenCode.'''

    def __init__(self) -> None:
        super().__init__(name='Fix Tests', retries=0)

    def run(self, ctx: WorkflowContext) -> None:
        if ctx.opencode_service is None:
            raise StepExecutionError('OpenCode service is not available on context.')

        success = ctx.opencode_service.run_phase('fix-tests', ctx)
        if not success:
            raise StepExecutionError('Fix-tests phase failed.')

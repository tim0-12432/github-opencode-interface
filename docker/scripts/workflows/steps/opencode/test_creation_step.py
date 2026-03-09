'''OpenCode test creation step.'''

from __future__ import annotations

from ..step import AbstractStep
from ....lib.context import WorkflowContext
from ....lib.exceptions import StepExecutionError


class TestCreationStep(AbstractStep):
    '''Run the test creation phase via OpenCode.'''

    def __init__(self) -> None:
        super().__init__(name='Test Creation', retries=0)

    def run(self, ctx: WorkflowContext) -> None:
        if ctx.opencode_service is None:
            raise StepExecutionError('OpenCode service is not available on context.')

        ctx.logger.phase('TESTING')
        success = ctx.opencode_service.run_phase('test', ctx)
        if not success:
            raise StepExecutionError('Test creation phase failed.')

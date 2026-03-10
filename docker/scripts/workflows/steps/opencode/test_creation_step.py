'''OpenCode test creation step.'''

from __future__ import annotations

from ....lib.config import ModelTier
from ....lib.context import WorkflowContext
from ....lib.exceptions import StepExecutionError
from .opencode_step import AbstractOpencodeStep


class TestCreationStep(AbstractOpencodeStep):
    '''Run the test creation phase via OpenCode.'''

    def __init__(self) -> None:
        super().__init__(name='Test Creation', phase='test', model_tier=ModelTier.STANDARD)

    def run(self, ctx: WorkflowContext) -> None:
        self._require_opencode(ctx)
        ctx.logger.phase('TESTING')
        success = self._run_opencode_phase(ctx)
        if not success:
            raise StepExecutionError('Test creation phase failed.')

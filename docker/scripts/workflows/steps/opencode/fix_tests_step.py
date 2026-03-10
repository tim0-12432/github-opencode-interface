'''OpenCode fix tests step.'''

from __future__ import annotations

from ....lib.config import ModelTier
from ....lib.context import WorkflowContext
from ....lib.exceptions import StepExecutionError
from .opencode_step import AbstractOpencodeStep


class FixTestsStep(AbstractOpencodeStep):
    '''Run the fix-tests phase via OpenCode.'''

    def __init__(self) -> None:
        super().__init__(name='Fix Tests', phase='fix-tests', model_tier=ModelTier.STANDARD)

    def run(self, ctx: WorkflowContext) -> None:
        self._require_opencode(ctx)
        success = self._run_opencode_phase(ctx)
        if not success:
            raise StepExecutionError('Fix-tests phase failed.')

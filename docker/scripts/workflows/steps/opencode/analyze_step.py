'''OpenCode analyze step.'''

from __future__ import annotations
import os

from ....lib.config import ModelTier
from ....lib.context import WorkflowContext
from ....lib.exceptions import StepExecutionError
from .opencode_step import AbstractOpencodeStep


class AnalyzeStep(AbstractOpencodeStep):
    '''Run the analyze phase via OpenCode.'''

    def __init__(self) -> None:
        super().__init__(name='Analyze', phase='analyze', model_tier=ModelTier.SMALL, expected_artifacts=['/workspace/plan.md'])

    def run(self, ctx: WorkflowContext) -> None:
        self._require_opencode(ctx)
        ctx.logger.phase('ANALYSIS')
        success = self._run_opencode_phase(ctx)
        if not success:
            raise StepExecutionError('Analyze phase failed.')

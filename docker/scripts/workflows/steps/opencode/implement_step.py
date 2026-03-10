'''OpenCode implement step.'''

from __future__ import annotations

from ....lib.config import ModelTier
from ....lib.context import WorkflowContext
from ....lib.exceptions import StepExecutionError
from .opencode_step import AbstractOpencodeStep


class ImplementStep(AbstractOpencodeStep):
    '''Run the implement phase via OpenCode.'''

    def __init__(self, review_cycle: int = 1) -> None:
        super().__init__(name='Implement', phase='implement', model_tier=ModelTier.LARGE)
        self.review_cycle = review_cycle

    def run(self, ctx: WorkflowContext) -> None:
        self._require_opencode(ctx)
        ctx.logger.phase(
            f'IMPLEMENTATION (Review Cycle {self.review_cycle}/{ctx.config.max_review_cycles})',
        )
        extra_context = ''
        if self.review_cycle > 1:
            feedback = ctx.state.get_review_feedback()
            if feedback:
                extra_context = f'Previous review feedback:\n{feedback}'

        success = self._run_opencode_phase(ctx, extra_context=extra_context)
        if not success:
            raise StepExecutionError('Implement phase failed.')

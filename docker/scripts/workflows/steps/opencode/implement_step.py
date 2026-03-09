'''OpenCode implement step.'''

from __future__ import annotations

from ..step import AbstractStep
from ....lib.context import WorkflowContext
from ....lib.exceptions import StepExecutionError


class ImplementStep(AbstractStep):
    '''Run the implement phase via OpenCode.'''

    def __init__(self, review_cycle: int = 1) -> None:
        super().__init__(name='Implement', retries=0)
        self.review_cycle = review_cycle

    def run(self, ctx: WorkflowContext) -> None:
        if ctx.opencode_service is None:
            raise StepExecutionError('OpenCode service is not available on context.')

        ctx.logger.phase(
            f'IMPLEMENTATION (Review Cycle {self.review_cycle}/{ctx.config.max_review_cycles})',
        )
        extra_context = ''
        if self.review_cycle > 1:
            feedback = ctx.state.get_review_feedback()
            if feedback:
                extra_context = f'Previous review feedback:\n{feedback}'

        success = ctx.opencode_service.run_phase(
            'implement',
            ctx,
            extra_context=extra_context,
        )
        if not success:
            raise StepExecutionError('Implement phase failed.')

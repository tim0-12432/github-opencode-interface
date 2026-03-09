'''Composite review cycle step.'''

from __future__ import annotations

from ..step import AbstractStep
from ....lib.context import WorkflowContext
from ....lib.exceptions import StepExecutionError
from ..opencode.review_step import ReviewStep
from ..opencode.implement_step import ImplementStep
from .test_cycle_step import TestCycleStep


class ReviewCycleStep(AbstractStep):
    '''Run review with re-implementation and re-testing cycles.'''

    def __init__(self) -> None:
        super().__init__(name='Review Cycle', retries=0)

    def run(self, ctx: WorkflowContext) -> None:
        for attempt in range(1, ctx.config.max_review_cycles + 1):
            ctx.logger.phase(
                f'REVIEW (Attempt {attempt}/{ctx.config.max_review_cycles})',
            )
            try:
                ReviewStep().run(ctx)
                return
            except StepExecutionError:
                if attempt == ctx.config.max_review_cycles:
                    ctx.logger.error(
                        'Review still failing after '
                        f'{ctx.config.max_review_cycles} implementation cycles',
                    )
                    raise

                ctx.logger.warn('Review found issues, going back to implementation...')
                ImplementStep(review_cycle=attempt + 1).run(ctx)
                try:
                    TestCycleStep().run(ctx)
                except StepExecutionError:
                    ctx.logger.warn('Tests not passing after re-implementation')

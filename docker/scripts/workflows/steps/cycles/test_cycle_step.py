'''Composite test cycle step.'''

from __future__ import annotations

from ..step import AbstractStep
from ....lib.context import WorkflowContext
from ....lib.exceptions import StepExecutionError
from ..opencode.test_creation_step import TestCreationStep
from ..opencode.fix_tests_step import FixTestsStep
from ..testing.run_tests_step import RunTestsStep


class TestCycleStep(AbstractStep):
    '''Run test creation then fix-test loop up to max cycles.'''

    def __init__(self) -> None:
        super().__init__(name='Test Cycle', retries=0)

    def run(self, ctx: WorkflowContext) -> None:
        ctx.logger.phase('TESTING')

        try:
            TestCreationStep().run(ctx)
        except StepExecutionError:
            ctx.logger.warn('Test creation phase had issues, continuing anyway...')

        for attempt in range(1, ctx.config.max_test_cycles + 1):
            ctx.logger.log(
                f'Test cycle {attempt}/{ctx.config.max_test_cycles}',
            )
            try:
                RunTestsStep().run(ctx)
                ctx.logger.success('All tests passing')
                return
            except StepExecutionError:
                if attempt == ctx.config.max_test_cycles:
                    ctx.logger.error(
                        f'Tests still failing after {ctx.config.max_test_cycles} fix attempts',
                    )
                    raise

                ctx.logger.warn(
                    f'Tests failed, attempting fix ({attempt}/{ctx.config.max_test_cycles})...',
                )
                try:
                    FixTestsStep().run(ctx)
                except StepExecutionError:
                    ctx.logger.warn(
                        'Fix-tests phase had issues, will retry tests anyway...',
                    )

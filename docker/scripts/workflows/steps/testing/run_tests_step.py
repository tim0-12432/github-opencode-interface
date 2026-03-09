'''Testing step for running tests.'''

from __future__ import annotations

from ..step import AbstractStep
from ....lib.context import WorkflowContext
from ....lib.exceptions import StepExecutionError


class RunTestsStep(AbstractStep):
    '''Run detected tests and store output in state.'''

    def __init__(self) -> None:
        super().__init__(name='Run Tests', retries=0)

    def run(self, ctx: WorkflowContext) -> None:
        if ctx.testing_service is None:
            raise StepExecutionError('Testing service is not available on context.')

        ctx.logger.log('Running tests...')
        try:
            success, output = ctx.testing_service.run_tests()
        except Exception as exc:
            raise StepExecutionError('Failed to execute tests.') from exc

        ctx.state.save_test_output(output)
        if success:
            ctx.tests_passed = True
            ctx.logger.success('Tests passed')
            return

        ctx.tests_passed = False
        ctx.logger.error('Tests failed')
        ctx.logger.verbose(f'Test output:\n{output}')
        raise StepExecutionError('Tests failed.')

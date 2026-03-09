'''OpenCode report steps for review workflow.'''

from __future__ import annotations

from ..step import AbstractStep
from ....lib.context import WorkflowContext
from ....lib.exceptions import StepExecutionError


class ReportPhaseStep(AbstractStep):
    '''Run a single report phase via OpenCode.'''

    def __init__(self, phase: str, label: str | None = None) -> None:
        name = label or f'Report: {phase}'
        super().__init__(name=name, retries=0)
        self.phase = phase

    def run(self, ctx: WorkflowContext) -> None:
        if ctx.opencode_service is None:
            raise StepExecutionError('OpenCode service is not available on context.')

        ctx.logger.log(f'Running report phase: {self.phase}...')
        success = ctx.opencode_service.run_phase(self.phase, ctx)
        if not success:
            raise StepExecutionError(f'Report phase failed: {self.phase}.')


class ReportAggregationStep(AbstractStep):
    '''Aggregate report outputs into a single summary.'''

    def __init__(self) -> None:
        super().__init__(name='Aggregate Reports', retries=0)

    def run(self, ctx: WorkflowContext) -> None:
        if ctx.opencode_service is None:
            raise StepExecutionError('OpenCode service is not available on context.')

        ctx.logger.phase('AGGREGATING REPORT')
        review_contents = (
            'SECURITY REPORT:\n'
            f'{ctx.state.get_review_report("security")}\n\n'
            'ARCHITECTURE REPORT:\n'
            f'{ctx.state.get_review_report("architecture")}\n\n'
            'CUSTOMER REPORT:\n'
            f'{ctx.state.get_review_report("customer")}\n\n'
            'ENGINEERING REPORT:\n'
            f'{ctx.state.get_review_report("engineering")}\n\n'
            'TESTING REPORT:\n'
            f'{ctx.state.get_review_report("testing")}\n\n'
            'RESOURCE REPORT:\n'
            f'{ctx.state.get_review_report("resource")}\n'
        )

        success = ctx.opencode_service.run_phase(
            'report-aggregation',
            ctx,
            extra_context=review_contents,
        )
        if not success:
            raise StepExecutionError('Aggregation phase failed.')

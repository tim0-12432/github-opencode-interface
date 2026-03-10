'''OpenCode report steps for review workflow.'''

from __future__ import annotations

from ....lib.config import ModelTier
from ....lib.context import WorkflowContext
from ....lib.exceptions import StepExecutionError
from .opencode_step import AbstractOpencodeStep


class ReportPhaseStep(AbstractOpencodeStep):
    '''Run a single report phase via OpenCode.'''

    def __init__(self, phase: str, label: str | None = None) -> None:
        name = label or f'Report: {phase}'
        super().__init__(name=name, phase=phase, model_tier=ModelTier.SMALL)

    def run(self, ctx: WorkflowContext) -> None:
        self._require_opencode(ctx)
        ctx.logger.log(f'Running report phase: {self.phase}...')
        success = self._run_opencode_phase(ctx)
        if not success:
            raise StepExecutionError(f'Report phase failed: {self.phase}.')


class ReportAggregationStep(AbstractOpencodeStep):
    '''Aggregate report outputs into a single summary.'''

    def __init__(self) -> None:
        super().__init__(name='Aggregate Reports', phase='report-aggregation', model_tier=ModelTier.LARGE)

    def run(self, ctx: WorkflowContext) -> None:
        self._require_opencode(ctx)
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

        success = self._run_opencode_phase(ctx, extra_context=review_contents)
        if not success:
            raise StepExecutionError('Aggregation phase failed.')

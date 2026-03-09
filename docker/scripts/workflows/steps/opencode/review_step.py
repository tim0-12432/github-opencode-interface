'''OpenCode review step.'''

from __future__ import annotations

from ..step import AbstractStep
from ....lib.context import WorkflowContext
from ....lib.exceptions import StepExecutionError


class ReviewStep(AbstractStep):
    '''Run the review phase via OpenCode.'''

    def __init__(self) -> None:
        super().__init__(name='Review', retries=0)

    def run(self, ctx: WorkflowContext) -> None:
        if ctx.opencode_service is None:
            raise StepExecutionError('OpenCode service is not available on context.')

        ctx.logger.log('Running review...')
        try:
            review_passed_path = ctx.config.state_dir / 'review_passed'
            review_feedback_path = ctx.config.state_dir / 'review_feedback'
            if review_passed_path.exists():
                review_passed_path.unlink()
            if review_feedback_path.exists():
                review_feedback_path.unlink()
        except OSError as exc:
            raise StepExecutionError('Failed to reset review state files.') from exc

        success = ctx.opencode_service.run_phase('review', ctx)
        if not success:
            ctx.review_passed = False
            raise StepExecutionError('Review phase failed.')

        if review_passed_path.exists():
            ctx.review_passed = True
            ctx.logger.success('Review passed')
            return

        if review_feedback_path.exists():
            feedback = ctx.state.load('review_feedback', '')
            if not feedback:
                feedback = review_feedback_path.read_text(encoding='utf-8')
            ctx.state.save_review_feedback(feedback)
            ctx.review_passed = False
            ctx.logger.warn('Review found issues')
            raise StepExecutionError('Review found issues.')

        ctx.review_passed = True
        ctx.logger.success('Review completed (no issues flagged)')

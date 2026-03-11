'''Resolve workflow implementation.'''

from __future__ import annotations

from ..lib.context import WorkflowContext
from ..lib.exceptions import StepExecutionError
from .workflow import AbstractWorkflow
from .steps import (
    AnalyzeStep,
    FinalizeErrorStep,
    FinalizePartialStep,
    FinalizeSuccessStep,
    GithubCloneRepoStep,
    GithubFetchIssueStep,
    GithubLoginStep,
    ImplementStep,
    InstallDependenciesStep,
    ReviewCycleStep,
    TestCycleStep,
)
from .steps.step import AbstractStep


class ResolveWorkflow(AbstractWorkflow):
    '''Workflow to resolve a GitHub issue end-to-end.'''

    def __init__(self) -> None:
        super().__init__('Resolve Workflow')

    def build_steps(self, ctx: WorkflowContext) -> list[AbstractStep]:
        return [
            GithubLoginStep(),
            GithubFetchIssueStep(),
            GithubCloneRepoStep(),
            InstallDependenciesStep(),
            AnalyzeStep(),
            ImplementStep(review_cycle=1),
            TestCycleStep(),
            ReviewCycleStep(),
            FinalizeSuccessStep(),
        ]

    def run(self, ctx: WorkflowContext) -> bool:
        ctx.logger.banner(f'Workflow: {self.name}')

        for step in self.build_steps(ctx):
            try:
                step.execute(ctx)
            except StepExecutionError as error:
                self._handle_partial(ctx, step, error)
                return False
            except Exception as error:
                FinalizeErrorStep(str(error)).run(ctx)
                return False

        return True

    def _handle_partial(
        self,
        ctx: WorkflowContext,
        step: AbstractStep,
        error: StepExecutionError,
    ) -> None:
        if isinstance(step, TestCycleStep):
            reason = self._format_test_failure(ctx)
        elif isinstance(step, ReviewCycleStep):
            reason = self._format_review_failure(ctx)
        else:
            reason = str(error) or 'Workflow stopped with partial completion.'
        FinalizePartialStep(reason).run(ctx)

    def _format_test_failure(self, ctx: WorkflowContext) -> str:
        output = self._trim_lines(ctx.state.get_test_output(), limit=50)
        return (
            'Tests could not be fixed after '
            f'{ctx.config.max_test_cycles} attempts.\n\n'
            'Last test output:\n'
            f'```\n{output}\n```'
        )

    def _format_review_failure(self, ctx: WorkflowContext) -> str:
        feedback = ctx.state.get_review_feedback()
        return (
            'Review cycle could not be completed after '
            f'{ctx.config.max_review_cycles} attempts.\n\n'
            'Last review feedback:\n'
            f'{feedback}'
        )

    @staticmethod
    def _trim_lines(text: str, limit: int) -> str:
        lines = text.splitlines()
        trimmed = lines[:limit] if limit > 0 else lines
        return '\n'.join(trimmed)

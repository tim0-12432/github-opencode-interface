'''Suggest workflow implementation.'''

from __future__ import annotations

from ..lib.context import WorkflowContext
from ..lib.exceptions import StepExecutionError
from .workflow import AbstractWorkflow
from .steps import (
    CreateIssueContextStep,
    GithubCloneRepoStep,
    GithubFetchIssueStep,
    GithubLoginStep,
    SuggestStep,
)
from .steps.step import AbstractStep


class SuggestWorkflow(AbstractWorkflow):
    '''Workflow to suggest follow-up issues.'''

    def __init__(self) -> None:
        super().__init__('Suggest Workflow')

    def build_steps(self, ctx: WorkflowContext) -> list[AbstractStep]:
        steps: list[AbstractStep] = [GithubLoginStep()]

        if ctx.config.issue is not None:
            steps.append(GithubFetchIssueStep())
        else:
            steps.append(CreateIssueContextStep('suggest'))

        steps.append(GithubCloneRepoStep(depth=50, create_branch=False))
        steps.append(SuggestStep())
        return steps

    def run(self, ctx: WorkflowContext) -> bool:
        ctx.logger.banner(f'Workflow: {self.name}')

        for step in self.build_steps(ctx):
            try:
                step.execute(ctx)
            except StepExecutionError as error:
                ctx.logger.error(f'Suggest workflow failed: {error}')
                return False
            except Exception as error:
                ctx.logger.error(f'Suggest workflow failed: {error}')
                return False

        self._print_report(ctx)
        return True

    def _print_report(self, ctx: WorkflowContext) -> None:
        ctx.logger.banner('💡 SUGGESTIONS COMPLETE')
        ctx.logger.log(f'  Repository: {ctx.config.repo}')
        if ctx.config.issue is not None:
            ctx.logger.log(f'  Source:     #{ctx.config.issue}')
        else:
            ctx.logger.log('  Source:     None')
        if ctx.suggested_issue_urls:
            ctx.logger.log('  Suggestions:')
            for url in ctx.suggested_issue_urls:
                ctx.logger.log(f'   - {url}')
        else:
            ctx.logger.log('  Suggestions: None')

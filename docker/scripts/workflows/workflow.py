from __future__ import annotations

from abc import ABC, abstractmethod

from ..lib.context import WorkflowContext
from .steps.step import AbstractStep, StepStatus


class AbstractWorkflow(ABC):
    '''Base class for workflow orchestration.'''

    def __init__(self, name: str, steps: list[AbstractStep] | None = None) -> None:
        '''Initialize the workflow.

        Args:
            name: Human-readable name of the workflow.
            steps: Optional pre-built steps for backwards compatibility.
        '''
        self.name = name
        self.steps = steps or []

    @abstractmethod
    def build_steps(self, ctx: WorkflowContext) -> list[AbstractStep]:
        '''Construct the steps for this workflow.

        Args:
            ctx: Workflow execution context.

        Returns:
            Ordered list of steps to execute.
        '''
        return self.steps

    def run(self, ctx: WorkflowContext) -> bool:
        '''Run the workflow steps.

        Args:
            ctx: Workflow execution context.
        '''
        ctx.logger.banner(f'Workflow: {self.name}')
        steps = self.build_steps(ctx)
        for step in steps:
            if step.should_skip(ctx):
                step.status = StepStatus.SKIPPED
                ctx.logger.warn(f"Skipping step '{step.name}'.")
                continue
            try:
                step.execute(ctx)
            except Exception as error:
                self.on_error(ctx, error)
                raise

        return True

    def on_error(self, ctx: WorkflowContext, error: Exception) -> None:
        '''Hook invoked when a step raises an error.

        Args:
            ctx: Workflow execution context.
            error: The exception raised by a step.
        '''
        ctx.logger.error(f'Workflow failed: {error}')

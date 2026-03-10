'''Abstract base class for OpenCode workflow steps.'''

from __future__ import annotations

from abc import ABC

from ..step import AbstractStep
from ....lib.config import ModelTier
from ....lib.context import WorkflowContext
from ....lib.exceptions import StepExecutionError


class AbstractOpencodeStep(AbstractStep, ABC):
    '''Base class for steps that invoke OpenCode.

    Subclasses declare a phase name and a model_tier. Simple steps get a
    working run() implementation for free. Complex steps override run() and
    call _run_opencode_phase() for the actual OpenCode invocations.
    '''

    def __init__(
        self,
        name: str,
        phase: str,
        model_tier: ModelTier = ModelTier.STANDARD,
        retries: int = 0,
        retry_delay: float = 2.0,
    ) -> None:
        super().__init__(name=name, retries=retries, retry_delay=retry_delay)
        self.phase = phase
        self.model_tier = model_tier

    def _require_opencode(self, ctx: WorkflowContext) -> None:
        '''Raise StepExecutionError if the OpenCode service is unavailable.'''
        if ctx.opencode_service is None:
            raise StepExecutionError('OpenCode service is not available on context.')

    def _resolve_model(self, ctx: WorkflowContext) -> str:
        '''Resolve the step's model tier to a concrete model string.'''
        return ctx.config.resolve_model(self.model_tier)

    def _run_opencode_phase(
        self,
        ctx: WorkflowContext,
        phase: str | None = None,
        extra_context: str = '',
        max_attempts: int | None = None,
    ) -> bool:
        '''Run an OpenCode phase using the step's declared model tier.

        Resolves the model tier, guards on service availability, and delegates
        to OpenCodeService.run_phase().

        Args:
            ctx: Workflow context.
            phase: Phase name override. Defaults to self.phase.
            extra_context: Optional additional context for the prompt.
            max_attempts: Override for maximum retry attempts.

        Returns:
            True if the phase completed successfully, otherwise False.
        '''
        self._require_opencode(ctx)
        model = self._resolve_model(ctx)
        return ctx.opencode_service.run_phase(  # type: ignore[union-attr]
            phase or self.phase,
            ctx,
            model=model,
            extra_context=extra_context,
            max_attempts=max_attempts,
        )

    def run(self, ctx: WorkflowContext) -> None:
        '''Default run implementation for simple OpenCode steps.

        Logs the phase banner, runs the OpenCode phase, and raises
        StepExecutionError on failure. Override in subclasses that need
        custom pre/post logic.
        '''
        self._require_opencode(ctx)
        ctx.logger.phase(self.name.upper())
        success = self._run_opencode_phase(ctx)
        if not success:
            raise StepExecutionError(f'{self.name} phase failed.')

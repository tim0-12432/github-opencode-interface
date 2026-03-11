from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from pathlib import Path
import time

from ...lib.context import WorkflowContext
from ...lib.exceptions import MissingArtifactError, StepRetryExhaustedError


class StepStatus(Enum):
    """Lifecycle status for a workflow step."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


class AbstractStep(ABC):
    """Base class for workflow steps with retry support.

    Args:
        name: Human-readable name of the step.
        retries: Number of retries before giving up.
        retry_delay: Delay in seconds between retries.
        expected_artifacts: Paths to files that must exist after run().
    """

    def __init__(
        self,
        name: str,
        retries: int = 0,
        retry_delay: float = 2.0,
        expected_artifacts: list[str | Path] | None = None,
    ) -> None:
        self.name = name
        self.retries = retries
        self.retry_delay = retry_delay
        self.expected_artifacts: list[Path] = [
            Path(a) for a in (expected_artifacts or [])
        ]
        self.status = StepStatus.PENDING

    def execute(self, ctx: WorkflowContext) -> None:
        """Execute the step with retries.

        Args:
            ctx: Workflow execution context.

        Raises:
            StepRetryExhaustedError: When all retries are exhausted.
        """
        if self.should_skip(ctx):
            self.status = StepStatus.SKIPPED
            ctx.logger.warn(f"Skipping step '{self.name}'.")
            return

        ctx.logger.log(f"Executing step: {self.name} with {self.retries} retries")
        attempt = 0
        self.status = StepStatus.RUNNING
        while attempt <= self.retries:
            try:
                self.run(ctx)
                self._check_artifacts()
                self.status = StepStatus.SUCCESS
                ctx.logger.success(f"Step '{self.name}' completed successfully.")
                return
            except Exception as error:
                attempt += 1
                if attempt > self.retries:
                    self.status = StepStatus.FAILED
                    ctx.logger.error(
                        f"Step '{self.name}' failed after {self.retries} retries.",
                    )
                    raise StepRetryExhaustedError(
                        f"Step '{self.name}' failed after {self.retries} retries.",
                    ) from error
                ctx.logger.warn(
                    f"Error executing step '{self.name}': {error}. "
                    f"Retrying ({attempt}/{self.retries})...",
                )
                if self.retry_delay > 0:
                    time.sleep(self.retry_delay)

    def _check_artifacts(self) -> None:
        """Check that all expected artifacts exist after step execution."""
        if not self.expected_artifacts:
            return

        missing = [path for path in self.expected_artifacts if not path.exists()]
        if missing:
            raise MissingArtifactError(
                f"Step '{self.name}' failed to produce expected artifacts: {[str(p) for p in missing]}",
            )

    def should_skip(self, ctx: WorkflowContext) -> bool:
        """Determine whether the step should be skipped.

        Args:
            ctx: Workflow execution context.

        Returns:
            True when the step should be skipped; otherwise False.
        """
        return False

    @abstractmethod
    def run(self, ctx: WorkflowContext) -> None:
        """Run the step logic.

        Args:
            ctx: Workflow execution context.
        """
        raise NotImplementedError("Subclasses must implement the run method.")

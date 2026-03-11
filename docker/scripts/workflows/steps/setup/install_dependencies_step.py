"""Install dependencies step."""

from __future__ import annotations

from ....lib.context import WorkflowContext
from ....lib.dependency_service import DependencyService, InstallResult
from ..step import AbstractStep


def _format_summary(results: list[InstallResult]) -> str:
    lines: list[str] = []
    for result in results:
        if result.skipped:
            status = "SKIPPED"
        elif result.success:
            status = "OK"
        else:
            status = "FAILED"
        lines.append(
            f"{result.ecosystem}: {result.command} [{status}] ({result.duration_seconds:.1f}s)",
        )
    return "\n".join(lines)


class InstallDependenciesStep(AbstractStep):
    """Detect and install project dependencies after repo clone."""

    def __init__(self) -> None:
        super().__init__(name="Install Dependencies", retries=0)

    def run(self, ctx: WorkflowContext) -> None:
        ctx.logger.log("Detecting project dependencies...")

        service = DependencyService(work_dir=ctx.config.work_dir)
        ecosystems = service.detect_ecosystems()

        if not ecosystems:
            ctx.logger.log("No recognized dependency ecosystems detected. Skipping.")
            ctx.state.save("dependency_install_summary", "")
            return

        ctx.logger.log("Detected ecosystems: " + ", ".join(ecosystems))

        results = service.install_all()

        for result in results:
            if result.skipped:
                ctx.logger.warn(f"[{result.ecosystem}] skipped ({result.output})")
            elif result.success:
                ctx.logger.success(
                    f"[{result.ecosystem}] {result.command} ({result.duration_seconds:.1f}s)",
                )
            else:
                ctx.logger.warn(
                    f"[{result.ecosystem}] {result.command} failed ({result.duration_seconds:.1f}s)",
                )
                ctx.logger.verbose(f"Output:\n{result.output}")

        succeeded = [r for r in results if r.success and not r.skipped]
        failed = [r for r in results if not r.success]

        if failed and not succeeded:
            ctx.logger.warn(
                "All dependency installations failed. "
                "Continuing anyway — tests may fail later.",
            )

        ctx.state.save("dependency_install_summary", _format_summary(results))

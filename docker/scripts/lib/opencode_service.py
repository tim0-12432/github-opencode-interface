'''Service for running opencode prompts.'''

from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

from .context import WorkflowContext
from .prompt_service import PromptService


@dataclass
class OpenCodeService:
    '''Run opencode prompts for workflow phases.'''

    model: str
    work_dir: Path
    binary_path: str = '/root/.opencode/bin/opencode'

    def run_prompt(self, prompt_content: str, timeout: int | None = None) -> str:
        '''Execute the opencode binary with prompt content via stdin.

        Args:
            prompt_content: Prompt content to send to opencode.
            timeout: Optional timeout in seconds.

        Returns:
            Standard output from the opencode run.
        '''
        result = subprocess.run(
            [self.binary_path, 'run', '--model', self.model],
            input=prompt_content,
            capture_output=True,
            text=True,
            cwd=str(self.work_dir),
            timeout=timeout,
        )
        if result.returncode != 0:
            raise subprocess.CalledProcessError(
                result.returncode,
                result.args,
                output=result.stdout,
                stderr=result.stderr,
            )
        return result.stdout

    def run_phase(
        self,
        phase: str,
        ctx: WorkflowContext,
        extra_context: str = '',
        max_attempts: int | None = None,
    ) -> bool:
        '''Run an opencode phase with retries and rendered context.

        Args:
            phase: Phase name to run.
            ctx: Workflow context for rendering.
            extra_context: Optional additional context to include.
            max_attempts: Override for maximum attempts.

        Returns:
            True if the phase completed successfully, otherwise False.
        '''
        prompt_service = PromptService(ctx.config.prompts_dir)
        try:
            template = prompt_service.load(phase)
        except FileNotFoundError:
            ctx.logger.warn(f'Prompt for phase "{phase}" not found. Skipping.')
            return True

        prompt = prompt_service.render(template, ctx, extra_context=extra_context)
        try:
            Path('/workspace/.current_prompt.md').write_text(prompt, encoding='utf-8')
        except OSError:
            pass

        if ctx.config.dry_run:
            ctx.logger.log(f'[DRY RUN] Would run opencode phase: {phase}')
            ctx.logger.verbose(f'[DRY RUN] Prompt content:\n{prompt[:500]}...')
            return True
        attempts = max_attempts if max_attempts is not None else ctx.config.max_phase_attempts

        for attempt in range(1, attempts + 1):
            try:
                self.run_prompt(prompt)
                return True
            except subprocess.SubprocessError as exc:
                ctx.logger.warn(
                    f'Phase "{phase}" attempt {attempt} failed: {exc}'
                )
                if attempt < attempts:
                    time.sleep(2)

        return False

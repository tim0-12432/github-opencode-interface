'''Prompt loading and rendering utilities.'''

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .context import WorkflowContext


@dataclass
class PromptService:
    '''Load prompt templates and render workflow context values.'''

    prompts_dir: Path

    def load(self, phase_name: str) -> str:
        '''Load a prompt template by phase name.

        Args:
            phase_name: Phase name used to locate the .prompt file.

        Returns:
            Prompt template content.

        Raises:
            FileNotFoundError: If the prompt file does not exist.
        '''
        prompt_path = self.prompts_dir / f'{phase_name}.prompt'
        try:
            return prompt_path.read_text(encoding='utf-8')
        except FileNotFoundError as exc:
            raise FileNotFoundError(
                f'Prompt template not found: {prompt_path}'
            ) from exc

    def render(
        self,
        template: str,
        ctx: WorkflowContext,
        extra_context: str = '',
        issue_context_path: Path | None = None,
        suggestions_count: int | None = None,
    ) -> str:
        '''Render a prompt template with workflow context values.

        Args:
            template: Prompt template text to render.
            ctx: Workflow context containing config and state data.
            extra_context: Optional additional context to append.

        Returns:
            Rendered prompt text.
        '''
        context_path = issue_context_path or ctx.config.issue_context_path
        suggested_count_value = (
            suggestions_count
            if suggestions_count is not None
            else ctx.config.suggested_issues_count
        )
        replacements = {
            '{{ISSUE_CONTEXT}}': self._load_issue_context(context_path),
            '{{ISSUE_NUMBER}}': str(ctx.config.issue) if ctx.config.issue else 'N/A',
            '{{REPO}}': ctx.config.repo,
            '{{TEST_OUTPUT}}': ctx.state.get_test_output(),
            '{{REVIEW_FEEDBACK}}': ctx.state.get_review_feedback(),
            '{{SUGGESTED_COUNT}}': str(suggested_count_value),
        }

        rendered = template
        for key, value in replacements.items():
            rendered = rendered.replace(key, value)

        if extra_context:
            rendered = f'{rendered}\n\n## Additional Context\n{extra_context}'

        return rendered

    def exists(self, phase_name: str) -> bool:
        '''Return whether a prompt template exists for the phase.

        Args:
            phase_name: Phase name used to locate the .prompt file.

        Returns:
            True if the prompt file exists, otherwise False.
        '''
        return (self.prompts_dir / f'{phase_name}.prompt').exists()

    def _load_issue_context(self, path: Path) -> str:
        '''Load issue context from the default workspace path.

        Returns:
            Issue context text or an empty string when missing.
        '''
        if not path.exists():
            return ''
        try:
            return path.read_text(encoding='utf-8')
        except OSError:
            return ''

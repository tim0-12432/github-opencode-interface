'''OpenCode suggest workflow step.'''

from __future__ import annotations

import json

from ..step import AbstractStep
from ....lib.context import WorkflowContext
from ....lib.exceptions import StepExecutionError


class SuggestStep(AbstractStep):
    '''Run the full suggestion pipeline with refinement loop.'''

    def __init__(self) -> None:
        super().__init__(name='Suggest Issues', retries=0)

    def run(self, ctx: WorkflowContext) -> None:
        if ctx.opencode_service is None:
            raise StepExecutionError('OpenCode service is not available on context.')
        if ctx.github is None:
            raise StepExecutionError('GitHub service is not available on context.')

        requested_count = ctx.config.suggested_issues_count
        if requested_count <= 0:
            if ctx.config.workflow_mode == 'suggest':
                requested_count = 3
                ctx.logger.warn(
                    'SUGGESTED_ISSUES_COUNT not set; defaulting to 3 for suggest workflow',
                )
            else:
                ctx.logger.verbose('Suggested issue generation disabled')
                return

        ctx.logger.phase('SUGGEST-ISSUES')
        if ctx.config.dry_run:
            ctx.logger.warn('Dry run - skipping suggested issue creation')
            return

        try:
            available_labels = ctx.github.list_labels()
        except Exception as exc:
            raise StepExecutionError('Failed to list labels for repository.') from exc

        extra_context = (
            f'SUGGESTED_COUNT: {requested_count}\n'
            f'AVAILABLE_LABELS: {",".join(available_labels)}'
        )
        success = ctx.opencode_service.run_phase(
            'suggest-issues',
            ctx,
            extra_context=extra_context,
        )
        if not success:
            ctx.logger.warn('Suggest-issues phase had issues, continuing without suggestions')
            return

        suggestions_file = ctx.config.state_dir / 'suggested_issues.json'
        if not suggestions_file.exists() or suggestions_file.stat().st_size == 0:
            ctx.logger.warn('No suggestions generated (suggested_issues.json missing or empty)')
            return

        try:
            suggestions = json.loads(suggestions_file.read_text(encoding='utf-8'))
        except (OSError, json.JSONDecodeError) as exc:
            ctx.logger.warn(f'Could not parse suggestions JSON: {exc}')
            return

        if not isinstance(suggestions, list) or not suggestions:
            ctx.logger.warn('Suggestions list is empty')
            return

        self._ensure_ai_suggested_label(ctx)

        created_urls: list[str] = []
        for index, suggestion in enumerate(suggestions):
            if not isinstance(suggestion, dict):
                ctx.logger.warn(f'Skipping suggestion #{index} due to invalid JSON')
                continue

            if not self._refine_suggestion(ctx, index, suggestion, available_labels):
                continue

            refined_file = ctx.config.state_dir / 'refined_issue.json'
            try:
                refined = json.loads(refined_file.read_text(encoding='utf-8'))
            except (OSError, json.JSONDecodeError) as exc:
                ctx.logger.warn(
                    f'Skipping suggestion #{index} due to refinement read failure',
                )
                self._cleanup_refinement_files(ctx)
                continue

            if not refined.get('create', False):
                reason = refined.get('reason') or refined.get('message') or 'No reason provided'
                ctx.logger.warn(
                    f'Suggestion #{index} skipped by refinement: {reason}',
                )
                self._cleanup_refinement_files(ctx)
                continue

            title = refined.get('title')
            body = refined.get('body')
            labels = refined.get('labels', [])
            priority = refined.get('priority')

            if not title or not body:
                ctx.logger.warn(
                    f'Skipping suggestion #{index} due to missing title/body',
                )
                self._cleanup_refinement_files(ctx)
                continue

            if priority:
                body = f'{body}\n\n**Priority:** {priority}'

            suggestion_footer = (
                f'Suggested by issue-suggestor after {ctx.config.repo}#{ctx.config.issue}.'
                if ctx.config.issue is not None
                else f'Suggested by issue-suggestor for {ctx.config.repo}.'
            )
            body = f'{body}\n\n---\n{suggestion_footer}'

            label_list = self._build_label_list(labels)
            try:
                issue_url = ctx.github.create_issue(title, body, label_list)
            except Exception as exc:
                ctx.logger.warn(
                    f'Failed to create suggested issue: {title}',
                )
                self._cleanup_refinement_files(ctx)
                continue

            created_urls.append(issue_url)
            ctx.logger.success(f'Suggested issue created: {issue_url}')
            self._cleanup_refinement_files(ctx)

        if created_urls:
            ctx.suggested_issue_urls = created_urls
            ctx.state.save('suggested_issue_urls', '\n'.join(created_urls))

    def _ensure_ai_suggested_label(self, ctx: WorkflowContext) -> None:
        try:
            ctx.github.ensure_label(
                name='ai-suggested',
                color='c5def5',
                description='AI suggested follow-up issue',
            )
        except Exception:
            ctx.logger.warn('Failed to create label ai-suggested (continuing)')

    def _refine_suggestion(
        self,
        ctx: WorkflowContext,
        index: int,
        suggestion: dict,
        available_labels: list[str],
    ) -> bool:
        current_file = ctx.config.state_dir / 'current_suggestion.json'
        refined_file = ctx.config.state_dir / 'refined_issue.json'
        try:
            current_file.write_text(json.dumps(suggestion), encoding='utf-8')
        except OSError as exc:
            ctx.logger.warn(
                f'Failed to write suggestion #{index} to {current_file}',
            )
            return False

        extra_context = (
            f'SUGGESTION_JSON: {json.dumps(suggestion)}\n'
            f'AVAILABLE_LABELS: {",".join(available_labels)}'
        )
        success = ctx.opencode_service.run_phase(
            'refine-issue',
            ctx,
            extra_context=extra_context,
        )
        if not success:
            ctx.logger.warn(f'Refine-issue phase failed for suggestion #{index}')
            return False

        if not refined_file.exists() or refined_file.stat().st_size == 0:
            ctx.logger.warn(
                f'Refined issue output missing for suggestion #{index}',
            )
            return False

        ctx.logger.verbose(f'Refinement complete for suggestion #{index}')
        return True

    def _build_label_list(self, labels: list[str]) -> list[str]:
        cleaned = ['ai-suggested']
        for label in labels:
            if not isinstance(label, str):
                continue
            trimmed = label.strip()
            if trimmed and trimmed not in cleaned:
                cleaned.append(trimmed)
        return cleaned

    def _cleanup_refinement_files(self, ctx: WorkflowContext) -> None:
        for filename in ('current_suggestion.json', 'refined_issue.json'):
            path = ctx.config.state_dir / filename
            try:
                if path.exists():
                    path.unlink()
            except OSError:
                ctx.logger.verbose(f'Failed to cleanup {filename}')

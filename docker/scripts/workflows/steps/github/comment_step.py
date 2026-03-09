'''GitHub issue comment step.'''

from __future__ import annotations

from ..step import AbstractStep
from ....lib.context import WorkflowContext
from ....lib.exceptions import StepExecutionError


class GithubCommentStep(AbstractStep):
    '''Add a status comment to the source issue.'''

    def __init__(self, status: str, details: str = '') -> None:
        super().__init__(name='Comment on Issue', retries=0)
        self.status = status
        self.comment_type = status
        self.details = details

    def run(self, ctx: WorkflowContext) -> None:
        if ctx.config.dry_run:
            ctx.logger.log(
                f'[DRY RUN] Would comment on issue #{ctx.config.issue}: {self.comment_type}'
            )
            return
        if ctx.github is None:
            raise StepExecutionError('GitHub service is not available on context.')
        if ctx.config.issue is None:
            ctx.logger.warn('ISSUE not set; skipping issue comment')
            return

        ctx.logger.log(f'Adding comment to issue #{ctx.config.issue}...')
        comment_body = self._build_comment(ctx)
        try:
            ctx.github.add_issue_comment(ctx.config.issue, comment_body)
        except Exception as exc:
            raise StepExecutionError('Failed to add issue comment.') from exc

        ctx.logger.success('Comment added to issue')

    def _build_comment(self, ctx: WorkflowContext) -> str:
        if self.status == 'success':
            suggestions_block = ''
            if ctx.suggested_issue_urls:
                suggestions = '\n'.join(
                    f'- {url}' for url in ctx.suggested_issue_urls
                )
                suggestions_block = f'\n\n### Suggested Follow-up Issues\n{suggestions}'
            return (
                '## 🤖 Automated Fix Ready\n\n'
                'A pull request has been created to resolve this issue.\n\n'
                f'**Branch:** `{ctx.working_branch}`\n'
                f'**PR:** {ctx.pr_url or "N/A"}\n\n'
                '### Status\n'
                '- ✅ Implementation complete\n'
                '- ✅ Tests passing\n'
                '- ✅ Review passed'
                f'{suggestions_block}\n\n'
                'Please review the PR and merge if satisfactory.'
            )

        if self.status == 'partial':
            tests_status = '✅ Tests passing' if ctx.tests_passed else '❌ Tests failing'
            review_status = (
                '✅ Review passed' if ctx.review_passed else '⚠️ Review found issues'
            )
            return (
                '## 🤖 Automated Fix - Partial Progress\n\n'
                "I've made progress on this issue but couldn't complete it fully.\n\n"
                f'**Branch:** `{ctx.working_branch}`\n'
                f'**PR:** {ctx.pr_url or "Not created"}\n\n'
                '### Status\n'
                '- ✅ Implementation attempted\n'
                f'- {tests_status}\n'
                f'- {review_status}\n\n'
                '### Details\n'
                f'{self.details}\n\n'
                '### Next Steps\n'
                'You can continue working on this branch manually, or run the resolver again:\n'
                f'```bash\n./resolve.py {ctx.config.repo} {ctx.config.issue} '
                f'--branch {ctx.working_branch}\n```'
            )

        if self.status == 'error':
            return (
                '## 🤖 Automated Fix - Error\n\n'
                'I encountered an error while trying to resolve this issue.\n\n'
                f'**Branch:** `{ctx.working_branch}`\n\n'
                '### Error Details\n'
                f'{self.details}\n\n'
                '### Next Steps\n'
                'You can try running the resolver again or work on the branch manually:\n'
                f'```bash\n./resolve.py {ctx.config.repo} {ctx.config.issue} '
                f'--branch {ctx.working_branch}\n```'
            )

        return f'Workflow completed with status: {self.status}'

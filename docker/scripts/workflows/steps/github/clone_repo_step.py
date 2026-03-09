'''GitHub repository clone step.'''

from __future__ import annotations

import shutil
from pathlib import Path

from ..step import AbstractStep
from ....lib.context import WorkflowContext
from ....lib.exceptions import StepExecutionError


class GithubCloneRepoStep(AbstractStep):
    '''Clone repository and checkout or create working branch.'''

    def __init__(self, depth: int = 100, create_branch: bool = True) -> None:
        super().__init__(name='Clone Repository', retries=0)
        self.depth = depth
        self.create_branch = create_branch

    def run(self, ctx: WorkflowContext) -> None:
        if ctx.git_service is None:
            raise StepExecutionError('Git service is not available on context.')

        ctx.logger.log(f'Setting up repository {ctx.config.repo}...')
        try:
            ctx.git_service.clone(ctx.config.repo, depth=self.depth)
        except Exception as exc:
            raise StepExecutionError('Failed to clone repository.') from exc

        try:
            ctx.default_branch = ctx.git_service.get_default_branch()
        except Exception as exc:
            raise StepExecutionError('Failed to determine default branch.') from exc

        if not self.create_branch:
            ctx.resuming = False
            ctx.working_branch = ctx.default_branch
            ctx.logger.success(f'Using default branch: {ctx.default_branch}')
        else:
            branch_name = ctx.config.computed_branch
            ctx.logger.log(f'Checking for existing branch: {branch_name}')
            try:
                branch_exists = ctx.git_service.branch_exists_remote(branch_name)
            except Exception as exc:
                raise StepExecutionError('Failed to check remote branch.') from exc

            if branch_exists:
                ctx.logger.log(f'Continuing on existing branch: {branch_name}')
                try:
                    ctx.git_service.checkout_existing(branch_name)
                except Exception as exc:
                    raise StepExecutionError('Failed to checkout existing branch.') from exc
                ctx.resuming = True
                ctx.working_branch = branch_name
                try:
                    commits_ahead = ctx.git_service.commits_ahead(ctx.default_branch)
                except Exception as exc:
                    raise StepExecutionError('Failed to count commits ahead.') from exc
                ctx.logger.success(
                    f'Checked out existing branch with {commits_ahead} commit(s) ahead',
                )
            else:
                ctx.logger.log(f'Creating new branch: {branch_name}')
                try:
                    ctx.git_service.checkout_new(branch_name)
                except Exception as exc:
                    raise StepExecutionError('Failed to create new branch.') from exc
                ctx.resuming = False
                ctx.working_branch = branch_name
                ctx.logger.success('Created new branch')

        opencode_config_src = Path('/opencode-config')
        if opencode_config_src.exists() and opencode_config_src.is_dir():
            for item in opencode_config_src.iterdir():
                dest = ctx.config.work_dir / item.name
                if item.is_dir():
                    shutil.copytree(item, dest, dirs_exist_ok=True)
                else:
                    shutil.copy2(item, dest)
            ctx.logger.log('Copied /opencode-config into work directory')

        ctx.logger.success(
            f'Repository ready (default branch: {ctx.default_branch})',
        )

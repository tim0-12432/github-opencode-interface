
from __future__ import annotations

import os
import sys
from dataclasses import replace

from .lib import (
    GitHubService,
    GitService,
    OpenCodeService,
    StateManager,
    TestingService,
    WorkflowConfig,
    WorkflowContext,
    WorkflowLogger,
)
from .lib.exceptions import ValidationError, WorkflowError
from .workflows import ResolveWorkflow, ReviewWorkflow, SuggestWorkflow

WORKFLOW_REGISTRY: dict[str, type] = {
    'resolve': ResolveWorkflow,
    'suggest': SuggestWorkflow,
    'review': ReviewWorkflow,
}


def _resolve_workflow_mode(config: WorkflowConfig, logger: WorkflowLogger) -> str:
    mode = (config.workflow_mode or '').strip().lower()
    if not mode and config.suggest_only:
        logger.warn('SUGGEST_ONLY is deprecated; use WORKFLOW_MODE=suggest instead')
        mode = 'suggest'
    if not mode:
        mode = 'resolve'
    return mode


def _suggestions_count(config: WorkflowConfig, mode: str) -> int:
    if mode == 'suggest' and config.suggested_issues_count <= 0:
        return 3
    return max(config.suggested_issues_count, 0)


def _print_banner(
    ctx: WorkflowContext,
    mode: str,
    suggestions_count: int,
) -> None:
    if mode == 'suggest':
        title = 'GitHub Issue Suggester'
    elif mode == 'review':
        title = 'GitHub Reviewer Reporter'
    else:
        title = 'GitHub Issue Resolver'

    ctx.logger.banner(title)
    issue_label = f'#{ctx.config.issue}' if ctx.config.issue is not None else 'not set'
    ctx.logger.log(f'  Workflow:      {mode}')
    ctx.logger.log(f'  Repository:    {ctx.config.repo or "not set"}')
    ctx.logger.log(f'  Issue:         {issue_label}')
    ctx.logger.log(f'  Provider:      {ctx.config.opencode_provider or "github-copilot"}')
    ctx.logger.log(f'  Model:         {ctx.config.opencode_model or "default"}')
    ctx.logger.log(f'  Test Cycles:   max {ctx.config.max_test_cycles}')
    ctx.logger.log(f'  Review Cycles: max {ctx.config.max_review_cycles}')
    ctx.logger.log(f'  Suggestions:  {suggestions_count}')
    ctx.logger.log('')


def main() -> int:
    try:
        config = WorkflowConfig.from_env(dict(os.environ))
    except WorkflowError as exc:
        print(f'Configuration error: {exc}', file=sys.stderr)
        return 1

    logger = WorkflowLogger(verbose=config.verbose)

    try:
        mode = _resolve_workflow_mode(config, logger)
        config = replace(config, workflow_mode=mode)
        config.validate()
    except ValidationError as exc:
        logger.error(str(exc))
        return 1
    except WorkflowError as exc:
        logger.error(f'Workflow configuration error: {exc}')
        return 1

    try:
        state = StateManager(config.state_dir)
        state.init()
        github = GitHubService(config.github_token, config.repo)
        git_service = GitService(config.work_dir, config.github_token)
        opencode_service = OpenCodeService(
            model=config.opencode_model,
            work_dir=config.work_dir,
        )
        testing_service = TestingService(config.work_dir)
    except Exception as exc:
        logger.error(f'Failed to initialize services: {exc}')
        return 1

    ctx = WorkflowContext(
        config=config,
        logger=logger,
        state=state,
        github=github,
        git_service=git_service,
        opencode_service=opencode_service,
        testing_service=testing_service,
    )

    suggestions_count = _suggestions_count(config, mode)
    _print_banner(ctx, mode, suggestions_count)

    if config.dry_run:
        ctx.logger.warn('=' * 60)
        ctx.logger.warn('  DRY RUN MODE — No writes will be performed')
        ctx.logger.warn('  GitHub reads (issue, labels) and git clone: allowed')
        ctx.logger.warn('  OpenCode, commits, pushes, PRs, comments: SKIPPED')
        ctx.logger.warn('=' * 60)

    workflow_cls = WORKFLOW_REGISTRY.get(mode)
    if workflow_cls is None:
        logger.error(
            f'Invalid workflow mode: {mode}. Use resolve, suggest, or review.',
        )
        return 1

    workflow = workflow_cls()

    try:
        success = workflow.run(ctx)
    except ValidationError as exc:
        logger.error(str(exc))
        return 1
    except WorkflowError as exc:
        logger.error(f'Workflow failed: {exc}')
        return 1
    except KeyboardInterrupt:
        logger.warn('Workflow interrupted by user')
        return 1
    except Exception as exc:
        logger.error(f'Unexpected error: {exc}')
        return 1

    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())

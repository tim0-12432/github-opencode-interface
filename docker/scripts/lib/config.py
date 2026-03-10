'''Configuration management for workflow execution.'''

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from .exceptions import ConfigError, ValidationError


class ModelTier(Enum):
    '''Model cost/capability tiers for OpenCode phases.'''

    SMALL = 'small'
    STANDARD = 'standard'
    LARGE = 'large'


@dataclass(frozen=True)
class WorkflowConfig:
    '''Configuration values for the workflow system.'''

    github_token: str
    repo: str
    issue: int | None
    branch: str | None
    opencode_provider: str
    opencode_model: str
    opencode_small_model: str
    opencode_standard_model: str
    opencode_large_model: str
    gh_token: str | None
    anthropic_api_key: str | None
    openai_api_key: str | None
    max_test_cycles: int
    max_review_cycles: int
    max_phase_attempts: int
    suggested_issues_count: int
    workflow_mode: str
    suggest_only: bool
    verbose: bool
    dry_run: bool
    git_author_name: str
    git_author_email: str
    work_dir: Path
    prompts_dir: Path
    state_dir: Path
    issue_context_path: Path

    def resolve_model(self, tier: ModelTier) -> str:
        '''Resolve a model tier to a concrete model string.

        Falls back to opencode_model (the legacy single-model field)
        if a tier-specific value is not configured.

        Args:
            tier: The model tier to resolve.

        Returns:
            The concrete model string for the given tier.
        '''
        mapping = {
            ModelTier.SMALL: self.opencode_small_model,
            ModelTier.STANDARD: self.opencode_standard_model,
            ModelTier.LARGE: self.opencode_large_model,
        }
        resolved = mapping.get(tier, '')
        return resolved or self.opencode_model

    @classmethod
    def from_env(cls, env: dict) -> 'WorkflowConfig':
        '''Create configuration from environment variables.

        Args:
            env: Environment variables mapping.

        Returns:
            WorkflowConfig built from the provided environment.
        '''
        def to_int(value: str | None, default: int) -> int:
            if value is None or value == '':
                return default
            try:
                return int(value)
            except ValueError as exc:
                raise ConfigError(f'Invalid integer value: {value}') from exc

        def to_bool(value: str | None) -> bool:
            return str(value or '').lower() == 'true'

        issue_value = env.get('ISSUE') or env.get('ISSUE_NUMBER')
        issue = int(issue_value) if issue_value and issue_value.isdigit() else None

        default_model = env.get('OPENCODE_MODEL', 'github-copilot/claude-sonnet-4.5')

        return cls(
            github_token=env.get('GITHUB_TOKEN', ''),
            repo=env.get('REPO', ''),
            issue=issue,
            branch=env.get('BRANCH'),
            opencode_provider=env.get('OPENCODE_PROVIDER', 'github-copilot'),
            opencode_model=default_model,
            opencode_small_model=env.get('OPENCODE_SMALL_MODEL', ''),
            opencode_standard_model=env.get('OPENCODE_STANDARD_MODEL', ''),
            opencode_large_model=env.get('OPENCODE_LARGE_MODEL', ''),
            gh_token=env.get('GH_TOKEN') or env.get('GITHUB_TOKEN'),
            anthropic_api_key=env.get('ANTHROPIC_API_KEY'),
            openai_api_key=env.get('OPENAI_API_KEY'),
            max_test_cycles=to_int(env.get('MAX_TEST_CYCLES'), 5),
            max_review_cycles=to_int(env.get('MAX_REVIEW_CYCLES'), 2),
            max_phase_attempts=to_int(env.get('MAX_PHASE_ATTEMPTS'), 3),
            suggested_issues_count=to_int(env.get('SUGGESTED_ISSUES_COUNT'), 0),
            workflow_mode=env.get('WORKFLOW_MODE', ''),
            suggest_only=to_bool(env.get('SUGGEST_ONLY')),
            verbose=to_bool(env.get('VERBOSE')),
            dry_run=to_bool(env.get('DRY_RUN')),
            git_author_name=env.get('GIT_AUTHOR_NAME', 'Issue Resolver Bot'),
            git_author_email=env.get('GIT_AUTHOR_EMAIL', 'bot@issue-resolver.local'),
            work_dir=Path(env.get('WORK_DIR', '/workspace/repo')),
            prompts_dir=Path(env.get('PROMPTS_DIR', '/prompts')),
            state_dir=Path(env.get('STATE_DIR', '/workspace/.state')),
            issue_context_path=Path(
                env.get('ISSUE_CONTEXT_PATH', '/workspace/issue_context.md'),
            ),
        )

    def validate(self) -> None:
        '''Validate configuration values.

        Raises:
            ValidationError: If required configuration is missing or invalid.
        '''
        errors: list[str] = []

        if not self.repo:
            errors.append(
                'REPO is not set. Set it in config.env or export REPO=owner/repo.',
            )

        if not self.github_token:
            errors.append(
                'GITHUB_TOKEN is not set. Create a token and export GITHUB_TOKEN=...',
            )

        if self.workflow_mode not in {'', 'resolve', 'suggest', 'review'}:
            errors.append(
                "Invalid WORKFLOW_MODE. Use 'resolve', 'suggest', or 'review'.",
            )

        requires_issue = self.workflow_mode not in {'suggest', 'review'} and not (
            self.suggest_only
        )
        if requires_issue and self.issue is None:
            errors.append(
                'ISSUE is not set. Provide the issue number (e.g., ISSUE=123).',
            )

        if not self.dry_run:
            provider = self.opencode_provider or 'github-copilot'
            if provider == 'github-copilot':
                if not self.gh_token:
                    errors.append(
                        'GH_TOKEN is not set for GitHub Copilot provider. '
                        'Export GH_TOKEN or set GITHUB_TOKEN.',
                    )
            elif provider == 'anthropic':
                if not self.anthropic_api_key:
                    errors.append(
                        'ANTHROPIC_API_KEY is not set. Export ANTHROPIC_API_KEY to continue.',
                    )
            elif provider == 'openai':
                if not self.openai_api_key:
                    errors.append(
                        'OPENAI_API_KEY is not set. Export OPENAI_API_KEY to continue.',
                    )
            else:
                errors.append(f'Unsupported OPENCODE_PROVIDER: {provider}')

        if errors:
            raise ValidationError('\n'.join(errors))

    @property
    def owner(self) -> str:
        '''Return repository owner from repo slug.'''
        if '/' not in self.repo:
            return ''
        return self.repo.split('/', maxsplit=1)[0]

    @property
    def repo_name(self) -> str:
        '''Return repository name from repo slug.'''
        if '/' not in self.repo:
            return self.repo
        return self.repo.split('/', maxsplit=1)[1]

    @property
    def computed_branch(self) -> str:
        '''Return computed branch name derived from issue or explicit branch.'''
        if self.branch:
            return self.branch
        if self.issue is None:
            return 'fix/issue'
        return f'fix/issue-{self.issue}'

'''Workflow context container.'''

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from .config import WorkflowConfig
from .logger import WorkflowLogger
from .state import StateManager

if TYPE_CHECKING:
    from .github_service import GitHubService
    from .git_service import GitService
    from .opencode_service import OpenCodeService
    from .testing_service import TestingService


@dataclass
class WorkflowContext:
    '''Runtime context for workflow execution.'''

    config: WorkflowConfig
    logger: WorkflowLogger
    state: StateManager
    github: 'GitHubService | None' = None
    git_service: 'GitService | None' = None
    opencode_service: 'OpenCodeService | None' = None
    testing_service: 'TestingService | None' = None

    default_branch: str | None = None
    working_branch: str | None = None
    resuming: bool = False
    tests_passed: bool = False
    review_passed: bool = False
    pr_url: str | None = None

    issue_title: str | None = None
    issue_body: str | None = None
    issue_labels: list[str] = field(default_factory=list)
    issue_comments: list[str] = field(default_factory=list)

    suggested_issue_urls: list[str] = field(default_factory=list)

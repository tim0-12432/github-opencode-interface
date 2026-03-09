# Python Workflow Architecture

This document describes the Python-based workflow architecture used by the
`github-opencode-interface` project. The Python implementation replaces the
legacy Bash workflows and provides a structured, testable system for automating
GitHub issue resolution with OpenCode.

## System overview

The workflow system automates three related jobs:

- **Resolve**: implement a fix for a GitHub issue, run tests, review, and open a PR.
- **Suggest**: generate follow-up issues based on repository context.
- **Review**: generate a multi-part code review report and open a PR containing it.

At runtime, the orchestrator reads configuration from environment variables,
initializes services, builds a `WorkflowContext`, and executes a workflow
composed of ordered steps.

### Design goals

- **Deterministic execution**: each workflow is a predictable sequence of steps.
- **Resumable state**: file-based state in `/workspace/.state` is compatible with
  OpenCode expectations.
- **Separation of concerns**: orchestration, steps, and services are isolated.
- **Extensibility**: new workflows and steps can be added with minimal wiring.
- **Safe failure**: standardized error handling, retries, and finalization steps.

## Module structure

```
docker/scripts/
  orchestrator.py
  lib/
    config.py
    context.py
    exceptions.py
    git_service.py
    github_service.py
    logger.py
    opencode_service.py
    prompt_service.py
    state.py
    testing_service.py
  workflows/
    workflow.py
    resolve_workflow.py
    suggest_workflow.py
    review_workflow.py
    steps/
      step.py
      cycles/
      finalize/
      github/
      opencode/
      setup/
      state/
      testing/
```

### Responsibilities by module

- **`orchestrator.py`**: entry point. Reads env, validates config, initializes
  services, builds `WorkflowContext`, and runs a selected workflow.
- **`lib/config.py`**: configuration model and validation.
- **`lib/context.py`**: shared runtime state between steps.
- **`lib/state.py`**: file-based state manager.
- **`lib/*_service.py`**: service layer for Git, GitHub, OpenCode, prompts, tests.
- **`workflows/*.py`**: workflow definitions and step sequences.
- **`workflows/steps/*`**: concrete step implementations.

## Class hierarchy

### Workflow orchestration

```
AbstractWorkflow
  - ResolveWorkflow
  - SuggestWorkflow
  - ReviewWorkflow
```

`AbstractWorkflow` defines the contract for constructing steps (`build_steps`)
and a default `run` method. Each concrete workflow can override `run` to add
custom error handling or finalization logic.

### Steps

```
AbstractStep
  - GithubLoginStep
  - GithubFetchIssueStep
  - GithubCloneRepoStep
  - AnalyzeStep
  - ImplementStep
  - TestCycleStep
  - ReviewCycleStep
  - FinalizeSuccessStep
  - ...and many more
```

`AbstractStep` provides:

- Retry support (per-step retries and delay).
- Lifecycle status (`PENDING`, `RUNNING`, `SUCCESS`, `FAILED`, `SKIPPED`).
- A shared `execute()` wrapper that calls `run()` with retry logic.

### Services

```
GitHubService    -> PyGithub API operations
GitService       -> git subprocess wrapper
OpenCodeService  -> opencode subprocess wrapper
TestingService   -> test detection and execution
PromptService    -> prompt loading and rendering
StateManager     -> file-based state storage
WorkflowLogger   -> structured console logging
```

Services are injected into `WorkflowContext` and accessed by steps.

## Data flow

### WorkflowContext

`WorkflowContext` is the runtime container passed to every step. It holds:

- `config`: immutable `WorkflowConfig` values.
- `logger`: `WorkflowLogger` instance.
- `state`: `StateManager` for file-based state.
- `github`, `git_service`, `opencode_service`, `testing_service`: services.
- Working fields: branch names, flags, issue metadata, suggested URLs.

### WorkflowConfig

`WorkflowConfig.from_env()` builds config from environment variables and
`validate()` enforces required values (repo, tokens, workflow mode). It also
computes a default branch name via `computed_branch`.

### StateManager

State is stored as individual files in `STATE_DIR` (default
`/workspace/.state`). Files are written without extensions to remain compatible
with OpenCode and the previous Bash implementation.

```
StateManager.save('last_test_output', '...')
StateManager.save_review_feedback('...')
```

Steps use `StateManager` to store and retrieve transient artifacts such as test
output, review feedback, or suggested issue URLs.

## Service layer pattern

The service layer isolates external integrations:

- **GitHubService**: wraps PyGithub for issues, labels, and PRs. It replaces the
  `gh` CLI for API operations.
- **GitService**: runs `git` commands with an authenticated clone URL and
  handles branches, commits, and push operations.
- **OpenCodeService**: runs the `opencode` binary via subprocess and executes
  prompt phases with retry logic.
- **TestingService**: detects repository test commands and executes tests.
- **PromptService**: loads prompt templates and renders context placeholders.

This separation allows steps to focus on flow control, not integration logic.

## Step lifecycle and execution

All steps inherit `AbstractStep` and implement `run(ctx)`.

Execution lifecycle:

1. `execute(ctx)` is called.
2. `should_skip(ctx)` is checked (defaults to `False`).
3. `run(ctx)` is executed with retry support.
4. Step status is updated and logged.

Example step skeleton:

```python
from ..step import AbstractStep
from ....lib.context import WorkflowContext


class ExampleStep(AbstractStep):
    def __init__(self) -> None:
        super().__init__(name='Example', retries=1)

    def run(self, ctx: WorkflowContext) -> None:
        ctx.logger.log('Doing work...')
```

## State management protocol

State is file-based for compatibility with OpenCode and the previous Bash
scripts. State files are stored in `STATE_DIR` and accessed via
`StateManager`. Some keys are read or written directly by steps and OpenCode
prompts.

Common state files:

| File | Purpose |
| --- | --- |
| `last_test_output` | Latest combined stdout/stderr from tests. |
| `last_review_feedback` | Feedback captured from the review step. |
| `suggested_issue_urls` | List of created issue URLs. |
| `review_passed` | Marker file produced by OpenCode review. |
| `review_feedback` | Feedback produced by OpenCode review. |
| `suggested_issues.json` | Suggest workflow output from OpenCode. |
| `current_suggestion.json` | Current suggestion to refine. |
| `refined_issue.json` | Refined suggestion output. |
| `*_review_report` | Individual report outputs, e.g. `security_review_report`. |

`StateManager.cleanup()` strips extensions from files (e.g. `foo.txt` → `foo`) to
normalize outputs that may come from OpenCode or external tools.

## Error handling and retries

Error handling happens in two layers:

1. **Step-level**: `AbstractStep.execute()` retries on exceptions and raises
   `StepRetryExhaustedError` once retries are exhausted.
2. **Workflow-level**: each workflow handles `StepExecutionError` differently
   and may invoke a finalize step.

Workflow-specific behavior:

- **ResolveWorkflow**: on `StepExecutionError`, writes a partial completion and
  reports test or review failures with context. On unexpected exceptions, it
  triggers `FinalizeErrorStep`.
- **SuggestWorkflow**: logs errors and stops without finalization steps.
- **ReviewWorkflow**: on any failure, triggers `FinalizeErrorStep`.

## Integration points

### PyGithub

`GitHubService` uses PyGithub (`github` package) to handle issue retrieval,
label management, and PR creation. This avoids reliance on the `gh` CLI.

### Git subprocess

`GitService` wraps `git` commands such as `clone`, `checkout`, `commit`, and
`push`, using `subprocess.run` with captured output. It uses an authenticated
clone URL built from the GitHub token.

### OpenCode subprocess

`OpenCodeService` runs the `opencode` binary using subprocess, sending prompt
content via stdin. It retries each phase up to `MAX_PHASE_ATTEMPTS` and reports
success or failure back to the steps.

### Testing subprocess

`TestingService` detects the test command based on repository files
(`package.json`, `pyproject.toml`, `go.mod`, `Cargo.toml`, `Makefile`) and runs
the tests via subprocess.

## Notes on legacy compatibility

Some files under `workflows/steps/` exist for backwards-compatible imports
(`github_login.py`, `github_fetch_issue.py`, etc.). The primary implementations
live in the `workflows/steps/github/` package. There is also a legacy
`opencode_step.py` that is not used by current workflows, retained to preserve
older imports.

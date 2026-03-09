# Workflow Execution Guide

This guide explains how the Python workflows execute in
`github-opencode-interface`, what each workflow does, and how to extend the
system safely.

## How workflows execute

Execution follows a simple pipeline:

```
orchestrator.py
  → Workflow (Resolve | Suggest | Review)
    → Ordered Steps
```

### Orchestrator responsibilities

`docker/scripts/orchestrator.py` performs the following tasks:

1. Build `WorkflowConfig` from environment variables.
2. Validate configuration.
3. Initialize services (GitHub, Git, OpenCode, Testing, State).
4. Construct `WorkflowContext`.
5. Select the workflow based on `WORKFLOW_MODE`.
6. Execute the workflow and handle high-level errors.

## The three workflows

### Resolve workflow

The resolve workflow fixes a GitHub issue end-to-end.

Step sequence (from `ResolveWorkflow.build_steps()`):

1. `GithubLoginStep`
2. `GithubFetchIssueStep`
3. `GithubCloneRepoStep`
4. `AnalyzeStep`
5. `ImplementStep(review_cycle=1)`
6. `TestCycleStep`
7. `ReviewCycleStep`
8. `FinalizeSuccessStep`

Error handling:

- If a step raises `StepExecutionError`, the workflow produces a partial result
  via `FinalizePartialStep` and records the failure reason (tests or review).
- Unexpected exceptions trigger `FinalizeErrorStep`.

### Suggest workflow

The suggest workflow generates follow-up GitHub issues based on repository
context (and optionally the current issue).

Step sequence:

1. `GithubLoginStep`
2. `GithubFetchIssueStep` **or** `CreateIssueContextStep('suggest')`
3. `GithubCloneRepoStep(depth=50)`
4. `SuggestStep`

It does not run finalize steps. It prints a report of created issues when done.

### Review workflow

The review workflow generates a multi-part audit report and opens a PR that
adds the report to the repository.

Step sequence:

1. `GithubLoginStep`
2. `GithubCloneRepoStep`
3. `CreateIssueContextStep('review')`
4. `ReportPhaseStep('security-report')`
5. `ReportPhaseStep('architecture-report')`
6. `ReportPhaseStep('customer-report')`
7. `ReportPhaseStep('engineering-report')`
8. `ReportPhaseStep('testing-report')`
9. `ReportPhaseStep('resource-report')`
10. `CleanupStateStep`
11. `ReportAggregationStep`
12. `CommitStep` (finalization)
13. `GithubPushStep`
14. `Create PR` (handled directly in `ReviewWorkflow._create_review_pr()`)

Any failure triggers `FinalizeErrorStep`.

## Step types and purposes

### GitHub steps

- **`GithubLoginStep`**: configure git identity (user name/email).
- **`GithubFetchIssueStep`**: fetch issue data via PyGithub and create
  `/workspace/issue_context.md` for prompts.
- **`GithubCloneRepoStep`**: clone the repository and check out a working branch.
- **`GithubPushStep`**: push the working branch to origin.
- **`GithubCreatePRStep`**: open a PR for a resolved issue.
- **`GithubCommentStep`**: comment on the issue with success/partial/error status.

### OpenCode steps

- **`AnalyzeStep`**: run the `analyze` prompt phase.
- **`ImplementStep`**: run the `implement` prompt phase, optionally with review
  feedback context.
- **`TestCreationStep`**: run the `test` prompt phase to create tests.
- **`FixTestsStep`**: run the `fix-tests` prompt phase.
- **`ReviewStep`**: run the `review` prompt phase and capture feedback markers.
- **`SuggestStep`**: run `suggest-issues` and `refine-issue` phases.
- **`ReportPhaseStep`**: run report-specific phases for review workflow.
- **`ReportAggregationStep`**: aggregate report outputs into a final report.

### Testing steps

- **`RunTestsStep`**: detect and run tests; store output in state.

### Cycles

- **`TestCycleStep`**: test creation → test execution → fix tests loop.
- **`ReviewCycleStep`**: review → re-implement → re-test loop.

### Finalization steps

- **`FinalizeSuccessStep`**: commit, push, open PR, and comment on issue.
- **`FinalizePartialStep`**: commit partial progress, push, comment with reason.
- **`FinalizeErrorStep`**: comment on error and record error state if possible.

## Cycle logic

### Test cycle

`TestCycleStep` runs:

1. `TestCreationStep` (best-effort; failures do not stop the cycle).
2. Up to `MAX_TEST_CYCLES` attempts:
   - `RunTestsStep`
   - If failing, `FixTestsStep` and retry.

The last test output is stored in `STATE_DIR/last_test_output` for prompt
context and partial finalization messages.

### Review cycle

`ReviewCycleStep` runs:

1. `ReviewStep`.
2. On failure, loop up to `MAX_REVIEW_CYCLES`:
   - `ImplementStep` (includes previous review feedback).
   - `TestCycleStep`.

The latest review feedback is stored in `STATE_DIR/last_review_feedback`.

## Configuration and environment variables

`WorkflowConfig.from_env()` reads and validates environment variables.

Common variables:

| Variable | Purpose |
| --- | --- |
| `REPO` | `owner/repo` repository slug. |
| `ISSUE` / `ISSUE_NUMBER` | Issue number to resolve. |
| `WORKFLOW_MODE` | `resolve`, `suggest`, or `review`. |
| `GITHUB_TOKEN` | Token used for GitHub API and clone auth. |
| `GH_TOKEN` | Token used by OpenCode GitHub provider (falls back to GITHUB_TOKEN). |
| `OPENCODE_PROVIDER` | `github-copilot`, `anthropic`, or `openai`. |
| `OPENCODE_MODEL` | Model name for OpenCode. |
| `MAX_TEST_CYCLES` | Max test fix attempts (default 5). |
| `MAX_REVIEW_CYCLES` | Max review fix attempts (default 2). |
| `MAX_PHASE_ATTEMPTS` | Max OpenCode phase retries (default 3). |
| `SUGGESTED_ISSUES_COUNT` | Desired number of suggestions. |
| `DRY_RUN` | When `true`, skip GitHub writes (PRs, comments, issues). |
| `VERBOSE` | Enable verbose logging. |
| `WORK_DIR` | Working directory (default `/workspace/repo`). |
| `PROMPTS_DIR` | Prompt templates directory (default `/prompts`). |
| `STATE_DIR` | State directory (default `/workspace/.state`). |
| `ISSUE_CONTEXT_PATH` | Issue context path (default `/workspace/issue_context.md`). |

### Example (resolve workflow)

```bash
export REPO=acme/widgets
export ISSUE=123
export WORKFLOW_MODE=resolve
export GITHUB_TOKEN=ghp_...
export OPENCODE_PROVIDER=github-copilot
export OPENCODE_MODEL=github-copilot/claude-sonnet-4.5
python docker/scripts/orchestrator.py
```

## State files and meanings

The workflow system and OpenCode prompts communicate via `STATE_DIR`.

| File | Meaning |
| --- | --- |
| `last_test_output` | Latest test output captured by `RunTestsStep`. |
| `last_review_feedback` | Feedback captured from review step. |
| `review_passed` | Marker file written by OpenCode review phase. |
| `review_feedback` | Raw feedback output from OpenCode review phase. |
| `suggested_issues.json` | Raw suggested issues from OpenCode. |
| `current_suggestion.json` | Suggestion currently being refined. |
| `refined_issue.json` | Refined suggestion output used to create issues. |
| `suggested_issue_urls` | URLs for created suggested issues. |
| `*_review_report` | Per-report outputs (e.g. `security_review_report`). |

`CleanupStateStep` removes extensions from files to normalize output names.

## Adding new workflows or steps

### Add a new step

1. Create a step class under `workflows/steps/<category>/`.
2. Inherit `AbstractStep` and implement `run(ctx)`.
3. Export the step in `workflows/steps/__init__.py`.

Example:

```python
from ..step import AbstractStep
from ....lib.context import WorkflowContext


class MyStep(AbstractStep):
    def __init__(self) -> None:
        super().__init__(name='My Step', retries=1)

    def run(self, ctx: WorkflowContext) -> None:
        ctx.logger.log('Doing my work')
```

### Add a new workflow

1. Create a workflow class inheriting `AbstractWorkflow`.
2. Implement `build_steps()` with the step sequence.
3. Register the workflow in `orchestrator.py` (`WORKFLOW_REGISTRY`).

Example:

```python
from .workflow import AbstractWorkflow
from .steps import GithubLoginStep
from ..lib.context import WorkflowContext


class MyWorkflow(AbstractWorkflow):
    def __init__(self) -> None:
        super().__init__('My Workflow')

    def build_steps(self, ctx: WorkflowContext):
        return [GithubLoginStep()]
```

## Troubleshooting

### Configuration errors

- **`REPO is not set`**: set `REPO=owner/repo`.
- **`GITHUB_TOKEN is not set`**: export a token with repo access.
- **`ISSUE is not set`**: required for resolve unless running suggest/review.

### Git failures

- **Clone fails**: verify `GITHUB_TOKEN` and repo permissions.
- **Branch errors**: ensure `BRANCH` or `ISSUE` is set so `computed_branch`
  resolves to a valid name.

### OpenCode failures

- **Phase missing**: ensure prompt files exist in `PROMPTS_DIR` with `.prompt`
  extension (e.g., `analyze.prompt`). Missing prompts are skipped with a warning.
- **`opencode` not found**: confirm `/root/.opencode/bin/opencode` exists in the
  container image.

### Tests keep failing

- Check `STATE_DIR/last_test_output` for the last test output.
- Increase `MAX_TEST_CYCLES` if you want more fix attempts.

### Review cycle never passes

- Check `STATE_DIR/last_review_feedback` for the latest feedback.
- Increase `MAX_REVIEW_CYCLES` or refine the review prompt.

### Suggest workflow creates nothing

- Ensure `SUGGESTED_ISSUES_COUNT` is set or rely on the default of 3.
- Verify `suggested_issues.json` is created by OpenCode.
- Ensure `DRY_RUN` is not enabled.

## Notes on legacy compatibility

Some legacy step modules still exist for backwards-compatible imports (e.g.
`github_login.py`, `github_fetch_issue.py`). The canonical implementations live
in `workflows/steps/github/` and `workflows/steps/opencode/`.

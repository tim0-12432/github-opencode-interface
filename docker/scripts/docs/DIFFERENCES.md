# Intentional Differences: Python vs Bash Implementation

## D1 — PyGithub replaces `gh` CLI
- **Bash**: Used the `gh` CLI for all GitHub API operations (issue fetch, PR creation, comments, labels)
- **Python**: Uses the `PyGithub` library for all GitHub API operations
- **Rationale**: Eliminates the need to install and authenticate `gh` CLI in the container. PyGithub provides a richer typed interface. Functionally equivalent.

## D6 — Unknown `OPENCODE_PROVIDER` rejected at startup
- **Bash**: Accepted any value for `OPENCODE_PROVIDER` silently; only failed later when OpenCode was invoked with wrong credentials
- **Python**: Rejects unknown provider values (`config.validate()`) immediately at startup with a clear error message
- **Rationale**: Fail-fast is better UX. Supported providers are: `github-copilot`, `anthropic`, `openai`

## D8 — Test execution uses `subprocess.run()` instead of `eval`
- **Bash**: Used `eval "$test_cmd"` to run test commands, which allows arbitrary shell expansion
- **Python**: Uses `subprocess.run(cmd.split(), shell=False)` for safe subprocess execution
- **Rationale**: Avoids shell injection. Supported test commands (`npm test`, `pytest`, `go test ./...`, `cargo test`, `make test`) are all safely handled by `.split()`.

## M1 — `setup_opencode_config()` not called in Python
- **Bash**: Dynamically wrote an opencode config JSON file at runtime based on provider/model env vars
- **Python**: Skips dynamic config file writing entirely
- **Rationale**: The Dockerfile already copies a static opencode config via `COPY docker/opencode/ /root/.config/opencode/`. OpenCode reads provider/model from environment variables directly, so the dynamic config write is redundant.

## M4 — Prerequisite validation is upfront, not per-phase
- **Bash**: Validated prerequisites (env vars, credentials) immediately before each OpenCode invocation
- **Python**: Validates all prerequisites once at startup in `config.validate()`
- **Rationale**: Fail-fast reduces wasted time. If credentials are missing, it's better to know before cloning the repo and running analysis phases.

Last updated: 2026-03-08

#!/usr/bin/env bash
# lib/setup.sh - Workflow setup and dispatch

resolve_workflow_mode() {
    local mode
    mode="${WORKFLOW_MODE:-}"

    if [[ -z "$mode" ]] && [[ "${SUGGEST_ONLY:-false}" == "true" ]]; then
        log_warn "SUGGEST_ONLY is deprecated; use WORKFLOW_MODE=suggest instead"
        mode="suggest"
    fi

    if [[ -z "$mode" ]]; then
        mode="resolve"
    fi

    echo "$mode"
}

validate_workflow_mode() {
    local mode="$1"

    case "$mode" in
        resolve|suggest|review)
            return 0
            ;;
        *)
            log_error "Invalid WORKFLOW_MODE: ${mode}. Use 'resolve', 'suggest', or 'review'."
            return 1
            ;;
    esac
}

setup_common() {
    init_state_dir
    setup_opencode_config
    setup_github_auth
}

validate_resolve_inputs() {
    validate_inputs
}

validate_suggest_inputs() {
    log "Validating inputs for suggest workflow..."

    local errors=0

    [[ -z "${REPO:-}" ]] && {
        log_error "REPO is not set. Set it in config.env or export REPO=owner/repo.";
        errors=$((errors + 1));
    }

    [[ -z "${GITHUB_TOKEN:-}" ]] && {
        log_error "GITHUB_TOKEN is not set. Create a token and export GITHUB_TOKEN=...";
        errors=$((errors + 1));
    }

    case "${OPENCODE_PROVIDER:-github-copilot}" in
        github-copilot)
            [[ -z "${GH_TOKEN:-${GITHUB_TOKEN:-}}" ]] && {
                log_error "GH_TOKEN is not set for GitHub Copilot provider. Export GH_TOKEN or set GITHUB_TOKEN.";
                errors=$((errors + 1));
            }
            ;;
        anthropic)
            [[ -z "${ANTHROPIC_API_KEY:-}" ]] && {
                log_error "ANTHROPIC_API_KEY is not set. Export ANTHROPIC_API_KEY to continue.";
                errors=$((errors + 1));
            }
            ;;
        openai)
            [[ -z "${OPENAI_API_KEY:-}" ]] && {
                log_error "OPENAI_API_KEY is not set. Export OPENAI_API_KEY to continue.";
                errors=$((errors + 1));
            }
            ;;
    esac

    [[ $errors -gt 0 ]] && return 1
    log_success "Inputs validated"
}

setup_resolve() {
    validate_resolve_inputs
    setup_common
    fetch_issue
    clone_or_continue_repo

    [[ -d "/opencode-config" ]] && cp -r /opencode-config/. "$WORK_DIR/" 2>/dev/null || true
}

setup_review() {
    validate_suggest_inputs
    setup_common
    clone_or_continue_repo
    create_review_context

    [[ -d "/opencode-config" ]] && cp -r /opencode-config/. "$WORK_DIR/" 2>/dev/null || true
}

clone_repo_for_suggest() {
    log "Cloning repository ${REPO}..."

    [[ -d "$WORK_DIR" ]] && rm -rf "$WORK_DIR"

    if ! git clone --depth 50 "https://x-access-token:${GITHUB_TOKEN}@github.com/${REPO}.git" "$WORK_DIR" 2>&1; then
        log_error "Failed to clone repository ${REPO}. Check your GITHUB_TOKEN and repository access."
        log_error "Tip: verify the repo exists and the token has read access."
        return 1
    fi

    if [[ ! -d "${WORK_DIR}/.git" ]]; then
        log_error "Repository clone succeeded but .git directory not found: ${WORK_DIR}"
        log_error "Tip: ensure WORK_DIR is writable and not overridden by a volume."
        return 1
    fi

    cd "$WORK_DIR"
    DEFAULT_BRANCH=$(git symbolic-ref refs/remotes/origin/HEAD | sed 's@^refs/remotes/origin/@@')
    log_success "Repository ready (default branch: ${DEFAULT_BRANCH})"
}

create_suggest_context() {
    cat > /workspace/issue_context.md <<EOF
# Repository: ${REPO}

No source issue was provided. Generate suggestions based on the current repository state.
EOF

    if [[ ! -s "/workspace/issue_context.md" ]]; then
        log_error "Failed to create issue context file or file is empty: /workspace/issue_context.md"
        log_error "Ensure the container can write to /workspace."
        return 1
    fi
}

create_review_context() {
    cat > /workspace/issue_context.md <<EOF
# Repository: ${REPO}

No source issue was provided. Generate review report based on the current repository state.
EOF

    if [[ ! -s "/workspace/issue_context.md" ]]; then
        log_error "Failed to create issue context file or file is empty: /workspace/issue_context.md"
        log_error "Ensure the container can write to /workspace."
        return 1
    fi
}

setup_suggest() {
    validate_suggest_inputs
    setup_common

    if [[ -n "${ISSUE:-}" ]]; then
        fetch_issue
    else
        create_suggest_context
    fi

    clone_repo_for_suggest
    [[ -d "/opencode-config" ]] && cp -r /opencode-config/. "$WORK_DIR/" 2>/dev/null || true
}

print_banner() {
    local mode
    mode=$(resolve_workflow_mode)

    local suggestions_count="${SUGGESTED_ISSUES_COUNT}"
    if [[ "$mode" == "suggest" ]] && [[ -z "${suggestions_count:-}" || "$suggestions_count" == "0" ]]; then
        suggestions_count="3"
    fi

    echo ""
    echo "╔════════════════════════════════════════════════════════════╗"
    if [[ "$mode" == "suggest" ]]; then
        echo "║                 GitHub Issue Suggester                     ║"
    elif [[ "$mode" == "review" ]]; then
        echo "║                 GitHub Reviewer Reporter                   ║"
    else
        echo "║           GitHub Issue Resolver                            ║"
    fi
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""
    echo "  Repository:    ${REPO:-not set}"
    if [[ -n "${ISSUE:-}" ]]; then
        echo "  Issue:         #${ISSUE}"
    else
        echo "  Issue:         not set"
    fi
    echo "  Provider:      ${OPENCODE_PROVIDER:-copilot}"
    echo "  Model:         ${OPENCODE_MODEL:-default}"
    echo "  Test Cycles:   max ${MAX_TEST_CYCLES}"
    echo "  Review Cycles: max ${MAX_REVIEW_CYCLES}"
    echo "  Suggestions:   ${suggestions_count}"
    echo ""
}

workflow_dispatch() {
    local mode
    mode=$(resolve_workflow_mode)

    if ! validate_workflow_mode "$mode"; then
        exit 1
    fi

    print_banner

    case "$mode" in
        resolve)
            run_workflow_resolve
            ;;
        suggest)
            run_workflow_suggest
            ;;
        review)
            run_workflow_review
            ;;
    esac
}

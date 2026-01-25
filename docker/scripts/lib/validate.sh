#!/usr/bin/env bash
# lib/validate.sh - Input validation

# Requires: REPO, ISSUE, GITHUB_TOKEN, OPENCODE_PROVIDER

# Export required variables (top-level, not in function)
export REPO="${REPO:-}"
export ISSUE="${ISSUE:-}"
export GITHUB_TOKEN="${GITHUB_TOKEN:-}"
export WORK_DIR="${WORK_DIR:-/workspace/repo}"

validate_inputs() {
    log "Validating inputs..."
    
    local errors=0
    
    [[ -z "${REPO:-}" ]] && {
        log_error "REPO is not set. Set it in config.env or export REPO=owner/repo.";
        errors=$((errors + 1));
    }
    [[ -z "${ISSUE:-}" ]] && {
        log_error "ISSUE is not set. Provide the issue number (e.g., ISSUE=123) or pass it as an argument.";
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

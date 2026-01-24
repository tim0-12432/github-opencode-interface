#!/usr/bin/env bash
# lib/validate.sh - Input validation

# Requires: REPO, ISSUE, GITHUB_TOKEN, OPENCODE_PROVIDER

validate_inputs() {
    log "Validating inputs..."
    
    local errors=0
    
    [[ -z "${REPO:-}" ]] && { log_error "REPO is not set"; errors=$((errors + 1)); }
    [[ -z "${ISSUE:-}" ]] && { log_error "ISSUE is not set"; errors=$((errors + 1)); }
    [[ -z "${GITHUB_TOKEN:-}" ]] && { log_error "GITHUB_TOKEN is not set"; errors=$((errors + 1)); }
    
    case "${OPENCODE_PROVIDER:-github-copilot}" in
        github-copilot)
            [[ -z "${GH_TOKEN:-${GITHUB_TOKEN:-}}" ]] && {
                log_error "GH_TOKEN is not set"; errors=$((errors + 1))
            }
            ;;
        anthropic)
            [[ -z "${ANTHROPIC_API_KEY:-}" ]] && {
                log_error "ANTHROPIC_API_KEY is not set"; errors=$((errors + 1))
            }
            ;;
        openai)
            [[ -z "${OPENAI_API_KEY:-}" ]] && {
                log_error "OPENAI_API_KEY is not set"; errors=$((errors + 1))
            }
            ;;
    esac
    
    [[ $errors -gt 0 ]] && exit 1
    log_success "Inputs validated"
}

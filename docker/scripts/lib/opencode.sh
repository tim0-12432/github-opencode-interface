#!/usr/bin/env bash
# lib/opencode.sh - OpenCode/AI operations

# Requires: WORK_DIR, PROMPTS_DIR, ISSUE, REPO, OPENCODE_MODEL, MAX_PHASE_ATTEMPTS

setup_opencode_config() {
    log "Configuring OpenCode for ${OPENCODE_PROVIDER:-github-copilot}..."
    
    local config_dir="/root/.config/opencode"
    mkdir -p "$config_dir"
    
    log_success "OpenCode configured"
}

_validate_prerequisites() {
    local errors=0

    if [[ -z "${ISSUE:-}" ]]; then
        if [[ "${WORKFLOW_MODE:-}" == "suggest" ]] || [[ "${SUGGEST_ONLY:-false}" == "true" ]]; then
            verbose "ISSUE not set; continuing for suggest workflow"
        elif [[ "${WORKFLOW_MODE:-}" == "review" ]]; then
            verbose "ISSUE not set; continuing for review workflow"
        else
            log_error "ISSUE is not set; cannot render prompt"
            errors=$((errors + 1))
        fi
    fi

    if [[ -z "${REPO:-}" ]]; then
        log_error "REPO is not set; cannot render prompt"
        errors=$((errors + 1))
    fi

    if [[ -z "${WORK_DIR:-}" ]]; then
        log_error "WORK_DIR is not set; cannot access repository"
        errors=$((errors + 1))
    elif [[ ! -d "${WORK_DIR}" ]]; then
        log_error "WORK_DIR does not exist: ${WORK_DIR}"
        errors=$((errors + 1))
    fi

    if [[ ! -f "/workspace/issue_context.md" ]]; then
        log_error "Issue context file not found: /workspace/issue_context.md"
        errors=$((errors + 1))
    fi

    [[ $errors -gt 0 ]] && return 1
    return 0
}

run_opencode_with_prompt() {
    local prompt_file="$1"
    local extra_context="${2:-}"
    local prompt_name=$(basename "$prompt_file" .prompt)
    
    log "Running OpenCode: ${prompt_name}..."

    if ! _validate_prerequisites; then
        return 1
    fi
    
    cd "$WORK_DIR"
    
    local prompt_content
    prompt_content=$(cat "$prompt_file")
    prompt_content="${prompt_content//\{\{ISSUE_CONTEXT\}\}/$(cat /workspace/issue_context.md)}"
    prompt_content="${prompt_content//\{\{ISSUE_NUMBER\}\}/${ISSUE:-N/A}}"
    prompt_content="${prompt_content//\{\{REPO\}\}/${REPO}}"
    prompt_content="${prompt_content//\{\{TEST_OUTPUT\}\}/$(get_test_output)}"
    prompt_content="${prompt_content//\{\{REVIEW_FEEDBACK\}\}/$(get_review_feedback)}"
    prompt_content="${prompt_content//\{\{SUGGESTED_COUNT\}\}/${SUGGESTED_ISSUES_COUNT:-3}}"
    
    if [[ -n "$extra_context" ]]; then
        prompt_content="${prompt_content}

## Additional Context
${extra_context}"
    fi
    
    local expanded_prompt="/workspace/.current_prompt.md"
    echo "$prompt_content" > "$expanded_prompt"
    
    verbose "Prompt saved to: $expanded_prompt"
    
    if cat "$expanded_prompt" | /root/.opencode/bin/opencode run --model "${OPENCODE_MODEL:-github-copilot/claude-sonnet-4.5}" 2>&1; then
        log_success "${prompt_name} completed"
        return 0
    else
        log_error "${prompt_name} failed"
        return 1
    fi
}

run_phase() {
    local phase="$1"
    local extra_context="${2:-}"
    local prompt_file="${PROMPTS_DIR}/${phase}.prompt"
    local attempt=1
    
    if [[ ! -f "$prompt_file" ]]; then
        log_warn "Prompt file not found: ${prompt_file}, skipping phase"
        return 0
    fi
    
    while [[ $attempt -le $MAX_PHASE_ATTEMPTS ]]; do
        verbose "Phase ${phase}: attempt ${attempt}/${MAX_PHASE_ATTEMPTS}"
        
        if run_opencode_with_prompt "$prompt_file" "$extra_context"; then
            return 0
        fi
        
        log_warn "Attempt ${attempt} failed, retrying..."
        attempt=$((attempt + 1))
        sleep 2
    done
    
    log_error "Phase ${phase} failed after ${MAX_PHASE_ATTEMPTS} attempts"
    return 1
}

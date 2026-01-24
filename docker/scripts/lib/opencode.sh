#!/usr/bin/env bash
# lib/opencode.sh - OpenCode/AI operations

# Requires: WORK_DIR, PROMPTS_DIR, ISSUE, REPO, OPENCODE_MODEL, MAX_PHASE_ATTEMPTS

setup_opencode_config() {
    log "Configuring OpenCode for ${OPENCODE_PROVIDER:-github-copilot}..."
    
    local config_dir="/root/.config/opencode"
    mkdir -p "$config_dir"
    
    log_success "OpenCode configured"
}

run_opencode_with_prompt() {
    local prompt_file="$1"
    local extra_context="${2:-}"
    local prompt_name=$(basename "$prompt_file" .prompt)
    
    log "Running OpenCode: ${prompt_name}..."
    
    cd "$WORK_DIR"
    
    local prompt_content
    prompt_content=$(cat "$prompt_file")
    prompt_content="${prompt_content//\{\{ISSUE_CONTEXT\}\}/$(cat /workspace/issue_context.md)}"
    prompt_content="${prompt_content//\{\{ISSUE_NUMBER\}\}/${ISSUE}}"
    prompt_content="${prompt_content//\{\{REPO\}\}/${REPO}}"
    prompt_content="${prompt_content//\{\{TEST_OUTPUT\}\}/$(get_test_output)}"
    prompt_content="${prompt_content//\{\{REVIEW_FEEDBACK\}\}/$(get_review_feedback)}"
    
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

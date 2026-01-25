#!/usr/bin/env bash
# lib/suggestions.sh - Issue suggestion generation workflow

# Requires: STATE_DIR, REPO, DRY_RUN
# Uses: run_phase, log, log_warn, log_error, log_success, save_state
# Exports: SUGGESTED_ISSUE_URLS

ensure_ai_suggested_label() {
    local label_name="ai-suggested"

    if gh label list --repo "$REPO" --json name >/dev/null 2>&1; then
        local existing_label
        existing_label=$(gh label list --repo "$REPO" --json name | jq -r '.[] | select(.name == "ai-suggested") | .name')
        if [[ "$existing_label" == "$label_name" ]]; then
            return 0
        fi
    fi

    log "Creating label: ${label_name}"
    gh label create "$label_name" \
        --repo "$REPO" \
        --color "c5def5" \
        --description "AI suggested follow-up issue" >/dev/null 2>&1 || {
        log_warn "Failed to create label ${label_name} (continuing)"
        return 0
    }
}

trim_label() {
    local value="$1"
    value="${value#"${value%%[![:space:]]*}"}"
    value="${value%"${value##*[![:space:]]}"}"
    echo "$value"
}

build_label_list() {
    local input_labels="$1"
    local labels=("ai-suggested")
    local label

    if [[ -n "$input_labels" ]]; then
        IFS=',' read -r -a input_array <<< "$input_labels"
        for label in "${input_array[@]}"; do
            label=$(trim_label "$label")
            [[ -z "$label" ]] && continue
            if [[ ! " ${labels[*]} " =~ " ${label} " ]]; then
                labels+=("$label")
            fi
        done
    fi

    local label_string
    label_string=$(IFS=','; echo "${labels[*]}")
    echo "$label_string"
}

refine_suggestion() {
    local index="$1"
    local suggestion_json="$2"
    local available_labels="$3"
    local current_suggestion_file="${STATE_DIR}/current_suggestion.json"
    local refined_issue_file="${STATE_DIR}/refined_issue.json"

    if ! printf '%s\n' "$suggestion_json" > "$current_suggestion_file"; then
        log_error "Failed to write suggestion #${index} to ${current_suggestion_file}"
        return 1
    fi

    if ! run_phase "refine-issue" "SUGGESTION_JSON: ${suggestion_json}\nAVAILABLE_LABELS: ${available_labels}"; then
        log_warn "Refine-issue phase failed for suggestion #${index}"
        return 1
    fi

    if [[ ! -s "$refined_issue_file" ]]; then
        log_warn "Refined issue output missing for suggestion #${index}"
        return 1
    fi

    verbose "Refinement complete for suggestion #${index}"
    return 0
}

suggest_issues_phase() {
    local requested_count="${SUGGESTED_ISSUES_COUNT:-0}"
    local workflow_mode="${WORKFLOW_MODE:-}"

    if [[ -z "$workflow_mode" ]] && [[ "${SUGGEST_ONLY:-false}" == "true" ]]; then
        workflow_mode="suggest"
    fi

    if [[ ! "$requested_count" =~ ^[0-9]+$ ]]; then
        log_warn "Invalid SUGGESTED_ISSUES_COUNT (${requested_count}); skipping suggestions"
        return 0
    fi

    if [[ "$requested_count" -le 0 ]]; then
        if [[ "$workflow_mode" == "suggest" ]]; then
            requested_count=3
            SUGGESTED_ISSUES_COUNT="${requested_count}"
            export SUGGESTED_ISSUES_COUNT
            log_warn "SUGGESTED_ISSUES_COUNT not set; defaulting to ${requested_count} for suggest workflow"
        else
            verbose "Suggested issue generation disabled"
            return 0
        fi
    fi

    log_phase "SUGGEST-ISSUES"

    if [[ "${DRY_RUN:-false}" == "true" ]]; then
        log_warn "Dry run - skipping suggested issue creation"
        return 0
    fi

    local available_labels
    if ! available_labels=$(gh label list --repo "$REPO" --json name | jq -r '.[].name' | paste -sd "," -); then
        log_error "Failed to list labels for ${REPO}"
        return 1
    fi

    if ! run_phase "suggest-issues" "SUGGESTED_COUNT: ${requested_count}\nAVAILABLE_LABELS: ${available_labels}"; then
        log_warn "Suggest-issues phase had issues, continuing without suggestions"
        return 0
    fi

    local suggestions_file="${STATE_DIR}/suggested_issues.json"
    if [[ ! -s "$suggestions_file" ]]; then
        log_warn "No suggestions generated (${suggestions_file} missing or empty)"
        return 0
    fi

    if ! jq -e 'type == "array"' "$suggestions_file" >/dev/null 2>&1; then
        log_warn "Invalid suggestions JSON (expected array)"
        return 0
    fi

    ensure_ai_suggested_label

    local suggestion_count
    suggestion_count=$(jq 'length' "$suggestions_file")

    if [[ "$suggestion_count" -eq 0 ]]; then
        log_warn "Suggestions list is empty"
        return 0
    fi

    local urls=()
    local index=0
    while [[ "$index" -lt "$suggestion_count" ]]; do
        local title
        local body
        local labels
        local priority
        local suggestion_json
        local current_suggestion_file="${STATE_DIR}/current_suggestion.json"
        local refined_issue_file="${STATE_DIR}/refined_issue.json"

        local skip=false

        suggestion_json=$(jq -c ".[${index}]" "$suggestions_file")
        if [[ -z "$suggestion_json" || "$suggestion_json" == "null" ]]; then
            log_warn "Skipping suggestion #${index} due to invalid JSON"
            skip=true
        fi

        if [[ "$skip" != "true" ]]; then
            if ! refine_suggestion "$index" "$suggestion_json" "$available_labels"; then
                log_warn "Skipping suggestion #${index} due to refinement failure"
                skip=true
            fi
        fi

        if [[ "$skip" != "true" ]]; then
            local create
            create=$(jq -r '.create' "$refined_issue_file" 2>/dev/null)
            if [[ "$create" != "true" ]]; then
                local reason
                reason=$(jq -r '.reason // .message // "No reason provided"' "$refined_issue_file" 2>/dev/null)
                log_warn "Suggestion #${index} skipped by refinement: ${reason}"
                skip=true
            fi
        fi

        if [[ "$skip" != "true" ]]; then
            title=$(jq -r '.title // empty' "$refined_issue_file")
            body=$(jq -r '.body // empty' "$refined_issue_file")
            labels=$(jq -r '.labels // [] | map(tostring) | join(",")' "$refined_issue_file")
            priority=$(jq -r '.priority // empty' "$refined_issue_file")

            if [[ -z "$title" || -z "$body" ]]; then
                log_warn "Skipping suggestion #${index} due to missing title/body"
                skip=true
            fi
        fi

        if [[ "$skip" != "true" ]]; then
            if [[ -n "$priority" && "$priority" != "null" ]]; then
                body="${body}

**Priority:** ${priority}"
            fi

            local suggestion_footer
            if [[ -n "${ISSUE:-}" ]]; then
                suggestion_footer="Suggested by issue-suggestor after ${REPO}#${ISSUE}."
            else
                suggestion_footer="Suggested by issue-suggestor for ${REPO}."
            fi

            body="${body}

---
${suggestion_footer}"

            local label_list
            label_list=$(build_label_list "$labels")

            local issue_url
            if [[ "${VERBOSE:-false}" == "true" ]]; then
                issue_url=$(gh issue create \
                    --repo "$REPO" \
                    --title "$title" \
                    --body "$body" \
                    --label "$label_list") || {
                    log_error "Failed to create suggested issue: ${title} (see above for details)"
                    skip=true
                }
            else
                issue_url=$(gh issue create \
                    --repo "$REPO" \
                    --title "$title" \
                    --body "$body" \
                    --label "$label_list" 2>/dev/null) || {
                    log_warn "Failed to create suggested issue: ${title} (run with --verbose for details)"
                    skip=true
                }
            fi

            if [[ "$skip" != "true" ]]; then
                urls+=("$issue_url")
                log_success "Suggested issue created: ${issue_url}"
            fi
        fi

        rm -f "$current_suggestion_file" "$refined_issue_file"
        index=$((index + 1))
    done

    if [[ ${#urls[@]} -gt 0 ]]; then
        SUGGESTED_ISSUE_URLS=$(printf "%s\n" "${urls[@]}")
        save_state "suggested_issue_urls" "$SUGGESTED_ISSUE_URLS"
    fi

    return 0
}

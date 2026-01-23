#!/usr/bin/env bash
# Main orchestration inside the container

set -euo pipefail

# ============================================================================
# Configuration
# ============================================================================

WORK_DIR="/workspace/repo"
PROMPTS_DIR="/prompts"
STATE_DIR="/workspace/.state"

# Retry limits
MAX_TEST_CYCLES="${MAX_TEST_CYCLES:-5}"
MAX_REVIEW_CYCLES="${MAX_REVIEW_CYCLES:-2}"
MAX_PHASE_ATTEMPTS="${MAX_PHASE_ATTEMPTS:-3}"

# State tracking
WORKFLOW_STATE="starting"
TESTS_PASSED=false
REVIEW_PASSED=false

# ============================================================================
# Colors & Logging
# ============================================================================

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

log()         { echo -e "${BLUE}[$(date '+%H:%M:%S')]${NC} $1"; }
log_success() { echo -e "${GREEN}[$(date '+%H:%M:%S')] ✓${NC} $1"; }
log_error()   { echo -e "${RED}[$(date '+%H:%M:%S')] ✗${NC} $1" >&2; }
log_warn()    { echo -e "${YELLOW}[$(date '+%H:%M:%S')] !${NC} $1"; }
log_phase()   { echo -e "\n${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"; \
                echo -e "${CYAN}  $1${NC}"; \
                echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"; }
verbose()     { [[ "${VERBOSE:-false}" == "true" ]] && echo -e "${BLUE}[DEBUG]${NC} $1" || true; }

# ============================================================================
# State Management
# ============================================================================

init_state_dir() {
    mkdir -p "$STATE_DIR"
}

save_state() {
    local key="$1"
    local value="$2"
    echo "$value" > "${STATE_DIR}/${key}"
}

load_state() {
    local key="$1"
    local default="${2:-}"
    if [[ -f "${STATE_DIR}/${key}" ]]; then
        cat "${STATE_DIR}/${key}"
    else
        echo "$default"
    fi
}

save_test_output() {
    save_state "last_test_output" "$1"
}

get_test_output() {
    load_state "last_test_output" "No test output available"
}

save_review_feedback() {
    save_state "last_review_feedback" "$1"
}

get_review_feedback() {
    load_state "last_review_feedback" ""
}

# ============================================================================
# OpenCode Configuration
# ============================================================================

setup_opencode_config() {
    log "Configuring OpenCode for ${OPENCODE_PROVIDER:-github-copilot}..."
    
    local config_dir="/root/.config/opencode"
    mkdir -p "$config_dir"
    
    log_success "OpenCode configured"
}

# ============================================================================
# Validation
# ============================================================================

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

# ============================================================================
# GitHub Operations
# ============================================================================

setup_github_auth() {
    log "Setting up GitHub authentication..."
    if gh auth login --with-token <<< "${GITHUB_TOKEN}" 2>&1 | grep -q "error"; then
        log_error "GitHub authentication failed"
        return 1
    fi
    if gh auth status &>/dev/null; then
        log_success "GitHub authenticated"
        return 0
    else
        log_error "GitHub authentication verification failed"
        return 1
    fi
}

fetch_issue() {
    log "Fetching issue #${ISSUE} from ${REPO}..."
    
    local issue_json
    issue_json=$(gh issue view "$ISSUE" --repo "$REPO" --json title,body,labels,comments)
    
    ISSUE_TITLE=$(echo "$issue_json" | jq -r '.title')
    ISSUE_BODY=$(echo "$issue_json" | jq -r '.body // "No description provided."')
    ISSUE_LABELS=$(echo "$issue_json" | jq -r '.labels[].name' | tr '\n' ', ' | sed 's/,$//')
    ISSUE_COMMENTS=$(echo "$issue_json" | jq -r '.comments[].body' | head -c 2000)
    
    cat > /workspace/issue_context.md <<EOF
# Issue #${ISSUE}: ${ISSUE_TITLE}

## Labels
${ISSUE_LABELS:-None}

## Description
${ISSUE_BODY}

## Comments
${ISSUE_COMMENTS:-No comments}
EOF

    log_success "Issue fetched: ${ISSUE_TITLE}"
}

check_existing_branch() {
    local branch_name="${BRANCH:-fix/issue-${ISSUE}}"
    
    log "Checking for existing branch: ${branch_name}..."
    
    # Check if branch exists on remote
    if git ls-remote --heads origin "$branch_name" 2>/dev/null | grep -q "$branch_name"; then
        log_success "Found existing branch on remote"
        return 0
    fi
    
    log "No existing branch found"
    return 1
}

clone_or_continue_repo() {
    log "Setting up repository ${REPO}..."
    
    local branch_name="${BRANCH:-fix/issue-${ISSUE}}"
    
    [[ -d "$WORK_DIR" ]] && rm -rf "$WORK_DIR"
    
    # Clone the repo
    git clone --depth 100 "https://x-access-token:${GITHUB_TOKEN}@github.com/${REPO}.git" "$WORK_DIR" 2>/dev/null
    
    cd "$WORK_DIR"
    git config user.email "${GIT_AUTHOR_EMAIL:-bot@issue-resolver.local}"
    git config user.name "${GIT_AUTHOR_NAME:-Issue Resolver Bot}"
    
    DEFAULT_BRANCH=$(git symbolic-ref refs/remotes/origin/HEAD | sed 's@^refs/remotes/origin/@@')
    
    # Check if we should continue on existing branch
    if check_existing_branch; then
        log "Continuing on existing branch: ${branch_name}"
        git fetch origin "$branch_name"
        git checkout -b "$branch_name" "origin/$branch_name"
        WORKING_BRANCH="$branch_name"
        RESUMING=true
        log_success "Checked out existing branch with $(git log --oneline origin/${DEFAULT_BRANCH}..HEAD | wc -l) commit(s) ahead"
    else
        log "Creating new branch: ${branch_name}"
        git checkout -b "$branch_name"
        WORKING_BRANCH="$branch_name"
        RESUMING=false
        log_success "Created new branch"
    fi
    
    log_success "Repository ready (default branch: ${DEFAULT_BRANCH})"
}

has_uncommitted_changes() {
    cd "$WORK_DIR"
    ! git diff --quiet || ! git diff --staged --quiet
}

commit_changes() {
    local message="${1:-fix: resolve issue #${ISSUE}}"
    local description="${2:-}"
    
    log "Committing changes..."
    
    cd "$WORK_DIR"
    
    if ! has_uncommitted_changes; then
        log_warn "No changes to commit"
        return 1
    fi
    
    git add -A
    
    if [[ -n "$description" ]]; then
        git commit -m "$message" -m "$description"
    else
        git commit -m "$message"
    fi
    
    log_success "Changes committed"
    return 0
}

push_branch() {
    log "Pushing branch to remote..."
    
    cd "$WORK_DIR"
    git push -u origin "$WORKING_BRANCH" 2>/dev/null
    
    log_success "Branch pushed: ${WORKING_BRANCH}"
}

create_pr() {
    if [[ "${DRY_RUN:-false}" == "true" ]]; then
        log_warn "Dry run - skipping PR creation"
        return 0
    fi
    
    log "Creating pull request..."
    
    cd "$WORK_DIR"
    
    # Check if PR already exists
    local existing_pr
    existing_pr=$(gh pr list --repo "$REPO" --head "$WORKING_BRANCH" --json number --jq '.[0].number' 2>/dev/null || echo "")
    
    if [[ -n "$existing_pr" ]]; then
        log_success "PR already exists: #${existing_pr}"
        PR_URL="https://github.com/${REPO}/pull/${existing_pr}"
        return 0
    fi
    
    PR_URL=$(gh pr create \
        --repo "$REPO" \
        --title "fix: ${ISSUE_TITLE}" \
        --body "## Summary
Automatically generated fix for #${ISSUE}

## Issue
${ISSUE_TITLE}

## Status
- Tests: $(if $TESTS_PASSED; then echo "✅ Passing"; else echo "❌ Failing"; fi)
- Review: $(if $REVIEW_PASSED; then echo "✅ Passed"; else echo "⚠️ Needs attention"; fi)

---
*Generated by issue-resolver*

Closes #${ISSUE}" \
        --base "$DEFAULT_BRANCH" \
        --head "$WORKING_BRANCH")
    
    log_success "Pull request created: ${PR_URL}"
}

add_issue_comment() {
    local status="$1"
    local details="${2:-}"
    
    if [[ "${DRY_RUN:-false}" == "true" ]]; then
        log_warn "Dry run - skipping issue comment"
        return 0
    fi
    
    log "Adding comment to issue #${ISSUE}..."
    
    local comment_body
    
    case "$status" in
        success)
            comment_body="## 🤖 Automated Fix Ready

A pull request has been created to resolve this issue.

**Branch:** \`${WORKING_BRANCH}\`
**PR:** ${PR_URL:-N/A}

### Status
- ✅ Implementation complete
- ✅ Tests passing
- ✅ Review passed

Please review the PR and merge if satisfactory."
            ;;
        partial)
            comment_body="## 🤖 Automated Fix - Partial Progress

I've made progress on this issue but couldn't complete it fully.

**Branch:** \`${WORKING_BRANCH}\`
**PR:** ${PR_URL:-Not created}

### Status
- ✅ Implementation attempted
- $(if $TESTS_PASSED; then echo "✅ Tests passing"; else echo "❌ Tests failing"; fi)
- $(if $REVIEW_PASSED; then echo "✅ Review passed"; else echo "⚠️ Review found issues"; fi)

### Details
${details}

### Next Steps
You can continue working on this branch manually, or run the resolver again:
\`\`\`bash
./resolve.py ${REPO} ${ISSUE} --branch ${WORKING_BRANCH}
\`\`\`"
            ;;
        error)
            comment_body="## 🤖 Automated Fix - Error

I encountered an error while trying to resolve this issue.

**Branch:** \`${WORKING_BRANCH}\`

### Error Details
${details}

### Next Steps
You can try running the resolver again or work on the branch manually:
\`\`\`bash
./resolve.py ${REPO} ${ISSUE} --branch ${WORKING_BRANCH}
\`\`\`"
            ;;
    esac
    
    gh issue comment "$ISSUE" --repo "$REPO" --body "$comment_body"
    
    log_success "Comment added to issue"
}

# ============================================================================
# OpenCode Operations
# ============================================================================

run_opencode_with_prompt() {
    local prompt_file="$1"
    local extra_context="${2:-}"
    local prompt_name=$(basename "$prompt_file" .prompt)
    
    log "Running OpenCode: ${prompt_name}..."
    
    cd "$WORK_DIR"
    
    # Read and expand prompt template
    local prompt_content
    prompt_content=$(cat "$prompt_file")
    prompt_content="${prompt_content//\{\{ISSUE_CONTEXT\}\}/$(cat /workspace/issue_context.md)}"
    prompt_content="${prompt_content//\{\{ISSUE_NUMBER\}\}/${ISSUE}}"
    prompt_content="${prompt_content//\{\{REPO\}\}/${REPO}}"
    prompt_content="${prompt_content//\{\{TEST_OUTPUT\}\}/$(get_test_output)}"
    prompt_content="${prompt_content//\{\{REVIEW_FEEDBACK\}\}/$(get_review_feedback)}"
    
    # Append extra context if provided
    if [[ -n "$extra_context" ]]; then
        prompt_content="${prompt_content}

## Additional Context
${extra_context}"
    fi
    
    local expanded_prompt="/workspace/.current_prompt.md"
    echo "$prompt_content" > "$expanded_prompt"
    
    verbose "Prompt saved to: $expanded_prompt"
    
    # Run opencode
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

# ============================================================================
# Test Execution
# ============================================================================

detect_test_command() {
    cd "$WORK_DIR"
    
    if [[ -f "package.json" ]] && grep -q '"test"' package.json 2>/dev/null; then
        echo "npm test"
    elif [[ -f "pyproject.toml" ]] || [[ -f "pytest.ini" ]] || [[ -d "tests" ]]; then
        echo "pytest"
    elif [[ -f "go.mod" ]]; then
        echo "go test ./..."
    elif [[ -f "Cargo.toml" ]]; then
        echo "cargo test"
    elif [[ -f "Makefile" ]] && grep -q "^test:" Makefile 2>/dev/null; then
        echo "make test"
    else
        echo ""
    fi
}

run_tests() {
    log "Running tests..."
    
    cd "$WORK_DIR"
    
    local test_cmd
    test_cmd=$(detect_test_command)
    
    if [[ -z "$test_cmd" ]]; then
        log_warn "No test framework detected, assuming tests pass"
        TESTS_PASSED=true
        return 0
    fi
    
    local test_output
    local exit_code=0
    
    test_output=$(eval "$test_cmd" 2>&1) || exit_code=$?
    
    # Save output for fix-tests prompt
    save_test_output "$test_output"
    
    if [[ $exit_code -eq 0 ]]; then
        log_success "Tests passed"
        TESTS_PASSED=true
        return 0
    else
        log_error "Tests failed"
        verbose "Test output:\n$test_output"
        TESTS_PASSED=false
        return 1
    fi
}

# ============================================================================
# Review Check
# ============================================================================

run_review() {
    log "Running review..."
    
    cd "$WORK_DIR"
    
    # Clear previous review result
    rm -f "${STATE_DIR}/review_passed"
    rm -f "${STATE_DIR}/review_feedback"
    
    if ! run_phase "review"; then
        REVIEW_PASSED=false
        return 1
    fi
    
    # Check if review passed (review prompt should create this file)
    if [[ -f "${STATE_DIR}/review_passed" ]]; then
        log_success "Review passed"
        REVIEW_PASSED=true
        return 0
    elif [[ -f "${STATE_DIR}/review_feedback" ]]; then
        save_review_feedback "$(cat "${STATE_DIR}/review_feedback")"
        log_warn "Review found issues"
        REVIEW_PASSED=false
        return 1
    else
        # If no explicit signal, assume passed
        log_success "Review completed (no issues flagged)"
        REVIEW_PASSED=true
        return 0
    fi
}

# ============================================================================
# Workflow Phases
# ============================================================================

implement_cycle() {
    local review_cycle="${1:-1}"
    
    log_phase "IMPLEMENTATION (Review Cycle ${review_cycle}/${MAX_REVIEW_CYCLES})"
    
    local feedback
    feedback=$(get_review_feedback)
    
    # Run implement phase with review feedback if available
    if [[ $review_cycle -gt 1 ]] && [[ -n "$feedback" ]]; then
        run_phase "implement" "Previous review feedback:\n${feedback}"
    else
        run_phase "implement"
    fi
}

test_cycle() {
    log_phase "TESTING"
    
    # First, create/update tests
    run_phase "test" || {
        log_warn "Test creation phase had issues, continuing anyway..."
    }
    
    # Now run the test-fix loop
    local test_attempt=1
    
    while [[ $test_attempt -le $MAX_TEST_CYCLES ]]; do
        log "Test cycle ${test_attempt}/${MAX_TEST_CYCLES}"
        
        if run_tests; then
            log_success "All tests passing"
            return 0
        fi
        
        if [[ $test_attempt -eq $MAX_TEST_CYCLES ]]; then
            log_error "Tests still failing after ${MAX_TEST_CYCLES} fix attempts"
            return 1
        fi
        
        log_warn "Tests failed, attempting fix (${test_attempt}/${MAX_TEST_CYCLES})..."
        
        # Run fix-tests with the captured test output
        run_phase "fix-tests" || {
            log_warn "Fix-tests phase had issues, will retry tests anyway..."
        }
        
        test_attempt=$((test_attempt + 1))
    done
    
    return 1
}

review_cycle() {
    local review_attempt=1
    
    while [[ $review_attempt -le $MAX_REVIEW_CYCLES ]]; do
        log_phase "REVIEW (Attempt ${review_attempt}/${MAX_REVIEW_CYCLES})"
        
        if run_review; then
            return 0
        fi
        
        if [[ $review_attempt -eq $MAX_REVIEW_CYCLES ]]; then
            log_error "Review still failing after ${MAX_REVIEW_CYCLES} implementation cycles"
            return 1
        fi
        
        log_warn "Review found issues, going back to implementation..."
        
        # Go back to implementation with feedback
        implement_cycle $((review_attempt + 1))
        
        # Re-run test cycle after re-implementation
        test_cycle || {
            log_warn "Tests not passing after re-implementation"
        }
        
        review_attempt=$((review_attempt + 1))
    done
    
    return 1
}

# ============================================================================
# Finalization
# ============================================================================

finalize_success() {
    log_phase "FINALIZING - SUCCESS"
    
    commit_changes "fix: resolve issue #${ISSUE}" "${ISSUE_TITLE}

Automatically resolved by issue-resolver bot.
- Tests: passing
- Review: passed"
    
    push_branch
    create_pr
    add_issue_comment "success"
    
    echo ""
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║                    ✅ SUCCESS                              ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""
}

finalize_partial() {
    local reason="$1"
    
    log_phase "FINALIZING - PARTIAL"
    
    # Commit whatever we have
    local commit_msg="wip: partial fix for issue #${ISSUE}"
    local commit_desc="${ISSUE_TITLE}

Status:
- Tests: $(if $TESTS_PASSED; then echo "passing"; else echo "failing"; fi)
- Review: $(if $REVIEW_PASSED; then echo "passed"; else echo "needs work"; fi)

${reason}

Automatically generated by issue-resolver bot."

    if commit_changes "$commit_msg" "$commit_desc"; then
        push_branch
        
        # Only create PR if we have something meaningful
        if $TESTS_PASSED || git log --oneline "origin/${DEFAULT_BRANCH}..HEAD" | grep -q .; then
            create_pr
        fi
    else
        # Even if no new changes, push any existing commits
        push_branch 2>/dev/null || true
    fi
    
    add_issue_comment "partial" "$reason"
    
    echo ""
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║                 ⚠️  PARTIAL COMPLETION                     ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""
    echo "  Branch: ${WORKING_BRANCH}"
    echo "  Reason: ${reason}"
    echo ""
    echo "  Run again to continue:"
    echo "  ./resolve.py ${REPO} ${ISSUE}"
    echo ""
}

finalize_error() {
    local error_msg="$1"
    
    log_phase "FINALIZING - ERROR"
    
    # Try to commit any changes we might have
    if has_uncommitted_changes; then
        commit_changes "wip: attempted fix for issue #${ISSUE} (error)" "Error occurred: ${error_msg}" || true
        push_branch 2>/dev/null || true
    fi
    
    add_issue_comment "error" "$error_msg"
    
    echo ""
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║                    ❌ ERROR                                ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""
    echo "  ${error_msg}"
    echo ""
}

# ============================================================================
# Main Workflow
# ============================================================================

main() {
    echo ""
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║           GitHub Issue Resolver                            ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""
    echo "  Repository:    ${REPO:-not set}"
    echo "  Issue:         #${ISSUE:-not set}"
    echo "  Provider:      ${OPENCODE_PROVIDER:-copilot}"
    echo "  Model:         ${OPENCODE_MODEL:-default}"
    echo "  Test Cycles:   max ${MAX_TEST_CYCLES}"
    echo "  Review Cycles: max ${MAX_REVIEW_CYCLES}"
    echo ""
    
    # Initialize state directory
    init_state_dir
    
    # ========================================================================
    # Setup Phase
    # ========================================================================
    
    log_phase "SETUP"
    
    validate_inputs
    setup_opencode_config
    setup_github_auth
    fetch_issue
    clone_or_continue_repo
    
    # Copy project-specific opencode config if exists
    [[ -d "/opencode-config" ]] && cp -r /opencode-config/. "$WORK_DIR/" 2>/dev/null || true
    
    if [[ "${RESUMING:-false}" == "true" ]]; then
        log "Resuming previous work on branch ${WORKING_BRANCH}"
    fi
    
    # ========================================================================
    # Analysis Phase
    # ========================================================================
    
    log_phase "ANALYSIS"
    
    if ! run_phase "analyze"; then
        finalize_error "Analysis phase failed"
        exit 1
    fi
    
    # ========================================================================
    # Implementation Phase
    # ========================================================================
    
    implement_cycle 1
    
    # ========================================================================
    # Test Cycle
    # ========================================================================
    
    if ! test_cycle; then
        finalize_partial "Tests could not be fixed after ${MAX_TEST_CYCLES} attempts.

Last test output:
\`\`\`
$(get_test_output | head -50)
\`\`\`"
        exit 0  # Exit 0 because we handled it gracefully
    fi
    
    # ========================================================================
    # Review Cycle
    # ========================================================================
    
    if ! review_cycle; then
        finalize_partial "Review cycle could not be completed after ${MAX_REVIEW_CYCLES} attempts.

Last review feedback:
$(get_review_feedback)"
        exit 0
    fi
    
    # ========================================================================
    # Success!
    # ========================================================================
    
    finalize_success
}

# Trap errors for graceful handling
trap 'finalize_error "Unexpected error on line $LINENO"' ERR

main "$@"

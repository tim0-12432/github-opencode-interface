#!/usr/bin/env bash
# orchestrator.sh - Main entry point
# This is the slim orchestrator that sources modular components

set -euo pipefail

# ============================================================================
# Configuration
# ============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LIB_DIR="${SCRIPT_DIR}/lib"

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
# Source Modules
# ============================================================================

source "${LIB_DIR}/colors.sh"
source "${LIB_DIR}/state.sh"
source "${LIB_DIR}/validate.sh"
source "${LIB_DIR}/github.sh"
source "${LIB_DIR}/opencode.sh"
source "${LIB_DIR}/testing.sh"
source "${LIB_DIR}/workflow.sh"
source "${LIB_DIR}/finalize.sh"

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
        exit 0
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

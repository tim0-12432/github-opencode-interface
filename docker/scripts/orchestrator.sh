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
SUGGESTED_ISSUES_COUNT="${SUGGESTED_ISSUES_COUNT:-0}"

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
source "${LIB_DIR}/suggestions.sh"
source "${LIB_DIR}/setup.sh"
source "${LIB_DIR}/workflows/resolve.sh"
source "${LIB_DIR}/workflows/suggest.sh"
source "${LIB_DIR}/workflows/review.sh"

# ==========================================================================
# Export Configuration
# ==========================================================================

export WORK_DIR
export PROMPTS_DIR
export STATE_DIR
export MAX_TEST_CYCLES
export MAX_REVIEW_CYCLES
export MAX_PHASE_ATTEMPTS
export SUGGESTED_ISSUES_COUNT

# ============================================================================
# Main Workflow
# ============================================================================

main() {
    workflow_dispatch
}

# Trap errors for graceful handling
trap 'finalize_error "Unexpected error on line $LINENO"' ERR

main "$@"

#!/usr/bin/env bash
# lib/workflows/resolve.sh - Resolve workflow

run_workflow_resolve() {
    log_phase "SETUP"

    setup_resolve

    if [[ "${RESUMING:-false}" == "true" ]]; then
        log "Resuming previous work on branch ${WORKING_BRANCH}"
    fi

    log_phase "ANALYSIS"

    if ! run_phase "analyze"; then
        finalize_error "Analysis phase failed"
        exit 1
    fi

    implement_cycle 1

    if ! test_cycle; then
        finalize_partial "Tests could not be fixed after ${MAX_TEST_CYCLES} attempts.

Last test output:
\`\`\`
$(get_test_output | head -50)
\`\`\`"
        exit 0
    fi

    if ! review_cycle; then
        finalize_partial "Review cycle could not be completed after ${MAX_REVIEW_CYCLES} attempts.

Last review feedback:
$(get_review_feedback)"
        exit 0
    fi

    finalize_success "true"
    finalize_success_report
}

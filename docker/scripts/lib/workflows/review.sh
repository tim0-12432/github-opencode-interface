#!/usr/bin/env bash
# lib/workflows/review.sh - Review workflow

run_workflow_review() {
    log_phase "SETUP"

    setup_review

    if [[ "${RESUMING:-false}" == "true" ]]; then
        log "Resuming previous work on branch ${WORKING_BRANCH}"
    fi

    log_phase "REVIEWING"

    if ! run_phase "security-report"; then
        finalize_error "Security Evaluation phase failed"
        exit 1
    fi

    if ! run_phase "architecture-report"; then
        finalize_error "Architecture Evaluation phase failed"
        exit 1
    fi

    if ! run_phase "customer-report"; then
        finalize_error "Customer Evaluation phase failed"
        exit 1
    fi

    if ! run_phase "engineering-report"; then
        finalize_error "Engineering Evaluation phase failed"
        exit 1
    fi

    if ! run_phase "testing-report"; then
        finalize_error "Testing Evaluation phase failed"
        exit 1
    fi

    if ! run_phase "resource-report"; then
        finalize_error "Resource Evaluation phase failed"
        exit 1
    fi

    log_phase "AGGREGATING REPORT"

    cleanup_state

    local review_contents="SECURITY REPORT:\n$(get_review_report 'security')\n\nARCHITECTURE REPORT:\n$(get_review_report 'architecture')\n\nCUSTOMER REPORT:\n$(get_review_report 'customer')\n\nENGINEERING REPORT:\n$(get_review_report 'engineering')\n\nTESTING REPORT:\n$(get_review_report 'testing')\n\nRESOURCE REPORT:\n$(get_review_report 'resource')\n"
    if ! run_phase "report-aggregation" "${review_contents:-}"; then
        finalize_error "Aggregation phase failed"
        exit 1
    fi

    finalize_review_report "true"
    finalize_success_report
}

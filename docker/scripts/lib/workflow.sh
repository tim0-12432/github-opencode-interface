#!/usr/bin/env bash
# lib/workflow.sh - Workflow phases

# Requires: MAX_TEST_CYCLES, MAX_REVIEW_CYCLES, STATE_DIR, WORK_DIR
# Uses: run_phase, run_tests, get_test_output, get_review_feedback, save_review_feedback
# Exports: TESTS_PASSED, REVIEW_PASSED

implement_cycle() {
    local review_cycle="${1:-1}"
    
    log_phase "IMPLEMENTATION (Review Cycle ${review_cycle}/${MAX_REVIEW_CYCLES})"
    
    local feedback
    feedback=$(get_review_feedback)
    
    if [[ $review_cycle -gt 1 ]] && [[ -n "$feedback" ]]; then
        run_phase "implement" "Previous review feedback:\n${feedback}"
    else
        run_phase "implement"
    fi
}

test_cycle() {
    log_phase "TESTING"
    
    run_phase "test" || {
        log_warn "Test creation phase had issues, continuing anyway..."
    }
    
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
        
        run_phase "fix-tests" || {
            log_warn "Fix-tests phase had issues, will retry tests anyway..."
        }
        
        test_attempt=$((test_attempt + 1))
    done
    
    return 1
}

run_review() {
    log "Running review..."
    
    cd "$WORK_DIR"
    
    rm -f "${STATE_DIR}/review_passed"
    rm -f "${STATE_DIR}/review_feedback"
    
    if ! run_phase "review"; then
        REVIEW_PASSED=false
        return 1
    fi
    
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
        log_success "Review completed (no issues flagged)"
        REVIEW_PASSED=true
        return 0
    fi
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
        
        implement_cycle $((review_attempt + 1))
        
        test_cycle || {
            log_warn "Tests not passing after re-implementation"
        }
        
        review_attempt=$((review_attempt + 1))
    done
    
    return 1
}

#!/usr/bin/env bash
# lib/testing.sh - Test detection and execution

# Requires: WORK_DIR
# Exports: TESTS_PASSED

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

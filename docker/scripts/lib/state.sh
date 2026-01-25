#!/usr/bin/env bash
# lib/state.sh - State management functions

# Requires: STATE_DIR to be set

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

get_review_report() {
    local file_name="${1}_review_report"
    load_state "$file_name" "No review report available"
}

cleanup_state() {
    for file in "${STATE_DIR}"/*.*; do
        local basename=$(basename "$file" | cut -d. -f1)
        mv -- "$file" "${STATE_DIR}/${basename}"
    done
    verbose "Cleaned up state files"
}

#!/usr/bin/env bash
# lib/workflows/suggest.sh - Suggest workflow

run_workflow_suggest() {
    log_phase "SETUP"

    setup_suggest

    log_phase "SUGGEST"

    suggest_issues_phase
    suggest_workflow_report
}

suggest_workflow_report() {
    echo ""
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║                 💡 SUGGESTIONS COMPLETE                    ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""
    echo "  Repository: ${REPO}"
    if [[ -n "${ISSUE:-}" ]]; then
        echo "  Source:     #${ISSUE}"
    else
        echo "  Source:     None"
    fi
    if [[ -n "${SUGGESTED_ISSUE_URLS:-}" ]]; then
        echo "  Suggestions:"
        echo "${SUGGESTED_ISSUE_URLS}" | sed 's/^/   - /'
    else
        echo "  Suggestions: None"
    fi
    echo ""
}

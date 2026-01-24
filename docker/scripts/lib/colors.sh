#!/usr/bin/env bash
# lib/colors.sh - Colors and logging utilities

# Colors
export RED='\033[0;31m'
export GREEN='\033[0;32m'
export YELLOW='\033[0;33m'
export BLUE='\033[0;34m'
export CYAN='\033[0;36m'
export NC='\033[0m'

log()         { echo -e "${BLUE}[$(date '+%H:%M:%S')]${NC} $1"; }
log_success() { echo -e "${GREEN}[$(date '+%H:%M:%S')] ✓${NC} $1"; }
log_error()   { echo -e "${RED}[$(date '+%H:%M:%S')] ✗${NC} $1" >&2; }
log_warn()    { echo -e "${YELLOW}[$(date '+%H:%M:%S')] !${NC} $1"; }

log_phase() {
    echo -e "\n${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}  $1${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
}

verbose() {
    [[ "${VERBOSE:-false}" == "true" ]] && echo -e "${BLUE}[DEBUG]${NC} $1" || true
}

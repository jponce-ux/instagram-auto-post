#!/usr/bin/env bash
#=========================================================================
# auto-commit.sh — Spec Kit Git Auto-Commit Hook (Bash)
#
# Usage: .specify/extensions/git/scripts/bash/auto-commit.sh <event_name>
#
# Example: .specify/extensions/git/scripts/bash/auto-commit.sh after_specify
#
# Reads .specify/extensions/git/git-config.yml to determine if
# auto-commit is enabled for the given event. Falls back to
# auto_commit.default if no event-specific config exists.
#=========================================================================

set -euo pipefail

EVENT_NAME="${1:-}"

if [ -z "$EVENT_NAME" ]; then
    echo "  ⚠ Usage: $0 <event_name>"
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../../../.." && pwd)"
CONFIG_PATH="$PROJECT_ROOT/.specify/extensions/git/git-config.yml"

# ---------- Helper: get YAML value for a dotted key ----------
get_yaml_value() {
    local config_file="$1"
    shift
    local keys=("$@")
    
    # Build a grep pattern like: ^  key1:\n    key2:\n      key3:\s+(.*)$
    local pattern=""
    local indent=""
    for key in "${keys[@]}"; do
        pattern+="${indent}${key}:"
        indent=$'\n'"${indent}  "
    done
    # Remove trailing newline+indent and add value capture
    pattern="${pattern%$'\n'*}:\s*(.*)$"
    
    # Use grep + sed to extract value
    # We need to handle multi-line YAML structure
    local value
    value=$(grep -A "${#keys[@]}" "^${keys[0]}:" "$config_file" 2>/dev/null | \
            head -n "$(( ${#keys[@]} * 2 ))" | \
            grep -E "^[[:space:]]*${keys[-1]}:[[:space:]]+" | \
            sed -E 's/^[[:space:]]*[^:]+:[[:space:]]*//' | \
            head -1)
    echo "$value"
}

# ---------- Check prerequisites ----------
if [ ! -f "$CONFIG_PATH" ]; then
    echo "  ⚠ Git config not found at $CONFIG_PATH. Skipping auto-commit."
    exit 0
fi

if ! command -v git &>/dev/null; then
    echo "  ⚠ Git is not installed or not in PATH. Skipping auto-commit."
    exit 0
fi

if ! git rev-parse --git-dir &>/dev/null; then
    echo "  ⚠ Not a git repository. Skipping auto-commit."
    exit 0
fi

# ---------- Parse config ----------
# Get event-specific enabled flag
ENABLED=$(awk -v event="$EVENT_NAME" '
    /^auto_commit:/ { in_auto = 1; next }
    in_auto && /^  default:/ { default_val = $2; next }
    in_auto && $0 ~ "^  " event ":" { in_event = 1; next }
    in_event && /^    enabled:/ { enabled_val = $2; in_event = 0; next }
    in_auto && /^  [a-z]/ { in_event = 0 }
    END {
        if (enabled_val != "") print enabled_val
        else if (default_val != "") print default_val
        else print "false"
    }
' "$CONFIG_PATH" 2>/dev/null || echo "false")

if [ "$ENABLED" != "true" ]; then
    echo "  ℹ Auto-commit disabled for '$EVENT_NAME'. Skipping."
    exit 0
fi

# Get commit message
COMMIT_MSG=$(awk -v event="$EVENT_NAME" '
    /^auto_commit:/ { in_auto = 1; next }
    in_auto && $0 ~ "^  " event ":" { in_event = 1; next }
    in_event && /^    message:/ { 
        sub(/^[[:space:]]*message:[[:space:]]*/, "")
        gsub(/^["\x27]|["\x27]$/, "")
        print
        exit
    }
' "$CONFIG_PATH" 2>/dev/null)

if [ -z "$COMMIT_MSG" ]; then
    COMMIT_MSG="[Spec Kit] Auto-commit after $EVENT_NAME"
fi

# ---------- Check for changes ----------
if [ -z "$(git status --porcelain 2>/dev/null)" ]; then
    echo "  ℹ No changes to commit after '$EVENT_NAME'."
    exit 0
fi

# ---------- Stage and commit ----------
echo "  ✔ Auto-commit enabled for '$EVENT_NAME' — committing changes..."
git add .
git commit -m "$COMMIT_MSG"

if [ $? -eq 0 ]; then
    echo "  ✔ Committed: $COMMIT_MSG"
else
    echo "  ⚠ Git commit failed."
fi

exit $?

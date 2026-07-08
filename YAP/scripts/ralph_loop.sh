#!/usr/bin/env bash
# Run a Docs/Plans/<folder> step-by-step: each step-N-*.md is executed by a
# fresh `claude` session, verified via its own Verify section, then the next
# step runs. Stops on the first failure (or your "no") so you can fix and resume.
#
# Designed to consume the output of the YAP skill (Docs/Plans/<name>/ with
# context.md + step_<n>_*.md files).
#
# Usage:
#   ralph_loop.sh <plan-folder> [--from <n>] [--model <model>] [--effort <level>] [--headless]
#
# Run it from inside the git repo whose plan you want to execute — the repo
# root is taken from your current directory's git toplevel.
#
# <plan-folder> must contain context.md + one or more step-<n>-*.md files.
# --from <n> skips steps numbered below n (for resuming after a fix).
# --model/--effort are passed straight through to `claude` (see `claude --help`
# for accepted values, e.g. --model sonnet, --effort high).
#
# Default is supervised: each step runs as a real interactive `claude` session,
# so any action the auto-mode classifier escalates shows you a real approval
# prompt instead of aborting. No structured pass/fail signal in that mode
# (interactive sessions don't emit one) — you exit the session yourself
# (/exit) and the script then asks you to confirm the step succeeded.
#
# --headless switches to the old fully-unattended mode: headless `claude -p`
# with a forced JSON status/summary the script parses itself. Faster and
# hands-off, but any escalated action just aborts the session — no chance to
# approve it.
#
# Requires: claude CLI, jq.

set -euo pipefail

DEFAULT_MODEL="sonnet"
DEFAULT_EFFORT="high"

# Directory this script lives in (so ralph_format.jq is found wherever the
# skill is installed), and the git repo the plan belongs to (from your CWD).
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(git rev-parse --show-toplevel)"

usage() {
    echo "Usage: $(basename "$0") <plan-folder> [--from <n>] [--model <model>] [--effort <level>] [--headless]" >&2
    exit 1
}

[ $# -ge 1 ] || usage
plan_dir="$1"; shift
from_n=1
model="$DEFAULT_MODEL"
effort="$DEFAULT_EFFORT"
supervised=true
while [ $# -gt 0 ]; do
    case "$1" in
        --from) from_n="$2"; shift 2 ;;
        --model) model="$2"; shift 2 ;;
        --effort) effort="$2"; shift 2 ;;
        --headless) supervised=false; shift ;;
        *) usage ;;
    esac
done
claude_extra_args=(--model "$model" --effort "$effort")

case "$plan_dir" in
    /*) : ;;
    *) plan_dir="$repo_root/$plan_dir" ;;
esac
[ -d "$plan_dir" ] || { echo "Not a directory: $plan_dir" >&2; exit 1; }

logs_dir="$plan_dir/logs"
mkdir -p "$logs_dir"

schema='{"type":"object","properties":{"status":{"enum":["success","failure"]},"summary":{"type":"string"}},"required":["status","summary"]}'

# ponytail: last .type=="result" line only; good enough for a single claude -p call's output
call_claude() {
    local prompt="$1" log="$2"
    (cd "$repo_root" && claude -p "$prompt" \
        --permission-mode auto \
        --output-format stream-json \
        --verbose \
        --json-schema "$schema" \
        "${claude_extra_args[@]}") | tee "$log" | jq --unbuffered -r -f "$script_dir/ralph_format.jq"
    local exit_code=${PIPESTATUS[0]}

    local last_result
    last_result="$(jq -c 'select(.type=="result")' "$log" | tail -1)"

    if [ "$exit_code" -ne 0 ] || [ -z "$last_result" ]; then
        echo "FAILED (session error, exit $exit_code) — see $log"
        return 1
    fi

    local verdict summary
    verdict="$(jq -r 'if .subtype=="success" and .structured_output.status=="success" then "success" else "failure" end' <<<"$last_result")"
    summary="$(jq -r '.structured_output.summary // .result // "no summary reported"' <<<"$last_result")"
    echo "$verdict — $summary"
    [ "$verdict" = "success" ]
}

# Real interactive session: no -p, so the auto-mode classifier can actually
# prompt you (y/n) instead of aborting on escalation. No structured result to
# parse, so you confirm success yourself once you exit the session.
call_claude_supervised() {
    local prompt="$1"
    (cd "$repo_root" && claude "$prompt" --permission-mode auto "${claude_extra_args[@]}")
    echo
    local ans
    read -r -p "Mark this step successful and continue? [y/N] " ans
    [ "$ans" = "y" ] || [ "$ans" = "Y" ]
}

run_one() {
    local prompt="$1" log="$2"
    if [ "$supervised" = true ]; then
        call_claude_supervised "$prompt"
    else
        call_claude "$prompt" "$log"
    fi
}

step_files=()
while IFS= read -r f; do
    step_files+=("$f")
done < <(find "$plan_dir" -maxdepth 1 \( -name 'step-*.md' -o -name 'step_*.md' \) | sort -V)

[ ${#step_files[@]} -gt 0 ] || { echo "No step-*.md files found in $plan_dir" >&2; exit 1; }

echo "Found ${#step_files[@]} step(s):"
for f in "${step_files[@]}"; do echo "  - $(basename "$f")"; done
echo

for f in "${step_files[@]}"; do
    base="$(basename "$f")"
    num="$(echo "$base" | sed -E 's/^step[-_]([0-9]+)[-_].*/\1/')"
    if [ "$num" -lt "$from_n" ] 2>/dev/null; then
        echo "Skipping $base (before --from $from_n)"
        continue
    fi

    rel="${f#$repo_root/}"
    log="$logs_dir/$(basename "$f" .md).jsonl"
    prompt="Execute the plan step described in $rel. It links to context.md in the same folder for shared background — read that first. Follow the step's Fix section, then run its Verify section to confirm the fix actually works. Report status via the required schema: status=\"success\" only if Verify passed; otherwise \"failure\" with the reason in summary."

    echo "=== Step $num: $base ==="
    if ! run_one "$prompt" "$log"; then
        echo
        echo "Stopping — step $num failed. Fix it, then resume with:"
        echo "  $(basename "$0") \"${plan_dir#$repo_root/}\" --from $num ${claude_extra_args[*]:-}"
        exit 1
    fi

    git -C "$repo_root" add -A
    if git -C "$repo_root" diff --cached --quiet; then
        echo "No changes to commit for step $num"
    else
        slug="$(echo "$base" | sed -E 's/^step[-_][0-9]+[-_]//')"
        git -C "$repo_root" commit -q -m "$(basename "$plan_dir"): step $num — ${slug%.md}"
        echo "Committed step $num"
    fi
    echo
done

context_file="$plan_dir/context.md"
if [ -f "$context_file" ] && grep -q "End-to-end verification" "$context_file"; then
    rel_context="${context_file#$repo_root/}"
    log="$logs_dir/end-to-end-verification.jsonl"
    prompt="Run the \"End-to-end verification\" section from $rel_context. Report status via the required schema: success only if every check in that section passes."

    echo "=== Final: end-to-end verification ==="
    if ! run_one "$prompt" "$log"; then
        echo
        echo "All steps succeeded, but end-to-end verification failed — see $log"
        exit 1
    fi
    echo
fi

echo "All steps + end-to-end verification complete."

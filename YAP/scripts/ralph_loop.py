#!/usr/bin/env python3
"""Run a Docs/Plans/<folder> step-by-step: each step-N-*.md is executed by a
fresh `claude` session, verified via its own Verification section, then the
next step runs. Stops on the first failure (or your "no") so you can fix and
resume.

Designed to consume the output of the YAP skill (Docs/Plans/<name>/ with
context.md + step_<n>_*.md files).

Usage:
    ralph_loop.py <plan-folder> [--from <n>] [--model <model>] [--effort <level>] [--headless]

Run it from inside the git repo whose plan you want to execute -- the repo root
is taken from your current directory's git toplevel.

<plan-folder> must contain context.md + one or more step-<n>-*.md files.
--from <n> skips steps numbered below n (for resuming after a fix).
--model/--effort are passed straight through to `claude` (see `claude --help`
for accepted values, e.g. --model sonnet, --effort high).

Default is supervised: each step runs as a real interactive `claude` session,
so any action the auto-mode classifier escalates shows you a real approval
prompt instead of aborting. No structured pass/fail signal in that mode
(interactive sessions don't emit one) -- you exit the session yourself
(/exit) and the script then asks you to confirm the step succeeded.

--headless switches to the fully-unattended mode: headless `claude -p` run
inside a Docker sandbox (`docker sandbox run claude`, needs Docker Desktop
4.50+) so a runaway agent can only touch the mounted repo, not your home
dir, SSH keys, or system files. Runs with `--permission-mode acceptEdits`
(auto-accepts edits so the loop doesn't stall) and parses a forced JSON
status/summary itself. If a step reports the whole plan is already done it
emits `<promise>COMPLETE</promise>` and the loop stops early, skipping any
remaining steps. Note: a sandbox mounts only the repo, so your global
AGENTS.md and user-level skills won't load (project skills in the repo do).

Cross-platform (macOS / Linux / Windows). Requires: Python 3.8+ and the
`claude` CLI. Stdlib only -- no jq (the stream-json formatting is reimplemented
in format_stream_event below).
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

DEFAULT_MODEL = "sonnet"
DEFAULT_EFFORT = "high"

# Sigil a headless step emits when the whole plan is already complete — stops the
# loop early. Borrowed from the Ralph loop (ghuntley.com/ralph).
COMPLETE_SIGIL = "<promise>COMPLETE</promise>"

SCHEMA = {
    "type": "object",
    "properties": {
        "status": {"enum": ["success", "failure"]},
        "summary": {"type": "string"},
    },
    "required": ["status", "summary"],
}


def clip(s, n):
    return s if len(s) <= n else s[:n] + "…"


def firstlines(s, n):
    lines = s.split("\n")
    if len(lines) > n:
        return "\n".join(lines[:n]) + "\n  …"
    return s


# ponytail: naive line/char clipping, not secret-aware -- don't rely on this to hide sensitive output
def format_stream_event(event):
    """Turn one stream-json event into 0+ display lines."""
    outputs = []
    etype = event.get("type")

    if etype == "assistant":
        for item in (event.get("message") or {}).get("content") or []:
            itype = item.get("type")
            if itype == "text":
                outputs.append(item.get("text", ""))
            elif itype == "tool_use":
                inp = item.get("input") or {}
                value = inp.get("command") or inp.get("file_path") or inp.get("pattern") or json.dumps(inp, separators=(",", ":"))
                outputs.append(f"→ {item.get('name')}: {clip(str(value), 200)}")

    elif etype == "user":
        for item in (event.get("message") or {}).get("content") or []:
            if not isinstance(item, dict) or item.get("type") != "tool_result":
                continue
            content = item.get("content")
            if isinstance(content, list):
                joined = "\n".join(c.get("text", str(c)) if isinstance(c, dict) else str(c) for c in content)
            else:
                joined = str(content)
            outputs.append("  " + firstlines(joined, 3))

    elif etype == "result":
        status = "FAILED" if event.get("is_error") else "done"
        summary = (event.get("structured_output") or {}).get("summary") or event.get("result") or ""
        outputs.append(f"── {status}: {summary}")

    return outputs


def call_claude(prompt, log_path, repo_root, claude_extra_args):
    """Headless -p call inside a Docker sandbox: stream-json piped through
    format_stream_event, tee'd to log_path. Returns (ok, plan_complete)."""
    cmd = [
        "docker", "sandbox", "run",
        "claude", "-p", prompt,
        "--permission-mode", "acceptEdits",
        "--output-format", "stream-json",
        "--verbose",
        "--json-schema", json.dumps(SCHEMA),
        *claude_extra_args,
    ]
    proc = subprocess.Popen(cmd, cwd=repo_root, stdout=subprocess.PIPE, text=True, bufsize=1)
    assert proc.stdout is not None  # stdout=PIPE guarantees this; narrows for the type checker
    events = []
    saw_complete = False
    with open(log_path, "w") as log_f:
        for line in proc.stdout:
            log_f.write(line)
            line = line.strip()
            if not line:
                continue
            if COMPLETE_SIGIL in line:
                saw_complete = True
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            events.append(event)
            for out in format_stream_event(event):
                print(out)
    exit_code = proc.wait()

    results = [e for e in events if e.get("type") == "result"]
    last_result = results[-1] if results else None

    if exit_code != 0 or last_result is None:
        print(f"FAILED (session error, exit {exit_code}) — see {log_path}")
        return False, saw_complete

    structured = last_result.get("structured_output") or {}
    verdict = "success" if last_result.get("subtype") == "success" and structured.get("status") == "success" else "failure"
    summary = structured.get("summary") or last_result.get("result") or "no summary reported"
    print(f"{verdict} — {summary}")
    return verdict == "success", saw_complete


def call_claude_supervised(prompt, repo_root, claude_extra_args):
    """Real interactive session: no -p, so the auto-mode classifier can actually
    prompt you (y/n) instead of aborting on escalation. No structured result to
    parse, so you confirm success yourself once you exit the session."""
    subprocess.run(["claude", prompt, "--permission-mode", "auto", *claude_extra_args], cwd=repo_root)
    print()
    ans = input("Mark this step successful and continue? [y/N] ")
    return ans in ("y", "Y"), False  # interactive mode has no completion sigil


def run_one(prompt, log_path, repo_root, claude_extra_args, supervised):
    """Returns (ok, plan_complete)."""
    if supervised:
        return call_claude_supervised(prompt, repo_root, claude_extra_args)
    return call_claude(prompt, log_path, repo_root, claude_extra_args)


def check_docker_sandbox():
    """Exit with a clear message if `docker sandbox` isn't available."""
    try:
        proc = subprocess.run(
            ["docker", "sandbox", "--help"],
            capture_output=True, text=True,
        )
    except FileNotFoundError:
        print("--headless needs Docker: `docker` not found. Install Docker Desktop 4.50+.", file=sys.stderr)
        sys.exit(1)
    if proc.returncode != 0:
        print("--headless needs `docker sandbox` (Docker Desktop 4.50+); it isn't available.", file=sys.stderr)
        sys.exit(1)


def find_step_files(plan_dir):
    files = list(plan_dir.glob("step-*.md")) + list(plan_dir.glob("step_*.md"))
    numbered = []
    for f in files:
        m = re.match(r"^step[-_](\d+)[-_]", f.name)
        if not m:
            print(f"Skipping {f.name}: doesn't match step-<n>-*.md", file=sys.stderr)
            continue
        numbered.append((int(m.group(1)), f))
    numbered.sort(key=lambda pair: pair[0])
    return numbered


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("plan_dir")
    parser.add_argument("--from", dest="from_n", type=int, default=1)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--effort", default=DEFAULT_EFFORT)
    parser.add_argument("--headless", action="store_true")
    args = parser.parse_args()

    try:
        toplevel = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
    except subprocess.CalledProcessError:
        print("Not inside a git repository (run this from the repo whose plan you want to execute).", file=sys.stderr)
        sys.exit(1)
    repo_root = Path(toplevel)

    claude_extra_args = ["--model", args.model, "--effort", args.effort]
    supervised = not args.headless
    if not supervised:
        check_docker_sandbox()

    plan_dir = Path(args.plan_dir)
    if not plan_dir.is_absolute():
        plan_dir = repo_root / plan_dir
    if not plan_dir.is_dir():
        print(f"Not a directory: {plan_dir}", file=sys.stderr)
        sys.exit(1)

    logs_dir = plan_dir / "logs"
    logs_dir.mkdir(exist_ok=True)

    step_files = find_step_files(plan_dir)
    if not step_files:
        print(f"No step-*.md files found in {plan_dir}", file=sys.stderr)
        sys.exit(1)

    print(f"Found {len(step_files)} step(s):")
    for _, f in step_files:
        print(f"  - {f.name}")
    print()

    for num, f in step_files:
        base = f.name
        if num < args.from_n:
            print(f"Skipping {base} (before --from {args.from_n})")
            continue

        rel = f.relative_to(repo_root)
        log = logs_dir / f"{f.stem}.jsonl"
        prompt = (
            f"Execute the plan step described in {rel}. It links to context.md in the same folder "
            "for shared background — read that first. Carry out the step's Actions section, then run its "
            "Verification section to confirm the step actually works. Report status via the required schema: "
            'status="success" only if Verification passed; otherwise "failure" with the reason in summary.'
        )
        if not supervised:
            prompt += (
                f" If, after this step, the entire plan is already complete and no further steps "
                f"are needed, output {COMPLETE_SIGIL}."
            )

        print(f"=== Step {num}: {base} ===")
        ok, plan_complete = run_one(prompt, log, repo_root, claude_extra_args, supervised)
        if not ok:
            print()
            print(f"Stopping — step {num} failed. Fix it, then resume with:")
            script_name = Path(sys.argv[0]).name
            print(f"  {script_name} \"{plan_dir.relative_to(repo_root)}\" --from {num} {' '.join(claude_extra_args)}")
            sys.exit(1)

        subprocess.run(["git", "-C", str(repo_root), "add", "-A"])
        diff = subprocess.run(["git", "-C", str(repo_root), "diff", "--cached", "--quiet"])
        if diff.returncode == 0:
            print(f"No changes to commit for step {num}")
        else:
            slug = re.sub(r"^step[-_]\d+[-_]", "", base)
            slug = re.sub(r"\.md$", "", slug)
            subprocess.run(["git", "-C", str(repo_root), "commit", "-q", "-m", f"{plan_dir.name}: step {num} — {slug}"])
            print(f"Committed step {num}")
        print()

        if plan_complete:
            print(f"Step {num} reported the plan complete ({COMPLETE_SIGIL}) — skipping remaining steps.")
            print()
            break

    context_file = plan_dir / "context.md"
    if context_file.is_file() and "End-to-end verification" in context_file.read_text():
        rel_context = context_file.relative_to(repo_root)
        log = logs_dir / "end-to-end-verification.jsonl"
        prompt = (
            f'Run the "End-to-end verification" section from {rel_context}. Report status via the '
            "required schema: success only if every check in that section passes."
        )

        print("=== Final: end-to-end verification ===")
        ok, _ = run_one(prompt, log, repo_root, claude_extra_args, supervised)
        if not ok:
            print()
            print(f"All steps succeeded, but end-to-end verification failed — see {log}")
            sys.exit(1)
        print()

    print("All steps + end-to-end verification complete.")


if __name__ == "__main__":
    main()

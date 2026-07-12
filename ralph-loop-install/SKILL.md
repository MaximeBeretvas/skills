---
name: ralph-loop-install
description: >
  Copy this skill's bundled ralph_loop.py into a target project and wire up
  a `just` recipe to run it. Trigger on requests like "install the ralph
  loop in <path>", "vendor the ralph loop", or "install ralph loop" with no
  path given.
---

# Ralph loop install

Vendors `ralph_loop.py` (bundled with this skill; designed to run plans
produced by the YAP skill) into the current repo so it can be run and
committed without depending on the skill install path.

## Steps

1. **Resolve the target location.** Use the path the user named. If none was
   given, default to `scripts/` at the repo root. *Done when:* you have one
   target directory.

2. **Locate the source `ralph_loop.py`.** It ships alongside this SKILL.md,
   at `scripts/ralph_loop.py`. If it's missing there, search the known
   candidate install paths (checking both project and home-relative forms):
   - `.claude/skills/ralph-loop-install/scripts/ralph_loop.py`
   - `~/.claude/skills/ralph-loop-install/scripts/ralph_loop.py`
   - `~/.cursor/skills/ralph-loop-install/scripts/ralph_loop.py`
   - any other `*/ralph-loop-install/scripts/ralph_loop.py` reachable from
     the repo root or home directory

   If none are found, ask the user for the path. If more than one match is
   found, ask which one to use. *Done when:* you have exactly one source
   file.

3. **Copy it.** `mkdir -p <target>` then copy `ralph_loop.py` into it,
   preserving permissions. *Done when:* the file exists at
   `<target>/ralph_loop.py`.

4. **Wire up the `just` recipe**, at the repo root's `justfile`:
   - No `justfile` exists → create one containing just the ralph recipe
     below.
   - `justfile` exists, no `ralph` recipe in it → append the recipe below.
   - `justfile` exists and already has a `ralph` recipe → ask the user
     before overwriting it. Never overwrite silently.

   Recipe (point the script path at wherever it landed in step 3):

   ```just
   # Run a YAP plan folder step-by-step via the ralph loop
   ralph plan *args:
       python3 <target>/ralph_loop.py {{plan}} {{args}}
   ```

   *Done when:* the `justfile` at the repo root has a `ralph` recipe
   pointing at the copied script, or the user has declined an overwrite.

5. **Report** the copied path and the justfile change (or the decline). Stop
   — do not run the loop or touch any plan folders.

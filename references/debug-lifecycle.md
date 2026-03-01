# Debug Code Lifecycle Reference

How to manage temporary debug instrumentation throughout the development cycle: marking, tracking, pre-commit protection, and promoting valuable logs to permanent.

---

## The Core Problem

Debug logging added during a bug investigation is useful in the moment but becomes noise (or a security risk) in production. Without a system, it either:
- Gets committed accidentally, polluting production logs or leaking sensitive data
- Gets left behind and ignored, creating permanent technical debt
- Gets removed too aggressively, destroying useful observability

The solution is a **two-tier marker system** with a **pre-commit gate** that forces a decision before any debug code reaches the repository.

---

## Marker Convention

Place a marker comment on the line **immediately before** each temporary debug statement. Never on the same line (makes automated search and removal easier).

### TEMP — Must remove before merging

```python
# DEBUG-TEMP: tracing entry point to isolate null user
log.debug("process_order: user=%r cart=%r", user, cart)
```

```javascript
// DEBUG-TEMP: checking if discount is applied twice
console.debug('[applyDiscount] cart total before:', cart.total, 'rules:', rules);
```

```go
// DEBUG-TEMP: verifying context propagation
slog.Debug("handleRequest", "ctx_keys", ctx.Value("request_id"), "user_id", userID)
```

### KEEP — Evaluate before merging, promote or remove

```python
# DEBUG-KEEP: this might be worth keeping as INFO — payment processor responses are hard to reconstruct
log.debug("payment processor: status=%s response=%r", status, response_body)
```

```javascript
// DEBUG-KEEP: could be useful INFO for support tickets
log.debug('subscription renewal', { userId, plan, renewalDate, amount });
```

### Language-specific prefixes

| Language | TEMP marker | KEEP marker |
|---|---|---|
| Python, Ruby, Shell, YAML, Makefile | `# DEBUG-TEMP:` | `# DEBUG-KEEP:` |
| JS, TS, Java, C, C++, Go, Rust, Swift, Kotlin, Scala | `// DEBUG-TEMP:` | `// DEBUG-KEEP:` |
| HTML, XML, JSX (non-code) | `<!-- DEBUG-TEMP: ... -->` | `<!-- DEBUG-KEEP: ... -->` |
| SQL | `-- DEBUG-TEMP:` | `-- DEBUG-KEEP:` |
| CSS, SCSS | `/* DEBUG-TEMP: ... */` | `/* DEBUG-KEEP: ... */` |
| Lua, Haskell | `-- DEBUG-TEMP:` | `-- DEBUG-KEEP:` |

---

## Git Pre-Commit Hook

### Install (one-time per repository)

```bash
# From the repository root:
cp .git/hooks/pre-commit.sample .git/hooks/pre-commit 2>/dev/null || touch .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit
```

Append the following to `.git/hooks/pre-commit`:

```bash
#!/bin/bash
# Debug marker check — blocks commit if temporary debug code is present

set -e

MARKERS="DEBUG-TEMP\|DEBUG-KEEP"
FOUND=$(git diff --cached --unified=0 | grep "^+" | grep -v "^+++" | grep "$MARKERS" || true)

if [ -n "$FOUND" ]; then
  echo ""
  echo "╔══════════════════════════════════════════════════════════════╗"
  echo "║  COMMIT BLOCKED: Unresolved debug markers found             ║"
  echo "╚══════════════════════════════════════════════════════════════╝"
  echo ""
  echo "The following debug markers must be resolved before committing:"
  echo ""
  git diff --cached --unified=0 | grep "^+" | grep -v "^+++" | grep --color=always "$MARKERS"
  echo ""
  echo "For each DEBUG-TEMP:  remove the marker and its debug statement."
  echo "For each DEBUG-KEEP:  remove OR promote to a permanent log (adjust level to INFO/WARN/ERROR)."
  echo ""
  echo "To scan all staged files: git diff --cached | grep 'DEBUG-TEMP\|DEBUG-KEEP'"
  echo ""
  exit 1
fi
```

### Bypass (emergency only)

If you intentionally need to commit with markers for a work-in-progress branch:
```bash
git commit --no-verify -m "WIP: debugging payment flow (debug markers present)"
```

Never bypass on a branch that will be merged to main/master.

---

## Shareable Team Config (`.git/hooks` vs shared scripts)

Git hooks in `.git/hooks/` are not committed to the repository. For team-wide enforcement, use one of these approaches:

### Option 1: Committed hook script + setup step

Add a `scripts/install-hooks.sh` to the repository:

```bash
#!/bin/bash
# scripts/install-hooks.sh
HOOK=.git/hooks/pre-commit

cat >> "$HOOK" << 'HOOKEOF'

# Debug marker check
MARKERS="DEBUG-TEMP\|DEBUG-KEEP"
FOUND=$(git diff --cached --unified=0 | grep "^+" | grep -v "^+++" | grep "$MARKERS" || true)
if [ -n "$FOUND" ]; then
  echo "COMMIT BLOCKED: Resolve debug markers before committing:"
  git diff --cached --unified=0 | grep "^+" | grep -v "^+++" | grep "$MARKERS"
  echo "Remove DEBUG-TEMP lines; promote or remove DEBUG-KEEP lines."
  exit 1
fi
HOOKEOF

chmod +x "$HOOK"
echo "Debug marker pre-commit hook installed."
```

Document in README / CLAUDE.md:
```
## Development Setup
Run `scripts/install-hooks.sh` after cloning to install pre-commit checks.
```

### Option 2: pre-commit framework (Python)

Add to `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: local
    hooks:
      - id: debug-markers
        name: Check for debug markers
        language: pygrep
        entry: 'DEBUG-TEMP|DEBUG-KEEP'
        args: [--multiline]
        description: "Blocks commit if temporary debug markers are present"
```

Install: `pip install pre-commit && pre-commit install`

### Option 3: lefthook (Go, fast, cross-platform)

Add to `lefthook.yml`:

```yaml
pre-commit:
  commands:
    debug-markers:
      run: |
        if git diff --cached | grep -E 'DEBUG-TEMP|DEBUG-KEEP'; then
          echo "Resolve debug markers before committing."
          exit 1
        fi
```

Install: `lefthook install`

---

## Mercurial Pre-Commit Hook

Add to `.hg/hgrc`:

```ini
[hooks]
precommit.debug-markers = python:check_debug_markers

[extensions]
# no extensions needed
```

Create `.hg/check_debug_markers.py`:

```python
import re, subprocess, sys

def check_debug_markers(ui, repo, **kwargs):
    diff = subprocess.check_output(['hg', 'diff', '-c', 'tip'], text=True)
    pattern = re.compile(r'DEBUG-TEMP|DEBUG-KEEP')
    matches = [line for line in diff.splitlines() if line.startswith('+') and pattern.search(line)]
    if matches:
        ui.warn("COMMIT BLOCKED: Unresolved debug markers:\n")
        for m in matches:
            ui.warn(f"  {m}\n")
        return True  # non-zero → abort
```

---

## Cleanup Checklist

When a bug is resolved and ready to commit:

```
□ Run: git grep -n "DEBUG-TEMP\|DEBUG-KEEP" (or grep -rn for non-git dirs)
□ For each DEBUG-TEMP marker:
    □ Delete the marker comment
    □ Delete the debug statement on the following line
□ For each DEBUG-KEEP marker:
    □ Ask: "Would this log be useful in production for support/monitoring?"
    □ If YES → promote:
        □ Remove the # DEBUG-KEEP: comment
        □ Change log level to INFO, WARN, or ERROR as appropriate
        □ Adjust message to be clear to someone who wasn't debugging (no jargon)
        □ Verify it doesn't log sensitive data (passwords, tokens, PII)
    □ If NO → remove marker and statement
□ Run pre-commit hook manually: .git/hooks/pre-commit
□ Review permanent logging added → confirm it follows project conventions
```

---

## Promoting Debug Logs to Permanent

Not all debug logs should be deleted. Consider keeping logs that:

| Criterion | Example |
|---|---|
| Records a significant decision or transition | Order state changed from `pending` to `fulfilled` |
| Captures external call parameters and responses | Payment processor request + response |
| Aids future bug diagnosis in the same area | The exact condition that triggered a fallback |
| Provides an audit trail | User permission escalation, financial operation |
| Would prevent a future debugging session | The single value that was wrong last time |

### Promotion steps

1. Remove the `# DEBUG-KEEP:` marker line
2. Change log level: `DEBUG` → `INFO` (normal operation) or `WARN` (unexpected but handled) or `ERROR` (failure)
3. Rewrite message to be self-explanatory without debug context:
   ```python
   # Before (debug):
   # DEBUG-KEEP: provider response hard to reconstruct
   log.debug("resp: %r %r", status, body)

   # After (promoted):
   log.info("payment.processed: provider=%s status=%s amount=%s",
            provider, status, amount)
   ```
4. Verify the log does not contain sensitive data
5. Confirm the message follows the project's logging conventions (naming, field names, format)

---

## Searching for Markers

```bash
# All debug markers in working tree:
grep -rn "DEBUG-TEMP\|DEBUG-KEEP" --include="*.py" --include="*.ts" --include="*.go" .

# Only in staged changes (pre-commit check):
git diff --cached | grep "DEBUG-TEMP\|DEBUG-KEEP"

# All debug markers in entire git history (find forgotten commits):
git log -S "DEBUG-TEMP" --oneline
git log -S "DEBUG-KEEP" --oneline
```

---

## Workflow Summary

```
Bug reported
    │
    ▼
Add debug instrumentation
    │  (mark each with # DEBUG-TEMP: or # DEBUG-KEEP:)
    ▼
Debug session — reproduce, inspect, understand root cause
    │
    ▼
Fix the bug
    │
    ▼
Cleanup pass:
  • Remove all DEBUG-TEMP markers + statements
  • Decide each DEBUG-KEEP: promote or remove
    │
    ▼
Pre-commit hook runs automatically
  → Blocks if any markers remain
  → Passes if clean
    │
    ▼
Commit and merge
```

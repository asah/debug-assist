---
name: debug-assist
description: This skill should be used when the user needs to diagnose a bug, wants to add debug logging or print statements, asks where to place logging, wants guidance on step-through debugging or breakpoints, needs to know what variables or state to inspect, asks about managing temporary debug code before committing, wants to clean up debug statements, or says things like "I can't figure out why this is failing", "help me debug this", "add some logging here", or "where should I put a breakpoint". Applies to any language or platform.
version: 1.0.0
tools: Read, Glob, Grep, Bash, Task
---

# Debug Assist

Systematic framework for diagnosing bugs through strategic logging, step-through debugging, and parallel code analysis. Language-agnostic — apply the appropriate idioms, tools, and frameworks for the detected language and runtime.

## Phase 1: Problem Assessment

Before suggesting any instrumentation, understand the nature of the bug:

1. **Gather symptoms** (ask if not provided):
   - What is the unexpected behavior vs. what was expected?
   - Is it reproducible? Always, intermittently, or only under specific conditions?
   - Where does it manifest — which module, function, layer, or request type?
   - What kind of failure: crash/exception, wrong output, missing data, deadlock, or performance?

2. **Scan the relevant code**:
   - Use Glob/Grep to locate the suspected function or module
   - Read the call path from trigger point to failure point
   - Check for existing logging — avoid duplicating it

3. **Select a debugging strategy** using the table below

## Strategy Selection

| Scenario | Approach |
|---|---|
| Remote, production, or staging system | Logging only |
| Async, concurrent, or timing-sensitive code | Logging with correlation IDs |
| Complex local logic needing object inspection | Debugger |
| Need historical trace (sequence of events over time) | Logging |
| Hypothesis testing (modify state to verify) | Debugger REPL |
| Multi-process or distributed system | Structured logging + trace IDs |
| Reproducible crash with local dev access | Debugger |
| Intermittent bug needing many trials | Logging + automated test harness |
| Performance bottleneck | Profiler + targeted timing logs |
| Unknown cause across multiple modules | Parallel subagents → then logging or debugger |

## Phase 2: Parallel Code Analysis (for Multi-Module Bugs)

When the bug could originate in multiple places, launch concurrent subagents to analyze each section independently — this is faster than sequential investigation.

**When to parallelize:**
- Bug spans more than one module, service, or layer
- Unclear which of several components is responsible
- Large codebase where tracing manually would take many steps

**Launch pattern** (adapt to the actual code sections):

```
Launch Task agents concurrently, one per logical section:
  Agent A: Trace data flow from the entry point to the suspected failure
  Agent B: Inspect state management and all mutation points for the key data structure
  Agent C: Analyze all external call boundaries (DB queries, API calls, file I/O, IPC)
  Agent D: Review error handling and exception propagation paths
```

Each agent should return:
- The code path it analyzed (files + line ranges)
- Suspicious logic, missing guards, or unexpected state
- Specific recommended log placement points with suggested log content
- Breakpoint locations if debugger is appropriate

Synthesize all agent findings before writing any instrumentation.

See **[references/parallel-debug-agents.md](references/parallel-debug-agents.md)** for ready-to-use agent prompt templates.

## Phase 3: Logging Instrumentation

### Where to Place Debug Logs

Instrument at these structural points (in order of diagnostic value):

1. **Function/method entry** — all parameters and their types/shapes; relevant initial state
2. **Function/method exit and return points** — return value; state that was mutated
3. **Before and after external calls** — DB queries with parameters and row counts, API calls with URL/status/body, file I/O with path and size, subprocess calls with args and exit code
4. **Branch decision points** — which branch was taken and the condition values that drove it
5. **Loop bodies** — on complex loops: iteration number, key variable values, and early-exit conditions
6. **State transitions** — before and after writes to shared, global, or session state
7. **Error paths** — full context (all relevant variables) immediately before raising or returning an error

### What to Include in Each Log Message

Every debug log should answer: **Where am I? What is the state? What just happened?**

- Function or method name (use language introspection to capture automatically when possible)
- The specific variable(s) relevant to the suspect logic — not a blind object dump
- For collections: length AND a representative sample (first/last element, or a slice)
- For nested objects: the fields that matter to this bug; use pretty-print for readability
- For errors: full error chain (cause → wrapping errors), not just the outermost message
- A short label so you can grep for this specific log point later

**Use the language's standard logging facility** (Python `logging`, Java `slf4j`, Go `slog`, JS `console.debug` or a logger, Rust `tracing`, etc.) rather than bare print statements. This preserves log-level filtering and doesn't pollute stdout in tests.

See **[references/logging-patterns.md](references/logging-patterns.md)** for language-specific idioms, structured logging patterns, and examples.

## Phase 4: Step-Through Debugging

Use when the bug is reproducible locally and you need fine-grained state inspection that would require too many log iterations.

### Breakpoint Placement Strategy

- **Primary**: At the exact suspected location
- **Secondary**: At the entry of the function containing the bug (to verify incoming state)
- **Tertiary**: At the call site if the function appears to be receiving bad input
- **Error sites**: At exception throw points and error handler entry
- **Conditional**: Use conditional breakpoints when the bug only occurs for specific values — avoids stopping on every iteration of a loop

### What to Inspect at Each Pause

At every breakpoint, check in this order:

1. **Local variables** — current values vs. what you expect them to be at this point
2. **Call stack** — who called this function, with what arguments, through what path
3. **Closure / captured variables** — if inside a lambda, closure, or anonymous function
4. **Object internals** — expand nested structures; don't trust surface-level string representations
5. **Global / module-level state** — any shared mutable state the function reads or writes
6. **Thread / goroutine / coroutine state** — for concurrent bugs, examine other threads' state and locks held
7. **Heap / references** — for memory bugs, check whether two variables alias the same object unexpectedly

### Debugger Workflow

1. Set breakpoints at the locations identified above
2. Use a minimal reproduction case — avoid running the full app if a smaller harness can trigger the bug
3. At first pause: confirm you're in the right place by reading the call stack
4. Inspect state systematically using the checklist above
5. Form a specific hypothesis: "variable `X` should be `Y` here but is `Z` because..."
6. Test the hypothesis: modify state via the debugger's REPL/watch if available, or add a conditional and re-run
7. Repeat until root cause is confirmed and understood

See **[references/debugger-strategies.md](references/debugger-strategies.md)** for platform-specific commands, watchpoint usage, and introspection techniques across common debuggers.

## Phase 5: Debug Code Lifecycle

All temporary debug instrumentation must be marked so it can be tracked, reviewed, and cleaned up before the code is merged or committed.

### Marking Convention

Place a marker comment on the line immediately **before** each temporary debug statement:

**Must remove before merge:**
```
# DEBUG-TEMP: <brief reason>
log.debug("entry: x=%r y=%r", x, y)
```

**Evaluate before merge — candidate for permanent logging:**
```
# DEBUG-KEEP: <brief reason why this might be worth keeping>
log.debug("payment processor response: status=%s body=%s", status, body)
```

Language-specific marker prefixes:
- Python / Ruby / Shell / YAML: `# DEBUG-TEMP:` / `# DEBUG-KEEP:`
- JS / TS / Java / C / C++ / Go / Rust / Swift / Kotlin: `// DEBUG-TEMP:` / `// DEBUG-KEEP:`
- HTML / XML: `<!-- DEBUG-TEMP: ... -->` / `<!-- DEBUG-KEEP: ... -->`
- SQL: `-- DEBUG-TEMP:` / `-- DEBUG-KEEP:`

### Pre-Commit Guard

Install a commit-time check that scans for these markers and blocks the commit until they are resolved. See **[references/debug-lifecycle.md](references/debug-lifecycle.md)** for pre-commit hook scripts for git (and other VCS), plus instructions on setting them up.

### Cleanup Procedure

When the bug is understood and fixed:

1. Search for all `DEBUG-TEMP` markers → **remove** the marker and its associated debug statement
2. Search for all `DEBUG-KEEP` markers → **decide** for each:
   - Remove if the information is no longer needed, or
   - Promote: adjust log level to `INFO`/`WARN`/`ERROR` as appropriate, remove the marker, and ensure message follows production logging conventions
3. Run the pre-commit check to confirm no markers remain
4. Review all retained logging — confirm it follows the project's logging conventions and doesn't leak sensitive data

### Elevating Temporary Logs to Permanent

A debug log is worth keeping permanently if it:
- Records a significant state transition or decision point
- Captures context that would otherwise require re-attaching a debugger to understand
- Provides an audit trail for security, compliance, or billing-related operations
- Would accelerate diagnosis of future regressions in the same area

When promoting, change the log level from `DEBUG` to the appropriate production level and ensure the message is self-contained and follows the project's conventions.

## Auto-Detection: When Claude Proactively Suggests Instrumentation

Proactively recommend adding debug logging (with markers) when the code being read or written shows:

- Complex branching (`if`/`else` chains, `switch`, polymorphic dispatch) with no logging at decision points
- External calls (DB, API, file, network) that log neither their inputs nor their outputs
- Long functions (>40–60 lines) with no intermediate observability
- Error handlers that catch exceptions and silently swallow or re-wrap them without logging
- Async or concurrent code paths with no correlation identifiers linking related log entries
- State mutations to shared or global objects with no before/after visibility
- Retry loops with no per-attempt logging

## Additional Resources

- **[references/logging-patterns.md](references/logging-patterns.md)** — Placement heuristics, what to log, structured logging, language idioms
- **[references/debugger-strategies.md](references/debugger-strategies.md)** — Breakpoint types, introspection checklist, platform-specific tips
- **[references/debug-lifecycle.md](references/debug-lifecycle.md)** — Marker convention, pre-commit hooks, promotion workflow, log level guidance
- **[references/parallel-debug-agents.md](references/parallel-debug-agents.md)** — When and how to use parallel subagents, prompt templates, synthesis patterns

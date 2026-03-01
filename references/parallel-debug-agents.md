# Parallel Debug Agents Reference

When to use concurrent subagents for debugging, how to structure their prompts, and how to synthesize their findings.

---

## When Parallel Agents Accelerate Debugging

Parallelizing is worth the overhead when:

| Situation | Benefit |
|---|---|
| Bug could originate in any of 3+ separate modules | Each agent focuses deeply on one module |
| Large codebase where tracing manually takes many steps | Agents explore concurrently |
| Multiple independent hypotheses to test | Each agent investigates one hypothesis |
| Bug spans multiple system layers (e.g., API → service → DB) | One agent per layer |
| Need both logging recommendations AND debugger guidance | Split by concern |
| Several async code paths that may interact | Each agent traces one path |

**When parallel agents are NOT worth it:**
- Bug is clearly localized to one function or file (just read and analyze directly)
- Codebase is small (<20 files) — sequential reading is faster
- You've already identified the root cause and just need to add instrumentation

---

## Coordination Pattern

```
Phase 1: Dispatch agents concurrently
  └─ Each agent: analyze one section, return findings + recommendations

Phase 2: Collect and synthesize
  └─ Read all agent results
  └─ Identify overlaps (same data passing through multiple sections)
  └─ Prioritize: which finding has highest confidence?
  └─ Resolve conflicts: if agents disagree, read the code yourself to arbitrate

Phase 3: Produce unified instrumentation plan
  └─ Ordered list of log placement points with content
  └─ Breakpoint recommendations
  └─ Root cause hypothesis based on combined evidence
```

---

## Agent Prompt Templates

Use these as starting points. Adapt to the specific bug, code structure, and language.

### Template 1 — Data Flow Tracer

Assigns one agent to follow a specific piece of data from entry to the point of failure.

```
You are a debugging specialist. Your job is to trace how [DATA/VALUE] flows through the code
and identify where it could become incorrect.

Starting point: [ENTRY FUNCTION OR FILE]
Suspected failure: [WHAT IS WRONG / WHAT VALUE IS UNEXPECTED]
Language/framework: [LANGUAGE] using [FRAMEWORK IF ANY]

Steps:
1. Read the entry point and identify how [DATA] is received and initially processed.
2. Follow every function call that touches [DATA], reading each function in turn.
3. For each step, note:
   - Is [DATA] validated or transformed here?
   - Could it become null/nil/None/undefined/wrong-type here?
   - Are there silent error paths that might corrupt it?
4. Identify the 2-3 most suspicious locations where [DATA] could become wrong.
5. For each suspicious location, provide:
   - File path and line number range
   - A specific log statement to add (with the exact variables to log and message format)
   - A breakpoint recommendation (file:line, what to inspect when paused)
6. Return: a ranked list of suspicious locations with log/breakpoint recommendations.

Files to start from: [LIST OF FILES]
```

### Template 2 — State Mutation Inspector

Assigns one agent to find all places where a shared piece of state is modified.

```
You are a debugging specialist focusing on state management.

The bug involves: [DESCRIBE THE STATE THAT SEEMS WRONG]
Suspected state variable(s): [VARIABLE NAME / OBJECT NAME]
Language/framework: [LANGUAGE]

Steps:
1. Find all locations in the codebase where [STATE] is written (not just read).
2. For each write location:
   - Note what value is being written and under what condition
   - Note whether the write is atomic, thread-safe, or could race with another write
   - Note whether there's any validation of the value before writing
3. Find all locations where [STATE] is read in ways that affect control flow or output.
4. Identify the most suspicious write(s) — the one most likely to produce the observed bug.
5. For each suspicious write, provide:
   - File path and line number
   - A before/after log statement showing old value → new value
   - A breakpoint recommendation with a list of what to inspect (local vars + call stack)

Files to search: [LIST OF FILES OR DIRECTORIES]
```

### Template 3 — External Call Boundary Auditor

Assigns one agent to look at all external calls (DB, API, file, IPC) and their error handling.

```
You are a debugging specialist focusing on external system boundaries.

The bug involves: [DESCRIBE THE SYMPTOM — wrong data, missing data, unexpected error]
System type: [WEB API / DATABASE / FILE SYSTEM / MESSAGE QUEUE / other]
Language/framework: [LANGUAGE]

Steps:
1. Find all external calls in the suspected code area (DB queries, HTTP requests, file reads/writes,
   queue reads/writes, subprocess calls).
2. For each external call:
   - Is the request/query logged with its parameters before sending?
   - Is the response/result logged with its status and key fields after receiving?
   - Is the error handling complete — or could errors be swallowed silently?
   - Could the response be unexpectedly empty, null, or paginated?
3. Identify which external call is most likely to be the source of the problem.
4. For each suspicious call, provide:
   - File path and line number
   - A log statement to add before the call (parameters being sent)
   - A log statement to add after the call (response summary and key fields)
   - An error log to add in any error/exception handler
5. If there are retry or timeout patterns, note whether they log each attempt.

Files to search: [LIST OF FILES]
```

### Template 4 — Error Propagation Tracer

Assigns one agent to trace how errors bubble up (or fail to bubble up) through the stack.

```
You are a debugging specialist focusing on error handling and propagation.

The symptom is: [DESCRIBE — e.g., "exception is caught but user sees wrong error message",
                  "error is silently swallowed", "error message is misleading"]
Language/framework: [LANGUAGE]

Steps:
1. Find the location where the error/exception originates (or could originate).
2. Trace how it propagates upward through the call stack:
   - Is it re-raised with full context?
   - Is it wrapped (and does the wrapper preserve the original cause)?
   - Is it caught and converted to a user-facing error (and is context preserved)?
   - Is it caught and silently ignored?
3. Identify any catch/except/rescue blocks that:
   - Swallow the exception without logging
   - Log only a summary without the original exception
   - Re-raise a different exception type that loses context
4. For each suspicious error handling location, provide:
   - File path and line number
   - A log statement to add (including full exception/error chain, all relevant context variables)
   - Whether the error handling should be changed (not just logged — note if it's structurally wrong)

Files to search: [LIST OF FILES]
```

### Template 5 — Async/Concurrency Reviewer

Assigns one agent to look for race conditions, ordering bugs, and missing correlation IDs.

```
You are a debugging specialist focusing on asynchronous and concurrent code.

The symptom is: [DESCRIBE — e.g., "intermittent failure", "data sometimes missing",
                  "operations occasionally in wrong order"]
Language/framework: [LANGUAGE — note: async/await, goroutines, threads, actors, etc.]

Steps:
1. Identify all async boundaries in the code path (async/await, goroutine launches,
   thread spawns, callbacks, event listeners, queue consumers).
2. For each async boundary:
   - Is a correlation/trace ID propagated across the boundary?
   - Are shared variables accessed from multiple goroutines/tasks/threads?
   - Is there a lock, mutex, or channel protecting the shared state?
   - Could two concurrent operations interleave in a way that produces the observed bug?
3. Identify the most suspicious race or ordering hazard.
4. For each hazard, provide:
   - File path and line number
   - A log statement that includes a correlation ID + the shared value being read/written
   - Whether a synchronization primitive is missing (and where to add it)
5. If no correlation ID exists in this code, suggest where to add one (entry point + propagation).

Files to search: [LIST OF FILES]
```

---

## Synthesis Pattern

After all agents return, combine their findings:

```markdown
## Debug Analysis Synthesis

### Confirmed overlaps (high confidence)
- Both Agent A (data flow) and Agent C (external calls) flagged [LOCATION] —
  high confidence this is the root cause
  → Add logging at [FILE:LINE] before and after [CALL]
  → Set breakpoint at [FILE:LINE], inspect [VARIABLES]

### Single-agent findings (medium confidence)
- Agent B (state mutation) flagged [LOCATION] — only one agent flagged this
  → Add a before/after state log at [FILE:LINE] to confirm or rule out

### Low-confidence signals (investigate if above don't reproduce the bug)
- Agent D noted [OBSERVATION] — keep in mind if primary hypothesis is wrong

### Recommended instrumentation order
1. [HIGHEST CONFIDENCE LOCATION] — add logs first, run, check output
2. [SECOND LOCATION] — if #1 doesn't reveal the bug
3. [THIRD LOCATION] — fallback

### Root cause hypothesis
Based on combined findings: [STATE HYPOTHESIS CLEARLY]
- If correct, the debug logs at [LOCATION] will show [WHAT YOU EXPECT TO SEE]
- If incorrect, the logs will show [WHAT WOULD REFUTE THE HYPOTHESIS]
```

---

## Capacity and Environment Considerations

Before launching parallel agents, check whether the environment supports them:

```bash
# Check if we're in a CI environment or resource-constrained shell:
echo "CPU cores: $(nproc 2>/dev/null || sysctl -n hw.ncpu 2>/dev/null || echo unknown)"
echo "Available memory: $(free -h 2>/dev/null | awk '/^Mem:/ {print $7}' || vm_stat 2>/dev/null | head -5)"
```

**Guidelines:**
- Use 2–3 parallel agents for most multi-module bugs (diminishing returns beyond 4)
- Each agent focuses on a distinct, non-overlapping section of code
- Avoid launching more agents than there are distinct hypotheses
- In resource-constrained environments (low memory, CI with limited runners), run agents sequentially

**Agent tool restrictions:**
- Give each agent only read-access tools: `Read, Glob, Grep, Bash`
- Agents should NOT modify files — they return recommendations only
- The main session implements instrumentation after synthesizing all findings

---

## Example: 3-Agent Parallel Debug Session

**Scenario:** An e-commerce checkout sometimes charges the wrong amount. The code spans: `CartService → PricingEngine → PaymentProcessor`.

**Agent dispatch:**

```
Agent 1 (Data Flow): Trace how cart.total flows from CartService.checkout()
through PricingEngine.calculateFinal() to PaymentProcessor.charge().
Focus on: any discount application, currency conversion, or rounding steps.
Files: src/cart/cart_service.py, src/pricing/engine.py

Agent 2 (State Mutation): Find all places where cart.total or any price field
is written after the cart is created. Look for mutation by reference vs. by value.
Files: src/cart/, src/pricing/, src/promotions/

Agent 3 (External Calls): Audit the PaymentProcessor.charge() call and all
calls to pricing microservices or discount APIs. Check: are parameters logged?
Are responses validated? Is the charged amount the same as what was calculated?
Files: src/payment/, src/pricing/external_client.py
```

**After synthesis:**
- If Agent 1 and Agent 2 both flag `PricingEngine.apply_discount()` → high confidence, add logging there first
- If only Agent 3 flags an API inconsistency → add logging around that external call next
- Formulate hypothesis, add targeted logs, run test case, confirm or refute

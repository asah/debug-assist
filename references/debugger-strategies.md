# Debugger Strategies Reference

Guidance on when to use a step-through debugger, how to set effective breakpoints, what to inspect, and platform-specific tips for common debuggers.

---

## When a Debugger Beats Logging

Prefer an interactive debugger when:

| Situation | Why a Debugger Wins |
|---|---|
| Complex, branchy logic needing object inspection | Can explore any variable without re-running |
| Hypothesis testing (try modifying state mid-run) | Debugger REPL lets you mutate and continue |
| One-time local reproduction available | Faster iteration than add-log → re-run → repeat |
| Call stack is the key question (who called me?) | Stack frame navigation is instant |
| Need to understand a loop or recursion | Can step through one iteration at a time |
| The bug disappears when you add print statements | Timing-sensitive: debugger shows state without output overhead (use logging instead for race conditions) |

---

## Breakpoint Placement Strategy

### Primary breakpoint — at the suspected location
Set this first. If you're not sure of the exact line, set it at the function entry and step forward.

### Secondary breakpoint — at the function entry
Verifies the inputs are what you expect before any internal logic runs. If inputs are already wrong, the bug is upstream.

### Tertiary breakpoint — at the call site
When the function receives bad input, step back up the call chain. Set a breakpoint at the line that calls the function and inspect the arguments being passed.

### Error site breakpoints
Set breakpoints on:
- The line that raises/throws an exception
- The top of each `catch`/`except`/`rescue` block
- The `return err` or `return nil, err` pattern in Go-style error handling

### Conditional breakpoints
Use conditional breakpoints to avoid stopping on every iteration of a loop or every request:

```
# Only stop when the bug condition is true:
user_id == 42
len(items) > 1000
status_code != 200
```

Most debuggers support this natively. Use it aggressively to reduce noise.

### Logpoints (non-breaking trace points)
Many modern debuggers support "logpoints" — breakpoints that print a message instead of pausing. These are useful when you want tracing without modifying source code. Available in VS Code, IntelliJ, Chrome DevTools.

---

## Systematic Inspection Checklist

At every breakpoint pause, check in this order:

### 1. Local variables
- Are they the expected type and value?
- Are any unexpectedly `null`/`nil`/`None`/`undefined`?
- Are numeric values within expected range?
- Are strings correctly encoded (watch for encoding bugs, extra whitespace, wrong locale)?

### 2. Call stack
- Is the call path what you expected?
- Are there unexpected intermediary calls?
- Was this function called recursively when it shouldn't be?
- Check each frame's arguments — is the bad data introduced at a specific call level?

### 3. Closure and captured variables
- If inside a lambda, callback, or anonymous function, inspect the enclosing scope
- Check that the captured variables haven't changed since the closure was created (stale closure)
- For event handlers: is `this`/`self` bound correctly?

### 4. Object internals — expand nested structures
- Don't trust the top-level string representation; expand into nested fields
- Check that the object is the instance you think it is (class/type name)
- Look for unexpected `None`/`null` inside a seemingly valid object
- For collections: check both the container and individual elements

### 5. Global and module-level state
- Any global variables the function reads or writes
- Module-level singletons, caches, registries
- Thread-local storage
- Application configuration that might have been modified

### 6. Concurrent state (for threading/async bugs)
- Other thread/goroutine call stacks
- Locks held vs. locks waiting to be acquired
- Shared queue or channel contents
- Order of operations across goroutines/threads

### 7. Heap / memory (for low-level or memory bugs)
- Do two variables unexpectedly reference the same object? (aliasing)
- Has an object been freed/GC'd prematurely?
- Is a buffer or slice sharing memory with another collection?
- Reference counts for languages with manual or ref-counted memory

---

## Debugger Workflow

```
1. Identify suspect location → set primary breakpoint
2. Create minimal reproduction (smallest input that triggers the bug)
3. Run under the debugger
4. At first pause: verify call stack — are you where you expected to be?
5. Inspect state systematically (checklist above)
6. Form hypothesis: "X should be Y here but is Z because ___"
7. Test hypothesis:
   a. Modify a variable in the debugger REPL and continue — does behavior change?
   b. Or add a conditional breakpoint closer to the root cause and re-run
8. When root cause is confirmed: fix, then verify fix under debugger before removing breakpoints
```

---

## Platform-Specific Reference

### Python — pdb / debugpy / IDE debuggers

**CLI (pdb):**
```python
import pdb; pdb.set_trace()  # break here
# or from Python 3.7+:
breakpoint()  # respects PYTHONBREAKPOINT env var
```

**Key pdb commands:**
```
n          # next line (step over)
s          # step into call
r          # run to end of current function (step out)
c          # continue to next breakpoint
l          # list source around current line
p expr     # print expression
pp expr    # pretty-print expression
w          # print call stack (where)
u / d      # move up/down stack frames
b 42       # set breakpoint at line 42
b fn       # set breakpoint at function entry
condition 1 x > 10  # make breakpoint 1 conditional
```

**Remote debugging (e.g., in Docker):**
```python
import debugpy
debugpy.listen(("0.0.0.0", 5678))
debugpy.wait_for_client()
```

**pytest integration:**
```bash
pytest --pdb              # drop into pdb on failure
pytest -x --pdb           # stop at first failure
pytest --trace            # pdb at start of each test
```

### JavaScript / TypeScript — Node.js

**Built-in inspector:**
```bash
node --inspect app.js           # start inspector, attach Chrome DevTools
node --inspect-brk app.js       # break at first line
```

**Programmatic breakpoint:**
```javascript
debugger;  // pauses when DevTools is open
```

**VS Code launch config (`.vscode/launch.json`):**
```json
{
  "type": "node",
  "request": "launch",
  "name": "Debug App",
  "program": "${workspaceFolder}/src/index.ts",
  "outFiles": ["${workspaceFolder}/dist/**/*.js"],
  "sourceMaps": true
}
```

**Chrome DevTools for browser code:**
- Open DevTools → Sources → find file → click line number to set breakpoint
- Use "Conditional breakpoint" (right-click line number)
- Use "Logpoint" (right-click → Add logpoint) for non-pausing trace

### Go — Delve

```bash
dlv debug ./cmd/server          # compile + debug
dlv test ./pkg/payments         # debug test
dlv attach <pid>                # attach to running process
```

**Key Delve commands:**
```
b main.processPayment           # breakpoint at function
b payments.go:42                # breakpoint at file:line
c                               # continue
n                               # next (step over)
s                               # step into
stepout                         # step out
p variableName                  # print variable
p *ptr                          # dereference pointer
locals                          # all local variables
args                            # function arguments
goroutines                      # list all goroutines
goroutine 5 bt                  # backtrace of goroutine 5
```

### Rust — rust-gdb / rust-lldb / VS Code + CodeLLDB

```bash
rust-gdb target/debug/myapp    # GDB with Rust pretty-printers
rust-lldb target/debug/myapp   # LLDB with Rust pretty-printers
```

**VS Code (CodeLLDB extension) launch config:**
```json
{
  "type": "lldb",
  "request": "launch",
  "name": "Debug",
  "program": "${workspaceFolder}/target/debug/myapp",
  "args": [],
  "env": {"RUST_LOG": "debug"}
}
```

**Useful for Rust:**
- Use `dbg!(expr)` macro to print + return a value during development (similar to a logpoint)
- `eprintln!("{:?}", value)` for debug-format output
- Conditional compilation: `#[cfg(debug_assertions)] { ... }` for debug-only code

### Java / Kotlin — JVM Debugger (jdwp)

```bash
# Start JVM in debug mode:
java -agentlib:jdwp=transport=dt_socket,server=y,suspend=y,address=*:5005 -jar app.jar
```

Connect via IntelliJ (Run → Attach to Process) or VS Code Java Extension.

**IntelliJ tips:**
- Evaluate Expression (Alt+F8) — run any expression in the current frame
- "Mark Object" — track a specific object instance across frames
- Stream Debugger — visualize stream pipeline transformations
- Async Stack Trace — correlate coroutine suspension points

### C / C++ — GDB / LLDB

**GDB:**
```bash
gdb ./myapp
run --arg1 value              # start with arguments
break main.c:42               # breakpoint at file:line
break processPayment          # breakpoint at function
condition 1 amount > 1000.0   # conditional breakpoint
watch variable                # watchpoint (breaks on write)
rwatch variable               # breaks on read
print variable                # print value
ptype variable                # print type
x/10x ptr                     # examine 10 hex words at ptr address
info locals                   # all local variables
bt                            # backtrace
frame 2                       # select stack frame
```

**LLDB (macOS / Clang):**
```bash
lldb ./myapp
b processPayment              # breakpoint
run                           # start
n                             # next
s                             # step in
p variable                    # print
fr v                          # frame variables (all locals)
bt                            # backtrace
thread list                   # all threads
thread select 2               # switch thread
```

### Ruby — byebug / binding.pry

```ruby
require 'byebug'; byebug  # drop into byebug at this line
require 'pry'; binding.pry  # drop into pry REPL
```

**byebug commands:**
```
n          # next
s          # step
c          # continue
l          # list source
p expr     # print
pp expr    # pretty-print
where      # call stack
up / down  # navigate stack
display x  # auto-print x at each step
```

### Swift — LLDB (via Xcode)

Set breakpoints in Xcode's gutter. In the LLDB console:
```
p variableName
po objectToPrettyPrint    # uses CustomDebugStringConvertible
bt                        # backtrace
frame variable            # all locals in current frame
expr variable = newValue  # modify state
```

---

## Watchpoints (Break on Data Change)

Watchpoints pause execution when a specific variable is written (or read). Extremely useful when you know a variable is being corrupted but don't know where.

```bash
# GDB:
watch my_variable          # break when my_variable is written
rwatch my_variable         # break when my_variable is read
awatch my_variable         # break on read or write

# Delve (Go):
# Use goroutine inspection + conditional breakpoints as an alternative
# (Delve doesn't have traditional watchpoints for heap variables)
```

---

## Debugger REPL: Testing Hypotheses Mid-Session

Most debuggers allow you to evaluate arbitrary expressions while paused. Use this to test hypotheses without re-running:

```python
# pdb REPL — modify state and continue:
(Pdb) p self.status
'pending'
(Pdb) self.status = 'active'  # mutate and see if behavior changes
(Pdb) c
```

```javascript
// Chrome DevTools Console while paused:
> user.subscription.isActive()  // call a method on the live object
> user.tier = 'premium'         // mutate and continue
```

```go
// Delve REPL:
(dlv) p amount
decimal.Decimal{...}
(dlv) call processPayment(amount, "USD", userID)  // call a function live
```

This is the most powerful debugging technique for hypothesis testing — faster than adding a log, re-running, reading output, and repeating.

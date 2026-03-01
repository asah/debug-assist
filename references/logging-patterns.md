# Logging Patterns Reference

Guidance on when to use logging, where to place log statements, what to include, and how to write them idiomatically across languages.

---

## When Logging Beats a Debugger

Prefer logging over a step-through debugger when:

| Situation | Why Logging Wins |
|---|---|
| Production or staging system | Cannot attach a debugger; logs are the only window |
| Async / concurrent code | Debugger pauses distort timing; logs show real execution order |
| Distributed / multi-process system | No single process to attach to; need correlation across services |
| Intermittent bug needing many samples | Logs accumulate evidence across runs; debugger catches one at a time |
| Timing-sensitive code (race conditions) | Debugger pauses change timing and hide the bug |
| Long-running background jobs | Can't watch a debugger for hours; logs provide a post-mortem |
| CI / automated test environments | No interactive debugger available |
| Need to share evidence with a teammate | Logs are copyable; a debugging session is not |

---

## Strategic Placement Heuristics

### Tier 1 — Always instrument these (highest diagnostic value)

**Function/method entry** — captures what was handed to the function:
```python
log.debug("process_payment: amount=%r currency=%r user_id=%r", amount, currency, user_id)
```

**External call boundaries** — before the call (what you're sending) and after (what you got back):
```python
log.debug("db.query: sql=%r params=%r", sql, params)
result = db.execute(sql, params)
log.debug("db.query result: rows=%d first=%r", len(result), result[0] if result else None)
```

**Error paths** — full context immediately before raising or returning an error:
```python
log.error("payment failed: amount=%r user=%r error=%r provider_response=%r",
          amount, user_id, err, provider_response)
```

### Tier 2 — Instrument when branch logic is suspected

**Branch decision points** — the condition values, not just which branch:
```python
log.debug("checkout: applying_discount=%r user_tier=%r cart_total=%r threshold=%r",
          applying_discount, user.tier, cart.total, DISCOUNT_THRESHOLD)
```

**State transitions** — before and after the mutation:
```python
log.debug("order state: %r -> %r (order_id=%r)", old_status, new_status, order.id)
```

### Tier 3 — Instrument only when the above don't isolate the bug

**Loop iteration** — on complex loops only; log entry, key values per iteration, and exit:
```python
for i, item in enumerate(items):
    log.debug("process_items loop: i=%d item_id=%r queue_len=%d", i, item.id, len(queue))
```

**Function exit** — when return values are complex or the function modifies state:
```python
result = compute_pricing(cart)
log.debug("compute_pricing exit: result=%r", result)
return result
```

---

## What to Include in a Log Message

**The minimum viable log message:**
- A label you can grep for (function name or a short unique string)
- The one or two variables most relevant to the suspected bug
- Enough context to understand what was happening when the log fired

**For collections:** log count AND a sample — never log an entire large collection:
```python
log.debug("items: count=%d sample=%r", len(items), items[:3])
```

**For nested objects:** log the fields that matter, not a blind serialization:
```python
log.debug("user: id=%r tier=%r subscription_status=%r",
          user.id, user.tier, user.subscription.status)
```

**For errors:** include the full error chain, the triggering input, and any relevant context:
```python
log.exception("retry failed: attempt=%d url=%r timeout=%r", attempt, url, timeout)
# log.exception() automatically appends the current exception traceback
```

**Anti-patterns to avoid:**
- `log.debug("here")` — useless without values
- `log.debug(str(obj))` — dumps everything, noisy, often unreadable
- Logging sensitive data (passwords, tokens, PII, credit card numbers) — never
- Logging inside tight inner loops at DEBUG level without a rate limit

---

## Language-Specific Idioms

### Python

Use the `logging` module, never `print()` for debugging:

```python
import logging
log = logging.getLogger(__name__)

# Basic
log.debug("fn: x=%r y=%r result=%r", x, y, result)

# Exception with traceback
try:
    risky()
except Exception:
    log.exception("risky failed: context=%r", context)

# Structured fields (when using structlog or python-json-logger)
log.debug("event", fn="process", x=x, y=y)
```

Enable DEBUG output for a session:
```bash
python -c "import logging; logging.basicConfig(level=logging.DEBUG)"
# or set LOG_LEVEL=DEBUG in environment
```

### JavaScript / TypeScript (Node.js)

Use a logger (e.g., `pino`, `winston`) rather than `console.log`:

```typescript
import pino from 'pino';
const log = pino({ level: process.env.LOG_LEVEL || 'info' });

log.debug({ x, y, result }, 'processPayment entry');
log.error({ err, orderId }, 'payment failed');
```

For browser debugging, `console.debug()` is acceptable during development (lower visibility than `console.log`):
```javascript
console.debug('[processCart] items:', items.length, 'total:', total);
```

Enable verbose logging in Node.js:
```bash
LOG_LEVEL=debug node app.js
```

### Go

Use `log/slog` (Go 1.21+) for structured logging:

```go
import "log/slog"

slog.Debug("processPayment", "amount", amount, "userID", userID)
slog.Error("payment failed", "err", err, "amount", amount, "userID", userID)
```

Legacy `log` package (avoid for new code):
```go
log.Printf("processPayment: amount=%v userID=%v", amount, userID)
```

Enable debug output:
```go
slog.SetLogLoggerLevel(slog.LevelDebug)
```

### Rust

Use the `tracing` or `log` crate:

```rust
use tracing::{debug, error, instrument};

#[instrument]  // automatically logs function entry/exit with all arguments
fn process_payment(amount: Decimal, user_id: u64) -> Result<Receipt> {
    debug!(amount = %amount, user_id, "processing payment");
    // ...
    error!(err = ?e, amount = %amount, "payment failed");
}
```

Enable:
```bash
RUST_LOG=debug cargo run
RUST_LOG=myapp::payments=debug cargo run  # module-specific
```

### Java / Kotlin

Use SLF4J with a backend (Logback, Log4j2):

```java
private static final Logger log = LoggerFactory.getLogger(PaymentService.class);

log.debug("processPayment: amount={} currency={} userId={}", amount, currency, userId);
log.error("payment failed: amount={} userId={}", amount, userId, exception);
```

Kotlin with kotlin-logging:
```kotlin
private val log = KotlinLogging.logger {}
log.debug { "processPayment: amount=$amount userId=$userId" }
```

### C / C++

Use a logging library (spdlog, glog, or project's own):

```cpp
#include "spdlog/spdlog.h"

spdlog::debug("process_payment: amount={} user_id={}", amount, user_id);
spdlog::error("payment failed: amount={} user_id={} error={}", amount, user_id, err.what());
```

For debugging without a library:
```c
#ifdef DEBUG
  fprintf(stderr, "[DEBUG] %s:%d process_payment: amount=%f user_id=%lu\n",
          __FILE__, __LINE__, amount, user_id);
#endif
```

### Ruby

```ruby
require 'logger'
log = Logger.new($stderr)
log.level = Logger::DEBUG  # or set via LOG_LEVEL env var

log.debug("process_payment: amount=#{amount} user_id=#{user_id}")
log.error("payment failed: #{e.message} (amount=#{amount} user_id=#{user_id})\n#{e.backtrace.first(5).join("\n")}")
```

---

## Structured Logging

When the project uses structured logging (JSON output), emit key-value pairs rather than interpolated strings. This enables log aggregation tools (Datadog, Splunk, ELK, Cloud Logging) to index and query the fields.

**Structured example (Python with structlog):**
```python
log.info("payment.processed", amount=amount, currency=currency,
         user_id=user_id, duration_ms=duration_ms, provider=provider)
```

**Structured example (Go slog):**
```go
slog.Info("payment.processed",
    "amount", amount, "currency", currency,
    "user_id", userID, "duration_ms", durationMs)
```

Key principles for structured logs:
- Use dot-namespaced event names (`payment.processed`, `auth.failed`)
- Keep field names consistent across the codebase (agree on `user_id` vs `userId` vs `uid`)
- Never put variable data in the event name — put it in fields
- Add a `correlation_id` / `trace_id` on all logs for a given request or job run

---

## Correlation IDs in Async / Concurrent Code

Without correlation, logs from concurrent requests are interleaved and unreadable. Always propagate a request or job ID through all log statements in an async context.

**Pattern (Python with contextvars):**
```python
import uuid, contextvars
request_id: contextvars.ContextVar[str] = contextvars.ContextVar('request_id')

# At request entry point:
request_id.set(str(uuid.uuid4()))

# In any function:
log.debug("processing: request_id=%s user=%r", request_id.get(), user_id)
```

**Pattern (Go with context):**
```go
ctx = context.WithValue(ctx, "request_id", requestID)
// Pass ctx to all downstream functions and log from it:
slog.DebugContext(ctx, "processing", "user_id", userID)
```

---

## Log Level Guide

| Level | Use for |
|---|---|
| `TRACE` / `VERBOSE` | Extremely granular: every loop iteration, every byte read |
| `DEBUG` | Temporary debug instrumentation; detailed internal state |
| `INFO` | Normal milestones: request received, job started/completed |
| `WARN` | Unexpected but handled: retry triggered, fallback used, deprecated API called |
| `ERROR` | Failures that affect a user or job outcome; requires investigation |
| `FATAL` / `CRITICAL` | Unrecoverable failures; process will exit |

Temporary debug logs should use `DEBUG` or `TRACE`. When promoting a log to permanent, raise the level to `INFO` or higher if it represents a meaningful event.

# Webhook Delivery Module

A comprehensive webhook delivery system with target management, HMAC signature verification, exponential backoff retries, and dead letter queue support. All data is stored in-memory, making it suitable for testing, prototyping, and embedding in applications that don't require persistent storage.

## Module Features

1. **Webhook Target Management** - Register, update, and delete webhook subscription targets with configurable URLs, signing secrets, and retry strategies.
2. **HMAC Signature Verification** - Sign outgoing requests with SHA-256 HMAC so receivers can verify request integrity and authenticity.
3. **Exponential Backoff Retry** - Automatically retry failed deliveries with exponentially increasing delays up to a configurable maximum.
4. **Dead Letter Queue (DLQ)** - Messages that exceed the maximum retry count are moved to a dead letter queue with a complete failure history for later inspection and manual reprocessing.

## Core Classes and Responsibilities

### WebhookTarget
A data class representing a webhook subscription target.
- `id`: Unique identifier for the target
- `url`: The HTTP(S) endpoint to deliver to
- `signing_secret`: The secret key used for HMAC signing
- `retry_strategy`: The `RetryStrategy` for this target
- `is_active`: Whether the target is enabled for delivery

### RetryStrategy
Configuration for the exponential backoff retry behavior.
- `initial_delay`: Delay before the first retry (in seconds, default: 1.0)
- `backoff_multiplier`: Multiplier for each subsequent delay (default: 2.0)
- `max_delay`: Maximum delay between retries (default: 60.0)
- `max_retries`: **Maximum number of retries allowed *after* the initial attempt (default: 3). A value of 0 means no retries — only the initial attempt is made. The total number of delivery attempts will be `max_retries + 1` before moving to the dead letter queue.

### WebhookTargetRepository
In-memory storage and management of `WebhookTarget` instances.
- `register(url, signing_secret, retry_strategy)`: Register a new target
- `update(target_id, ...)`: Update a target's configuration
- `delete(target_id)`: Remove a target
- `get(target_id)`: Retrieve a target by ID
- `list_all()` / `list_active()`: List all or only active targets

### WebhookMessage
A data class representing a message to be delivered.
- `id`: Unique message identifier
- `target_id`: The target this message is for
- `event_type`: The type of event being delivered
- `payload`: The message body (dict)
- `delivery_attempts`: Number of delivery attempts made
- `status`: Current delivery status (`pending`, `delivering`, `success`, `failed`, `dead_letter`)
- `next_delivery_at`: Scheduled time for the next attempt

### DeadLetterMessage
A message that has been moved to the dead letter queue.
- `message_id`: The original message ID
- `target_id`: The target this message was for
- `event_type` / `payload`: The original event data
- `failure_count`: Number of failed attempts
- `last_error`: The most recent error message
- `delivery_history`: Complete list of `DeliveryAttempt` records

### DeliveryAttempt
A record of a single delivery attempt.
- `success`: Whether the attempt succeeded
- `attempted_at`: When the attempt was made
- `status_code`: HTTP status code received (if any)
- `error_message`: Error message (if failed)
- `response_body`: Response body from the server

### WebhookDeliveryEngine
The main orchestrator that ties everything together.
- `enqueue(target_id, event_type, payload)`: Create and queue a new message
- `deliver(message_id)`: Attempt delivery of a specific message. Raises `DeliveryNotReadyError` if the message's exponential backoff window has not elapsed yet (i.e. `now < next_delivery_at`).
- `deliver_all_ready()`: Deliver all messages whose retry window has elapsed
- `build_signed_request(message, target)`: Build a signed request for a message
- `get_pending_messages()` / `get_dead_letter_messages()`: Inspect queue state
- `get_delivery_history(message_id)`: Get all attempts for a message

### HttpTransport / InMemoryTransport
An abstraction over HTTP delivery. `InMemoryTransport` is used for testing and records all delivery attempts without making real network calls.

## Signature Mechanism

Outgoing requests are signed using **HMAC-SHA256** with the following construction:

```
signature = "v1=" + HMAC-SHA256(secret, timestamp + "." + canonical_json(payload))
```

The canonical JSON is produced by serializing the payload with sorted keys and no whitespace (`json.dumps(payload, sort_keys=True, separators=(",", ":"))`).

The following HTTP headers are set on every delivery:

| Header | Description |
|--------|-------------|
| `X-Webhook-Signature` | The HMAC signature in `v1=<hex>` format |
| `X-Webhook-Timestamp` | Unix timestamp (integer seconds) of the signature |
| `X-Webhook-Event-Type` | The event type string |
| `X-Webhook-Message-Id` | The unique message identifier |
| `Content-Type` | `application/json` |

### Verifying a Signature

On the receiving side, use `verify_signature()`:

```python
from solocoder_py.webhook_delivery import verify_signature

verify_signature(
    payload=received_payload,
    signing_secret="my-secret",
    timestamp=float(headers["X-Webhook-Timestamp"]),
    signature=headers["X-Webhook-Signature"],
    tolerance_seconds=300,
    current_time=time.time(),
)
```

This raises `SignatureVerificationError` if the signature is invalid, the version is unsupported, or the timestamp is outside the tolerance window.

## Retry and Dead Letter Mechanism

1. When a delivery fails (non-2xx status code or transport error), the engine records the failure and increments `delivery_attempts` (counting the initial attempt and all retries).
2. If `delivery_attempts <= max_retries`, the message is scheduled for a retry with an **exponentially increasing delay**:
   - Retry 1 (2nd attempt overall): delay = `initial_delay`
   - Retry 2 (3rd attempt overall): delay = `initial_delay * backoff_multiplier`
   - Retry N (N+1-th attempt overall): delay = `initial_delay * (backoff_multiplier ^ (N-1))`
   - All delays are capped at `max_delay`
3. The message's `next_delivery_at` is set to `now + delay`. Calling `deliver()` before this time elapses raises `DeliveryNotReadyError`.
4. If `delivery_attempts > max_retries` (i.e. all retries have been exhausted), the message is moved to the **dead letter queue** with:
   - A complete history of all delivery attempts
   - The last error message
   - The original payload and metadata
5. Example: with `max_retries=3`, the engine makes **4 total delivery attempts** (1 initial + 3 retries). After the 4th failure, the message is moved to the DLQ.
6. Messages in the DLQ can be inspected via `get_dead_letter_messages()` for manual reprocessing or debugging.

## Usage Examples

### Basic Setup and Delivery

```python
from solocoder_py.webhook_delivery import (
    InMemoryTransport,
    ManualClock,
    RetryStrategy,
    WebhookDeliveryEngine,
    WebhookTargetRepository,
)

# Initialize components
clock = ManualClock()
transport = InMemoryTransport()
repository = WebhookTargetRepository()
engine = WebhookDeliveryEngine(
    repository=repository,
    transport=transport,
    clock=clock,
)

# Register a target
target = repository.register(
    url="https://example.com/webhook",
    signing_secret="my-secret-key",
    retry_strategy=RetryStrategy(
        initial_delay=1.0,
        backoff_multiplier=2.0,
        max_delay=30.0,
        max_retries=3,
    ),
)

# Enqueue a message
message = engine.enqueue(
    target_id=target.id,
    event_type="order.created",
    payload={"order_id": "12345", "amount": 99.99},
)

# Deliver the message
result = engine.deliver(message.id)
print(result.status)  # "success"
```

### Handling Failures and Dead Letters

```python
# Configure transport to always fail
transport.set_should_fail(True, status_code=500, message="Server Down")

message = engine.enqueue(target.id, "payment.failed", {"id": "pay_001"})

# After 4 attempts (1 initial + 3 retries), message moves to DLQ
for _ in range(4):
    try:
        engine.deliver(message.id)
    except MaxRetriesExceededError:
        break
    clock.advance(60)  # Advance past retry delays

# Inspect the DLQ
dlq_messages = engine.get_dead_letter_messages()
print(dlq_messages[0].failure_count)  # 4
print(dlq_messages[0].last_error)     # "HTTP 500: Server Down"
```

### Signature Verification (Receiver Side)

```python
from solocoder_py.webhook_delivery import (
    SignatureVerificationError,
    verify_signature,
)

try:
    verify_signature(
        payload=request.json,
        signing_secret="shared-secret",
        timestamp=float(request.headers["X-Webhook-Timestamp"]),
        signature=request.headers["X-Webhook-Signature"],
        tolerance_seconds=300,
        current_time=time.time(),
    )
    # Signature is valid — process the webhook
    process_event(request.json)
except SignatureVerificationError as e:
    # Reject the request
    return Response(status=401)
```

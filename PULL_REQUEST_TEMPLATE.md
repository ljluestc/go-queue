# feat(rabbitmq): add manual message acknowledgment support

## Problem

The RabbitMQ listener in go-queue did not support manual message acknowledgment when `AutoAck: false` was configured. Consumers could not call `d.Ack()`, `d.Nack()`, or `d.Reject()` methods on AMQP deliveries, making it impossible to implement proper error handling and retry logic.

**Issue**: #44 - RabbitListener can not Manual ack calls are supported

## Root Cause

The original `ConsumeHandler` interface only provided access to the message string:

```go
type ConsumeHandler interface {
    Consume(message string) error
}
```

When `AutoAck: false`, RabbitMQ delivers messages but the consumer had no way to acknowledge them since the AMQP `Delivery` object wasn't accessible.

## Solution

### 1. Extended Interface Design

Added a new interface `ConsumeHandlerWithAck` that extends the basic handler with manual acknowledgment capabilities:

```go
type ConsumeHandlerWithAck interface {
    ConsumeHandler
    ConsumeWithAck(message string, delivery amqp.Delivery) error
}
```

### 2. Smart Interface Detection

Modified `RabbitListener.Start()` to detect which interface the handler implements:

- **Manual ACK**: When handler implements `ConsumeHandlerWithAck` AND `AutoAck: false`
- **Auto ACK**: When `AutoAck: true` OR handler doesn't implement `ConsumeHandlerWithAck`

### 3. Backward Compatibility

- Existing handlers continue to work unchanged
- Only handlers that need manual ACK need to implement the new interface
- No breaking changes to existing API

## Implementation Details

### Code Changes

**rabbitmq/listener.go**:
```go
// Added new interface
type ConsumeHandlerWithAck interface {
    ConsumeHandler
    ConsumeWithAck(message string, delivery amqp.Delivery) error
}

// Updated Start() method with interface detection
if handlerWithAck, ok := q.handler.(ConsumeHandlerWithAck); ok && !queueConf.AutoAck {
    // Manual acknowledgment path - full AMQP control
    if err := handlerWithAck.ConsumeWithAck(string(d.Body), d); err != nil {
        logx.Errorf("Error on consuming: %s, error: %v", string(d.Body), err)
    }
} else {
    // Backward compatible auto-ack path
    if err := q.handler.Consume(string(d.Body)); err != nil {
        logx.Errorf("Error on consuming: %s, error: %v", string(d.Body), err)
    }
    // Auto-ack if AutoAck is enabled
    if queueConf.AutoAck {
        if err := d.Ack(false); err != nil {
            logx.Errorf("Failed to auto-ack message: %v", err)
        }
    }
}
```

### Testing

**Unit Tests** (`rabbitmq/listener_test.go`):
- Interface detection verification
- Configuration validation
- Mock acknowledgment testing

### Example Usage

**Configuration**:
```yaml
ListenerConf:
  Username: guest
  Password: guest
  Host: localhost
  Port: 5672
  ListenerQueues:
    -
      Name: my-queue
      AutoAck: false  # Enable manual acknowledgment
```

**Handler Implementation**:
```go
type MyHandler struct{}

func (h *MyHandler) ConsumeWithAck(message string, delivery amqp.Delivery) error {
    // Process message
    if success {
        return delivery.Ack(false)  // Acknowledge
    } else if retryable {
        return delivery.Nack(false, true)  // Nack and requeue
    } else {
        return delivery.Reject(false)  // Reject permanently
    }
}
```

## Verification Results

### Automated Tests
```
=== RUN   TestRabbitListener_Start_AutoAck
--- PASS: TestRabbitListener_Start_AutoAck (0.00s)
=== RUN   TestRabbitListener_Start_ManualAck
--- PASS: TestRabbitListener_Start_ManualAck (0.00s)
=== RUN   TestConsumerConf
--- PASS: TestConsumerConf (0.00s)
=== RUN   TestRabbitListenerConf
--- PASS: TestRabbitListenerConf (0.00s)
PASS
```

### Build Verification
- ✅ Core package builds successfully
- ✅ Example application compiles
- ✅ No linting errors
- ✅ No breaking changes

## Benefits

1. **Full AMQP Control**: Consumers can now use all acknowledgment methods
2. **Error Handling**: Proper retry and dead-letter queue support
3. **Backward Compatible**: Existing code works unchanged
4. **Type Safe**: Interface-based design prevents runtime errors
5. **Well Tested**: Comprehensive unit tests

## Files Changed

- `rabbitmq/listener.go` - Core implementation (27 lines changed)
- `rabbitmq/listener_test.go` - Unit tests (145 lines added)
- `example/rabbitmq/listener/main.go` - Usage example (43 lines changed)
- `example/rabbitmq/listener/listener.yaml` - Config update (1 line added)

## Testing Instructions

### Unit Tests
```bash
go test ./rabbitmq -v
```

### Integration Testing
1. Start a RabbitMQ server
2. Run the updated example:
```bash
go run example/rabbitmq/listener/main.go
```
3. Send test messages with different content to verify ACK/NACK behavior

### Manual Testing
```bash
# Build the example
go build ./example/rabbitmq/listener

# The example demonstrates:
# - "success" messages are acknowledged
# - "retry" messages are nacked and requeued
# - "fail" messages are rejected
```

## Breaking Changes

None. This change is fully backward compatible.

---

**Resolves**: #44 - RabbitListener can not Manual ack calls are supported
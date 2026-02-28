# Operational Metrics System Guide

## Overview

The operational metrics system provides comprehensive tracking and monitoring of critical operational events in the Healthcare AI Assistant. This system enables operational maturity by tracking guard failures, escalations, intent mismatches, and other key events.

## Features

- **Thread-safe metrics collection** with configurable retention
- **Real-time aggregation** of operational events
- **Session-based tracking** for debugging specific user interactions
- **Time-windowed queries** for trend analysis
- **RESTful API** for dashboard integration
- **Automatic cleanup** of old events

## Metric Types

### 1. Guard Failures
Tracks when safety guards fail or trigger, including:
- `appointment_id_verification` - Appointment ID verification failures
- `confirmation_required` - Missing confirmation before destructive actions
- `hallucination_guard` - Hallucination detection triggers
- `slot_completeness` - Missing required slots

### 2. Escalations
Tracks when the system escalates to human operators:
- `safety_conflicts` - Multiple safety conflicts detected
- `validation_failures` - Repeated validation failures
- `name_gate_max_attempts` - Maximum name collection attempts exceeded

### 3. Intent Mismatches
Tracks unexpected intent classification changes that may indicate:
- User confusion
- Classification errors
- Ambiguous user input

### 4. Intent Overrides
Tracks when users explicitly change their intent mid-conversation:
- Pattern tracking (e.g., `booking→cancellation`)
- Confidence scores
- Frequency analysis

### 5. Safety Conflicts
Tracks safety-related issues:
- Unverified appointment IDs
- Missing confirmations
- Policy violations

### 6. Validation Failures
Tracks validation errors:
- Missing required slots
- Invalid data formats
- Business rule violations

## Usage

### Recording Metrics in Graph Nodes

```python
from app.core.metrics import (
    record_guard_failure,
    record_escalation,
    record_intent_override,
    record_safety_conflict,
    record_validation_failure
)

# In appointment_agent_node.py
def appointment_agent_node(state: AgentState) -> dict:
    # ... existing code ...
    
    # Record guard failure
    if not appointment_id_verified:
        record_guard_failure(
            "appointment_id_verification",
            user_id=state.get("user_id"),
            session_id=state.get("session_id"),
            appointment_id=requested_id,
            reason="ID not in verified list"
        )
    
    # Record escalation
    if safety_conflicts >= 2:
        record_escalation(
            "safety_conflicts",
            user_id=state.get("user_id"),
            session_id=state.get("session_id"),
            safety_conflict_count=safety_conflicts
        )
    
    # ... rest of code ...
```

### Recording Intent Overrides

```python
# In flow_planner_node.py
if clf_intent == override_candidate and clf_conf >= 0.7:
    record_intent_override(
        from_intent=active_intent,
        to_intent=override_candidate,
        confidence=clf_conf,
        user_id=state.get("user_id"),
        session_id=state.get("session_id"),
        user_text=last_user_text
    )
```

### Recording Safety Conflicts

```python
# In tool_executor_node.py
if not confirmed and tool_name in DESTRUCTIVE_TOOLS:
    record_safety_conflict(
        "missing_confirmation",
        user_id=state.get("user_id"),
        session_id=state.get("session_id"),
        tool_name=tool_name,
        intent=state.get("active_intent")
    )
```

## API Endpoints

### Get Metrics Summary
```bash
GET /api/metrics/summary?time_window_hours=24
```

Returns aggregated metrics including:
- Total events by type
- Guard failures by type
- Escalations by reason
- Intent override patterns
- Time-based metrics (last hour, last 24h)

### Get Recent Events
```bash
GET /api/metrics/events?metric_type=guard_failure&limit=100
```

Returns recent metric events with optional filtering by:
- `metric_type` - Filter by specific metric type
- `session_id` - Filter by session
- `limit` - Maximum number of events

### Get Session Metrics
```bash
GET /api/metrics/session/{session_id}
```

Returns all metrics for a specific session, useful for debugging.

### Get Guard Failures
```bash
GET /api/metrics/guard-failures?time_window_hours=24
```

Returns guard failure counts by type.

### Get Escalations
```bash
GET /api/metrics/escalations?time_window_hours=24
```

Returns escalation counts by reason.

### Get Intent Overrides
```bash
GET /api/metrics/intent-overrides?time_window_hours=24
```

Returns intent override patterns and counts.

### Health Check
```bash
GET /api/metrics/health
```

Returns metrics system health status.

## Example Dashboard Queries

### Monitor Guard Failure Rate
```python
import requests

response = requests.get("http://localhost:8000/api/metrics/summary?time_window_hours=1")
data = response.json()

guard_failure_rate = data["guard_failures_total"] / max(data["total_events"], 1)
print(f"Guard failure rate: {guard_failure_rate:.2%}")
```

### Track Escalation Trends
```python
# Get escalations for last 24 hours
response = requests.get("http://localhost:8000/api/metrics/escalations?time_window_hours=24")
escalations = response.json()

print("Escalations by reason:")
for reason, count in escalations.items():
    print(f"  {reason}: {count}")
```

### Analyze Intent Override Patterns
```python
response = requests.get("http://localhost:8000/api/metrics/intent-overrides?time_window_hours=24")
patterns = response.json()

print("Most common intent overrides:")
sorted_patterns = sorted(patterns.items(), key=lambda x: x[1], reverse=True)
for pattern, count in sorted_patterns[:5]:
    print(f"  {pattern}: {count}")
```

### Debug Specific Session
```python
session_id = "session_abc123"
response = requests.get(f"http://localhost:8000/api/metrics/session/{session_id}")
session_data = response.json()

print(f"Session {session_id} metrics:")
print(f"  Total events: {session_data['total_events']}")
print(f"  Events by type: {session_data['events_by_type']}")
```

## Integration with Monitoring Systems

### Prometheus Integration (Future)
The metrics system is designed to be easily integrated with Prometheus:

```python
from prometheus_client import Counter, Histogram

guard_failure_counter = Counter(
    'guard_failures_total',
    'Total guard failures',
    ['guard_type']
)

# In metrics collector
def record_guard_failure(self, guard_type: str, **kwargs):
    # ... existing code ...
    guard_failure_counter.labels(guard_type=guard_type).inc()
```

### Grafana Dashboard (Future)
Create dashboards to visualize:
- Guard failure rates over time
- Escalation frequency by reason
- Intent override patterns
- Session-level event timelines

## Best Practices

1. **Always include session_id** when available for better debugging
2. **Include user_id** for user-specific analysis (with PHI considerations)
3. **Add contextual details** in the `details` parameter for richer insights
4. **Use time windows** for trend analysis rather than all-time metrics
5. **Monitor escalation rates** as a key operational health indicator
6. **Track guard failure patterns** to identify systematic issues

## Performance Considerations

- Metrics collection is thread-safe and low-overhead
- Events are stored in memory with configurable retention (default 24 hours)
- Automatic cleanup prevents memory growth
- Maximum event limit prevents unbounded memory usage
- Lock contention is minimized with efficient data structures

## Testing

Run the comprehensive test suite:

```bash
cd backend
python -m pytest tests/test_operational_metrics.py -v
```

Tests cover:
- Metric event creation and serialization
- Thread-safe collection
- Time-windowed queries
- Session tracking
- Aggregation accuracy
- Cleanup functionality

## Future Enhancements

1. **Persistent storage** - Store metrics in database for long-term analysis
2. **Alerting** - Trigger alerts when thresholds are exceeded
3. **Anomaly detection** - Detect unusual patterns in metrics
4. **Export formats** - Support for Prometheus, StatsD, etc.
5. **Real-time streaming** - WebSocket-based real-time metrics updates
6. **Advanced analytics** - Correlation analysis, trend prediction

## Related Documentation

- [LANGGRAPH_PRODUCTION_ARCHITECTURE_REVIEW.md](./LANGGRAPH_PRODUCTION_ARCHITECTURE_REVIEW.md) - Architecture review that identified the need for operational metrics
- [to-do.md](./to-do.md) - Task tracking including metrics implementation

## Support

For questions or issues with the metrics system, contact the Advanced AI Systems Team.

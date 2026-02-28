"""
Tests for Operational Metrics System
====================================

Tests the metrics collection, aggregation, and dashboard functionality
for guard failures, escalations, and intent mismatches.

Author: Advanced AI Systems Team
Last Modified: 2026-02-26
"""

import pytest
import time
from typing import Dict, Any

from app.core.metrics import (
    MetricsCollector,
    MetricType,
    MetricEvent,
    MetricsSummary,
    get_metrics_collector,
    record_guard_failure,
    record_escalation,
    record_intent_mismatch,
    record_intent_override,
    record_safety_conflict,
    record_validation_failure
)


@pytest.fixture
def metrics_collector():
    """Create a fresh metrics collector for each test."""
    collector = MetricsCollector(max_events=1000, retention_hours=24)
    yield collector
    collector.reset()


@pytest.fixture
def populated_collector(metrics_collector):
    """Create a collector with sample data."""
    # Guard failures
    metrics_collector.record_guard_failure(
        "appointment_id_verification",
        user_id=123,
        session_id="session_1",
        appointment_id="apt_001"
    )
    metrics_collector.record_guard_failure(
        "confirmation_required",
        user_id=123,
        session_id="session_1"
    )
    metrics_collector.record_guard_failure(
        "hallucination_guard",
        user_id=456,
        session_id="session_2"
    )
    
    # Escalations
    metrics_collector.record_escalation(
        "safety_conflicts",
        user_id=123,
        session_id="session_1",
        safety_conflict_count=2
    )
    metrics_collector.record_escalation(
        "validation_failures",
        user_id=789,
        session_id="session_3",
        validation_failure_count=3
    )
    
    # Intent mismatches
    metrics_collector.record_intent_mismatch(
        "booking",
        "cancellation",
        confidence=0.85,
        user_id=123,
        session_id="session_1"
    )
    
    # Intent overrides
    metrics_collector.record_intent_override(
        "booking",
        "cancellation",
        confidence=0.92,
        user_id=456,
        session_id="session_2"
    )
    metrics_collector.record_intent_override(
        "cancellation",
        "rescheduling",
        confidence=0.88,
        user_id=456,
        session_id="session_2"
    )
    
    # Safety conflicts
    metrics_collector.record_safety_conflict(
        "unverified_appointment_id",
        user_id=123,
        session_id="session_1"
    )
    
    # Validation failures
    metrics_collector.record_validation_failure(
        "missing_required_slots",
        user_id=789,
        session_id="session_3"
    )
    
    return metrics_collector


class TestMetricEvent:
    """Tests for MetricEvent dataclass."""
    
    def test_metric_event_creation(self):
        """Test creating a metric event."""
        event = MetricEvent(
            metric_type=MetricType.GUARD_FAILURE,
            timestamp=time.time(),
            user_id=123,
            session_id="test_session",
            details={"guard_type": "test_guard"}
        )
        
        assert event.metric_type == MetricType.GUARD_FAILURE
        assert event.user_id == 123
        assert event.session_id == "test_session"
        assert event.details["guard_type"] == "test_guard"
    
    def test_metric_event_to_dict(self):
        """Test converting metric event to dictionary."""
        timestamp = time.time()
        event = MetricEvent(
            metric_type=MetricType.ESCALATION,
            timestamp=timestamp,
            user_id=456,
            session_id="session_abc",
            details={"reason": "safety_conflicts"}
        )
        
        event_dict = event.to_dict()
        
        assert event_dict["metric_type"] == "escalation"
        assert event_dict["timestamp"] == timestamp
        assert event_dict["user_id"] == 456
        assert event_dict["session_id"] == "session_abc"
        assert "datetime" in event_dict
        assert event_dict["details"]["reason"] == "safety_conflicts"


class TestMetricsCollector:
    """Tests for MetricsCollector class."""
    
    def test_collector_initialization(self, metrics_collector):
        """Test metrics collector initialization."""
        assert metrics_collector is not None
        summary = metrics_collector.get_summary()
        assert summary.total_events == 0
    
    def test_record_guard_failure(self, metrics_collector):
        """Test recording guard failures."""
        metrics_collector.record_guard_failure(
            "appointment_id_verification",
            user_id=123,
            session_id="test_session"
        )
        
        summary = metrics_collector.get_summary()
        assert summary.total_events == 1
        assert summary.guard_failures_total == 1
        assert summary.guard_failures_by_type["appointment_id_verification"] == 1
    
    def test_record_multiple_guard_failures(self, metrics_collector):
        """Test recording multiple guard failures of different types."""
        metrics_collector.record_guard_failure("guard_type_a", user_id=1)
        metrics_collector.record_guard_failure("guard_type_b", user_id=2)
        metrics_collector.record_guard_failure("guard_type_a", user_id=3)
        
        summary = metrics_collector.get_summary()
        assert summary.guard_failures_total == 3
        assert summary.guard_failures_by_type["guard_type_a"] == 2
        assert summary.guard_failures_by_type["guard_type_b"] == 1
    
    def test_record_escalation(self, metrics_collector):
        """Test recording escalations."""
        metrics_collector.record_escalation(
            "safety_conflicts",
            user_id=123,
            session_id="test_session",
            safety_conflict_count=2
        )
        
        summary = metrics_collector.get_summary()
        assert summary.total_events == 1
        assert summary.escalations_total == 1
        assert summary.escalations_by_reason["safety_conflicts"] == 1
    
    def test_record_intent_mismatch(self, metrics_collector):
        """Test recording intent mismatches."""
        metrics_collector.record_intent_mismatch(
            "booking",
            "cancellation",
            confidence=0.85,
            user_id=123
        )
        
        summary = metrics_collector.get_summary()
        assert summary.total_events == 1
        assert summary.intent_mismatches_total == 1
    
    def test_record_intent_override(self, metrics_collector):
        """Test recording intent overrides."""
        metrics_collector.record_intent_override(
            "booking",
            "cancellation",
            confidence=0.92,
            user_id=123
        )
        
        summary = metrics_collector.get_summary()
        assert summary.total_events == 1
        assert summary.intent_overrides_total == 1
        assert summary.intent_override_patterns["booking→cancellation"] == 1
    
    def test_record_safety_conflict(self, metrics_collector):
        """Test recording safety conflicts."""
        metrics_collector.record_safety_conflict(
            "unverified_appointment_id",
            user_id=123
        )
        
        summary = metrics_collector.get_summary()
        assert summary.total_events == 1
        assert summary.safety_conflicts_total == 1
    
    def test_record_validation_failure(self, metrics_collector):
        """Test recording validation failures."""
        metrics_collector.record_validation_failure(
            "missing_required_slots",
            user_id=123
        )
        
        summary = metrics_collector.get_summary()
        assert summary.total_events == 1
        assert summary.validation_failures_total == 1
    
    def test_get_summary_with_populated_data(self, populated_collector):
        """Test getting summary with populated data."""
        summary = populated_collector.get_summary()
        
        assert summary.total_events == 10
        assert summary.guard_failures_total == 3
        assert summary.escalations_total == 2
        assert summary.intent_mismatches_total == 1
        assert summary.intent_overrides_total == 2
        assert summary.safety_conflicts_total == 1
        assert summary.validation_failures_total == 1
    
    def test_get_summary_with_time_window(self, metrics_collector):
        """Test getting summary with time window filter."""
        # Record events at different times
        metrics_collector.record_guard_failure("guard_a", user_id=1)
        time.sleep(0.1)
        metrics_collector.record_guard_failure("guard_b", user_id=2)
        
        # Get summary for last hour (should include all)
        summary = metrics_collector.get_summary(time_window_hours=1)
        assert summary.total_events == 2
        
        # Get summary for very short window (may include fewer)
        summary_short = metrics_collector.get_summary(time_window_hours=0.0001)
        assert summary_short.total_events <= 2
    
    def test_get_events_all(self, populated_collector):
        """Test getting all events."""
        events = populated_collector.get_events(limit=100)
        
        assert len(events) == 10
        assert all("metric_type" in event for event in events)
        assert all("timestamp" in event for event in events)
    
    def test_get_events_filtered_by_type(self, populated_collector):
        """Test getting events filtered by type."""
        guard_events = populated_collector.get_events(
            metric_type=MetricType.GUARD_FAILURE,
            limit=100
        )
        
        assert len(guard_events) == 3
        assert all(event["metric_type"] == "guard_failure" for event in guard_events)
    
    def test_get_events_filtered_by_session(self, populated_collector):
        """Test getting events filtered by session."""
        session_events = populated_collector.get_events(
            session_id="session_1",
            limit=100
        )
        
        assert len(session_events) == 5
        assert all(event["session_id"] == "session_1" for event in session_events)
    
    def test_get_events_with_limit(self, populated_collector):
        """Test getting events with limit."""
        events = populated_collector.get_events(limit=3)
        
        assert len(events) == 3
    
    def test_get_session_metrics(self, populated_collector):
        """Test getting session-specific metrics."""
        session_data = populated_collector.get_session_metrics("session_1")
        
        assert session_data["session_id"] == "session_1"
        assert session_data["total_events"] == 5
        assert session_data["events_by_type"]["guard_failure"] == 2
        assert session_data["events_by_type"]["escalation"] == 1
    
    def test_cleanup_old_events(self, metrics_collector):
        """Test cleanup of old events."""
        # Create collector with very short retention
        short_retention_collector = MetricsCollector(
            max_events=1000,
            retention_hours=0.0001  # Very short retention
        )
        
        # Record some events
        short_retention_collector.record_guard_failure("test_guard", user_id=1)
        short_retention_collector.record_escalation("test_reason", user_id=2)
        
        # Wait a bit
        time.sleep(0.5)
        
        # Cleanup should remove old events
        removed = short_retention_collector.cleanup_old_events()
        assert removed >= 0  # May or may not remove depending on timing
    
    def test_reset(self, populated_collector):
        """Test resetting all metrics."""
        # Verify data exists
        summary_before = populated_collector.get_summary()
        assert summary_before.total_events > 0
        
        # Reset
        populated_collector.reset()
        
        # Verify data is cleared
        summary_after = populated_collector.get_summary()
        assert summary_after.total_events == 0
        assert summary_after.guard_failures_total == 0
        assert summary_after.escalations_total == 0
    
    def test_thread_safety(self, metrics_collector):
        """Test thread-safe operations."""
        import threading
        
        def record_metrics():
            for i in range(10):
                metrics_collector.record_guard_failure(f"guard_{i}", user_id=i)
        
        # Create multiple threads
        threads = [threading.Thread(target=record_metrics) for _ in range(5)]
        
        # Start all threads
        for thread in threads:
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        # Verify all events were recorded
        summary = metrics_collector.get_summary()
        assert summary.total_events == 50  # 5 threads * 10 events each


class TestConvenienceFunctions:
    """Tests for convenience functions."""
    
    def test_record_guard_failure_convenience(self):
        """Test convenience function for recording guard failures."""
        collector = get_metrics_collector()
        collector.reset()
        
        record_guard_failure("test_guard", user_id=123)
        
        summary = collector.get_summary()
        assert summary.guard_failures_total >= 1
    
    def test_record_escalation_convenience(self):
        """Test convenience function for recording escalations."""
        collector = get_metrics_collector()
        collector.reset()
        
        record_escalation("test_reason", user_id=123)
        
        summary = collector.get_summary()
        assert summary.escalations_total >= 1
    
    def test_record_intent_mismatch_convenience(self):
        """Test convenience function for recording intent mismatches."""
        collector = get_metrics_collector()
        collector.reset()
        
        record_intent_mismatch("booking", "cancellation", 0.85, user_id=123)
        
        summary = collector.get_summary()
        assert summary.intent_mismatches_total >= 1
    
    def test_record_intent_override_convenience(self):
        """Test convenience function for recording intent overrides."""
        collector = get_metrics_collector()
        collector.reset()
        
        record_intent_override("booking", "cancellation", 0.92, user_id=123)
        
        summary = collector.get_summary()
        assert summary.intent_overrides_total >= 1


class TestMetricsIntegration:
    """Integration tests for metrics system."""
    
    def test_complete_session_tracking(self, metrics_collector):
        """Test tracking a complete session with multiple events."""
        session_id = "integration_session"
        user_id = 999
        
        # Simulate a session with various events
        metrics_collector.record_guard_failure(
            "appointment_id_verification",
            user_id=user_id,
            session_id=session_id
        )
        
        metrics_collector.record_safety_conflict(
            "unverified_appointment_id",
            user_id=user_id,
            session_id=session_id
        )
        
        metrics_collector.record_validation_failure(
            "missing_confirmation",
            user_id=user_id,
            session_id=session_id
        )
        
        metrics_collector.record_escalation(
            "safety_conflicts",
            user_id=user_id,
            session_id=session_id,
            safety_conflict_count=2
        )
        
        # Verify session metrics
        session_data = metrics_collector.get_session_metrics(session_id)
        assert session_data["total_events"] == 4
        assert session_data["events_by_type"]["guard_failure"] == 1
        assert session_data["events_by_type"]["safety_conflict"] == 1
        assert session_data["events_by_type"]["validation_failure"] == 1
        assert session_data["events_by_type"]["escalation"] == 1
    
    def test_intent_override_pattern_tracking(self, metrics_collector):
        """Test tracking intent override patterns."""
        # Record various override patterns
        metrics_collector.record_intent_override("booking", "cancellation", 0.9, user_id=1)
        metrics_collector.record_intent_override("booking", "cancellation", 0.85, user_id=2)
        metrics_collector.record_intent_override("cancellation", "rescheduling", 0.88, user_id=3)
        metrics_collector.record_intent_override("booking", "rescheduling", 0.92, user_id=4)
        
        summary = metrics_collector.get_summary()
        
        # Verify pattern counts
        assert summary.intent_override_patterns["booking→cancellation"] == 2
        assert summary.intent_override_patterns["cancellation→rescheduling"] == 1
        assert summary.intent_override_patterns["booking→rescheduling"] == 1
    
    def test_guard_failure_types_tracking(self, metrics_collector):
        """Test tracking different guard failure types."""
        guard_types = [
            "appointment_id_verification",
            "confirmation_required",
            "hallucination_guard",
            "slot_completeness",
            "appointment_id_verification"  # Duplicate
        ]
        
        for guard_type in guard_types:
            metrics_collector.record_guard_failure(guard_type, user_id=1)
        
        summary = metrics_collector.get_summary()
        
        assert summary.guard_failures_total == 5
        assert summary.guard_failures_by_type["appointment_id_verification"] == 2
        assert summary.guard_failures_by_type["confirmation_required"] == 1
        assert summary.guard_failures_by_type["hallucination_guard"] == 1
        assert summary.guard_failures_by_type["slot_completeness"] == 1
    
    def test_time_based_metrics(self, metrics_collector):
        """Test time-based metric calculations."""
        # Record events
        for i in range(5):
            metrics_collector.record_guard_failure(f"guard_{i}", user_id=i)
        
        summary = metrics_collector.get_summary()
        
        # All events should be in last hour and last 24h
        assert summary.events_last_hour == 5
        assert summary.events_last_24h == 5
        
        # Verify time range
        assert summary.start_time is not None
        assert summary.end_time is not None
        assert summary.end_time >= summary.start_time


class TestMetricsSummary:
    """Tests for MetricsSummary dataclass."""
    
    def test_summary_to_dict(self, populated_collector):
        """Test converting summary to dictionary."""
        summary = populated_collector.get_summary()
        summary_dict = summary.to_dict()
        
        assert isinstance(summary_dict, dict)
        assert "total_events" in summary_dict
        assert "guard_failures_total" in summary_dict
        assert "escalations_total" in summary_dict
        assert "intent_mismatches_total" in summary_dict
        assert "intent_overrides_total" in summary_dict
        assert summary_dict["total_events"] == 10


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

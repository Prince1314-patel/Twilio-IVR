"""
Operational Metrics System
==========================

Tracks operational metrics for guard failures, escalations, and intent mismatches
to build operational maturity and enable monitoring dashboards.

This module provides:
- Metrics collection for critical operational events
- Thread-safe counters and gauges
- Metrics export for monitoring systems
- Historical tracking with time-series data

Author: Advanced AI Systems Team
Last Modified: 2026-02-26
"""

import time
import threading
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from collections import defaultdict, deque
from enum import Enum

from app.core.logger_config import get_ai_agent_logger

logger = get_ai_agent_logger()


class MetricType(Enum):
    """Types of operational metrics tracked."""
    GUARD_FAILURE = "guard_failure"
    ESCALATION = "escalation"
    INTENT_MISMATCH = "intent_mismatch"
    INTENT_OVERRIDE = "intent_override"
    VALIDATION_FAILURE = "validation_failure"
    SAFETY_CONFLICT = "safety_conflict"
    NAME_GATE_BLOCK = "name_gate_block"
    TOOL_EXECUTION_ERROR = "tool_execution_error"


@dataclass
class MetricEvent:
    """Represents a single metric event."""
    metric_type: MetricType
    timestamp: float
    user_id: Optional[int] = None
    session_id: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "metric_type": self.metric_type.value,
            "timestamp": self.timestamp,
            "datetime": datetime.fromtimestamp(self.timestamp).isoformat(),
            "user_id": self.user_id,
            "session_id": self.session_id,
            "details": self.details
        }


@dataclass
class MetricsSummary:
    """Summary statistics for operational metrics."""
    total_events: int = 0
    events_by_type: Dict[str, int] = field(default_factory=dict)
    events_last_hour: int = 0
    events_last_24h: int = 0
    
    # Guard-specific metrics
    guard_failures_total: int = 0
    guard_failures_by_type: Dict[str, int] = field(default_factory=dict)
    
    # Escalation metrics
    escalations_total: int = 0
    escalations_by_reason: Dict[str, int] = field(default_factory=dict)
    
    # Intent metrics
    intent_mismatches_total: int = 0
    intent_overrides_total: int = 0
    intent_override_patterns: Dict[str, int] = field(default_factory=dict)
    
    # Safety metrics
    safety_conflicts_total: int = 0
    validation_failures_total: int = 0
    
    # Time range
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return asdict(self)


class MetricsCollector:
    """
    Thread-safe metrics collector for operational monitoring.
    
    Collects and aggregates metrics about guard failures, escalations,
    intent mismatches, and other operational events.
    """
    
    def __init__(self, max_events: int = 10000, retention_hours: int = 24):
        """
        Initialize metrics collector.
        
        Args:
            max_events: Maximum number of events to keep in memory
            retention_hours: Hours to retain events before cleanup
        """
        self._lock = threading.RLock()
        self._events: deque = deque(maxlen=max_events)
        self._retention_seconds = retention_hours * 3600
        
        # Counters by type
        self._counters: Dict[MetricType, int] = defaultdict(int)
        
        # Detailed tracking
        self._guard_failures: Dict[str, int] = defaultdict(int)
        self._escalation_reasons: Dict[str, int] = defaultdict(int)
        self._intent_patterns: Dict[str, int] = defaultdict(int)
        
        # Session tracking
        self._session_metrics: Dict[str, List[MetricEvent]] = defaultdict(list)
        
        logger.info("[METRICS] Metrics collector initialized (max_events=%d, retention=%dh)",
                   max_events, retention_hours)
    
    def record_guard_failure(self, guard_type: str, user_id: Optional[int] = None,
                           session_id: Optional[str] = None, **details) -> None:
        """
        Record a guard failure event.
        
        Args:
            guard_type: Type of guard that failed (e.g., "appointment_id_verification",
                       "confirmation_required", "hallucination_guard")
            user_id: User ID if available
            session_id: Session ID if available
            **details: Additional context about the failure
        """
        event = MetricEvent(
            metric_type=MetricType.GUARD_FAILURE,
            timestamp=time.time(),
            user_id=user_id,
            session_id=session_id,
            details={"guard_type": guard_type, **details}
        )
        
        with self._lock:
            self._events.append(event)
            self._counters[MetricType.GUARD_FAILURE] += 1
            self._guard_failures[guard_type] += 1
            
            if session_id:
                self._session_metrics[session_id].append(event)
        
        logger.warning("[METRICS] Guard failure recorded: %s (user=%s, session=%s)",
                      guard_type, user_id, session_id)
    
    def record_escalation(self, reason: str, user_id: Optional[int] = None,
                         session_id: Optional[str] = None, **details) -> None:
        """
        Record an escalation event.
        
        Args:
            reason: Reason for escalation (e.g., "safety_conflicts", "validation_failures",
                   "name_gate_max_attempts")
            user_id: User ID if available
            session_id: Session ID if available
            **details: Additional context about the escalation
        """
        event = MetricEvent(
            metric_type=MetricType.ESCALATION,
            timestamp=time.time(),
            user_id=user_id,
            session_id=session_id,
            details={"reason": reason, **details}
        )
        
        with self._lock:
            self._events.append(event)
            self._counters[MetricType.ESCALATION] += 1
            self._escalation_reasons[reason] += 1
            
            if session_id:
                self._session_metrics[session_id].append(event)
        
        logger.critical("[METRICS] Escalation recorded: %s (user=%s, session=%s)",
                       reason, user_id, session_id)
    
    def record_intent_mismatch(self, expected_intent: str, actual_intent: str,
                              confidence: float, user_id: Optional[int] = None,
                              session_id: Optional[str] = None, **details) -> None:
        """
        Record an intent classification mismatch.
        
        Args:
            expected_intent: Expected or previous intent
            actual_intent: Newly classified intent
            confidence: Classification confidence
            user_id: User ID if available
            session_id: Session ID if available
            **details: Additional context
        """
        event = MetricEvent(
            metric_type=MetricType.INTENT_MISMATCH,
            timestamp=time.time(),
            user_id=user_id,
            session_id=session_id,
            details={
                "expected_intent": expected_intent,
                "actual_intent": actual_intent,
                "confidence": confidence,
                **details
            }
        )
        
        with self._lock:
            self._events.append(event)
            self._counters[MetricType.INTENT_MISMATCH] += 1
            
            if session_id:
                self._session_metrics[session_id].append(event)
        
        logger.info("[METRICS] Intent mismatch: %s → %s (conf=%.2f, user=%s, session=%s)",
                   expected_intent, actual_intent, confidence, user_id, session_id)
    
    def record_intent_override(self, from_intent: str, to_intent: str,
                              confidence: float, user_id: Optional[int] = None,
                              session_id: Optional[str] = None, **details) -> None:
        """
        Record an intent override event.
        
        Args:
            from_intent: Original intent
            to_intent: Override intent
            confidence: Classification confidence
            user_id: User ID if available
            session_id: Session ID if available
            **details: Additional context
        """
        pattern = f"{from_intent}→{to_intent}"
        
        event = MetricEvent(
            metric_type=MetricType.INTENT_OVERRIDE,
            timestamp=time.time(),
            user_id=user_id,
            session_id=session_id,
            details={
                "from_intent": from_intent,
                "to_intent": to_intent,
                "confidence": confidence,
                "pattern": pattern,
                **details
            }
        )
        
        with self._lock:
            self._events.append(event)
            self._counters[MetricType.INTENT_OVERRIDE] += 1
            self._intent_patterns[pattern] += 1
            
            if session_id:
                self._session_metrics[session_id].append(event)
        
        logger.info("[METRICS] Intent override: %s (conf=%.2f, user=%s, session=%s)",
                   pattern, confidence, user_id, session_id)
    
    def record_safety_conflict(self, conflict_type: str, user_id: Optional[int] = None,
                              session_id: Optional[str] = None, **details) -> None:
        """Record a safety conflict event."""
        event = MetricEvent(
            metric_type=MetricType.SAFETY_CONFLICT,
            timestamp=time.time(),
            user_id=user_id,
            session_id=session_id,
            details={"conflict_type": conflict_type, **details}
        )
        
        with self._lock:
            self._events.append(event)
            self._counters[MetricType.SAFETY_CONFLICT] += 1
            
            if session_id:
                self._session_metrics[session_id].append(event)
        
        logger.warning("[METRICS] Safety conflict: %s (user=%s, session=%s)",
                      conflict_type, user_id, session_id)
    
    def record_validation_failure(self, validation_type: str, user_id: Optional[int] = None,
                                 session_id: Optional[str] = None, **details) -> None:
        """Record a validation failure event."""
        event = MetricEvent(
            metric_type=MetricType.VALIDATION_FAILURE,
            timestamp=time.time(),
            user_id=user_id,
            session_id=session_id,
            details={"validation_type": validation_type, **details}
        )
        
        with self._lock:
            self._events.append(event)
            self._counters[MetricType.VALIDATION_FAILURE] += 1
            
            if session_id:
                self._session_metrics[session_id].append(event)
        
        logger.warning("[METRICS] Validation failure: %s (user=%s, session=%s)",
                      validation_type, user_id, session_id)
    
    def get_summary(self, time_window_hours: Optional[int] = None) -> MetricsSummary:
        """
        Get summary statistics for all metrics.
        
        Args:
            time_window_hours: Optional time window to filter events (None = all time)
            
        Returns:
            MetricsSummary: Aggregated metrics summary
        """
        with self._lock:
            current_time = time.time()
            cutoff_time = current_time - (time_window_hours * 3600) if time_window_hours else 0
            
            # Filter events by time window
            filtered_events = [e for e in self._events if e.timestamp >= cutoff_time]
            
            summary = MetricsSummary()
            summary.total_events = len(filtered_events)
            summary.start_time = filtered_events[0].timestamp if filtered_events else None
            summary.end_time = current_time
            
            # Count events by type
            for event in filtered_events:
                event_type = event.metric_type.value
                summary.events_by_type[event_type] = summary.events_by_type.get(event_type, 0) + 1
                
                # Aggregate specific metrics
                if event.metric_type == MetricType.GUARD_FAILURE:
                    summary.guard_failures_total += 1
                    guard_type = event.details.get("guard_type", "unknown")
                    summary.guard_failures_by_type[guard_type] = \
                        summary.guard_failures_by_type.get(guard_type, 0) + 1
                
                elif event.metric_type == MetricType.ESCALATION:
                    summary.escalations_total += 1
                    reason = event.details.get("reason", "unknown")
                    summary.escalations_by_reason[reason] = \
                        summary.escalations_by_reason.get(reason, 0) + 1
                
                elif event.metric_type == MetricType.INTENT_MISMATCH:
                    summary.intent_mismatches_total += 1
                
                elif event.metric_type == MetricType.INTENT_OVERRIDE:
                    summary.intent_overrides_total += 1
                    pattern = event.details.get("pattern", "unknown")
                    summary.intent_override_patterns[pattern] = \
                        summary.intent_override_patterns.get(pattern, 0) + 1
                
                elif event.metric_type == MetricType.SAFETY_CONFLICT:
                    summary.safety_conflicts_total += 1
                
                elif event.metric_type == MetricType.VALIDATION_FAILURE:
                    summary.validation_failures_total += 1
            
            # Calculate time-based metrics
            one_hour_ago = current_time - 3600
            twenty_four_hours_ago = current_time - 86400
            
            summary.events_last_hour = sum(1 for e in filtered_events if e.timestamp >= one_hour_ago)
            summary.events_last_24h = sum(1 for e in filtered_events if e.timestamp >= twenty_four_hours_ago)
            
            return summary
    
    def get_events(self, metric_type: Optional[MetricType] = None,
                  session_id: Optional[str] = None,
                  limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get recent events, optionally filtered.
        
        Args:
            metric_type: Filter by metric type
            session_id: Filter by session ID
            limit: Maximum number of events to return
            
        Returns:
            List of event dictionaries
        """
        with self._lock:
            events = list(self._events)
            
            # Filter by metric type
            if metric_type:
                events = [e for e in events if e.metric_type == metric_type]
            
            # Filter by session
            if session_id:
                events = [e for e in events if e.session_id == session_id]
            
            # Sort by timestamp (most recent first) and limit
            events.sort(key=lambda e: e.timestamp, reverse=True)
            events = events[:limit]
            
            return [e.to_dict() for e in events]
    
    def get_session_metrics(self, session_id: str) -> Dict[str, Any]:
        """
        Get all metrics for a specific session.
        
        Args:
            session_id: Session ID to query
            
        Returns:
            Dictionary with session metrics
        """
        with self._lock:
            session_events = self._session_metrics.get(session_id, [])
            
            return {
                "session_id": session_id,
                "total_events": len(session_events),
                "events_by_type": {
                    metric_type.value: sum(1 for e in session_events if e.metric_type == metric_type)
                    for metric_type in MetricType
                },
                "events": [e.to_dict() for e in session_events]
            }
    
    def cleanup_old_events(self) -> int:
        """
        Remove events older than retention period.
        
        Returns:
            Number of events removed
        """
        with self._lock:
            current_time = time.time()
            cutoff_time = current_time - self._retention_seconds
            
            initial_count = len(self._events)
            
            # Filter out old events
            self._events = deque(
                (e for e in self._events if e.timestamp >= cutoff_time),
                maxlen=self._events.maxlen
            )
            
            removed_count = initial_count - len(self._events)
            
            if removed_count > 0:
                logger.info("[METRICS] Cleaned up %d old events", removed_count)
            
            return removed_count
    
    def reset(self) -> None:
        """Reset all metrics (useful for testing)."""
        with self._lock:
            self._events.clear()
            self._counters.clear()
            self._guard_failures.clear()
            self._escalation_reasons.clear()
            self._intent_patterns.clear()
            self._session_metrics.clear()
            
            logger.info("[METRICS] All metrics reset")


# Global metrics collector instance
_metrics_collector: Optional[MetricsCollector] = None
_collector_lock = threading.Lock()


def get_metrics_collector() -> MetricsCollector:
    """
    Get the global metrics collector instance.
    
    Returns:
        MetricsCollector: Global metrics collector
    """
    global _metrics_collector
    
    if _metrics_collector is None:
        with _collector_lock:
            if _metrics_collector is None:
                _metrics_collector = MetricsCollector()
    
    return _metrics_collector


# Convenience functions for easy metric recording
def record_guard_failure(guard_type: str, **kwargs) -> None:
    """Record a guard failure."""
    get_metrics_collector().record_guard_failure(guard_type, **kwargs)


def record_escalation(reason: str, **kwargs) -> None:
    """Record an escalation."""
    get_metrics_collector().record_escalation(reason, **kwargs)


def record_intent_mismatch(expected: str, actual: str, confidence: float, **kwargs) -> None:
    """Record an intent mismatch."""
    get_metrics_collector().record_intent_mismatch(expected, actual, confidence, **kwargs)


def record_intent_override(from_intent: str, to_intent: str, confidence: float, **kwargs) -> None:
    """Record an intent override."""
    get_metrics_collector().record_intent_override(from_intent, to_intent, confidence, **kwargs)


def record_safety_conflict(conflict_type: str, **kwargs) -> None:
    """Record a safety conflict."""
    get_metrics_collector().record_safety_conflict(conflict_type, **kwargs)


def record_validation_failure(validation_type: str, **kwargs) -> None:
    """Record a validation failure."""
    get_metrics_collector().record_validation_failure(validation_type, **kwargs)

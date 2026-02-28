"""
Operational Metrics API
=======================

FastAPI endpoints for operational metrics dashboard.

Provides access to:
- Guard failure metrics
- Escalation metrics
- Intent mismatch/override metrics
- Safety and validation metrics
- Session-specific metrics

Author: Advanced AI Systems Team
Last Modified: 2026-02-26
"""

from fastapi import APIRouter, Query, HTTPException
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field

from app.core.metrics import (
    get_metrics_collector,
    MetricType,
    MetricsSummary
)
from app.core.logger_config import get_application_logger

logger = get_application_logger()
router = APIRouter(prefix="/metrics", tags=["metrics"])


class MetricsSummaryResponse(BaseModel):
    """Response model for metrics summary."""
    total_events: int
    events_by_type: Dict[str, int]
    events_last_hour: int
    events_last_24h: int
    guard_failures_total: int
    guard_failures_by_type: Dict[str, int]
    escalations_total: int
    escalations_by_reason: Dict[str, int]
    intent_mismatches_total: int
    intent_overrides_total: int
    intent_override_patterns: Dict[str, int]
    safety_conflicts_total: int
    validation_failures_total: int
    start_time: Optional[float]
    end_time: Optional[float]


class MetricEventResponse(BaseModel):
    """Response model for individual metric events."""
    metric_type: str
    timestamp: float
    datetime: str
    user_id: Optional[int]
    session_id: Optional[str]
    details: Dict[str, Any]


class SessionMetricsResponse(BaseModel):
    """Response model for session-specific metrics."""
    session_id: str
    total_events: int
    events_by_type: Dict[str, int]
    events: List[MetricEventResponse]


@router.get("/summary", response_model=MetricsSummaryResponse)
async def get_metrics_summary(
    time_window_hours: Optional[int] = Query(
        None,
        description="Time window in hours (None = all time)",
        ge=1,
        le=168  # Max 1 week
    )
) -> MetricsSummaryResponse:
    """
    Get aggregated metrics summary.
    
    Returns summary statistics for all operational metrics including:
    - Guard failures by type
    - Escalations by reason
    - Intent mismatches and overrides
    - Safety conflicts and validation failures
    
    Args:
        time_window_hours: Optional time window to filter metrics
        
    Returns:
        Aggregated metrics summary
    """
    try:
        collector = get_metrics_collector()
        summary = collector.get_summary(time_window_hours=time_window_hours)
        
        logger.info("[METRICS API] Summary requested (window=%s hours)", time_window_hours)
        
        return MetricsSummaryResponse(**summary.to_dict())
    
    except Exception as e:
        logger.error("[METRICS API] Error getting summary: %s", str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve metrics summary")


@router.get("/events", response_model=List[MetricEventResponse])
async def get_metric_events(
    metric_type: Optional[str] = Query(
        None,
        description="Filter by metric type"
    ),
    session_id: Optional[str] = Query(
        None,
        description="Filter by session ID"
    ),
    limit: int = Query(
        100,
        description="Maximum number of events to return",
        ge=1,
        le=1000
    )
) -> List[MetricEventResponse]:
    """
    Get recent metric events with optional filtering.
    
    Args:
        metric_type: Filter by specific metric type
        session_id: Filter by session ID
        limit: Maximum number of events to return
        
    Returns:
        List of metric events
    """
    try:
        collector = get_metrics_collector()
        
        # Validate metric type if provided
        metric_type_enum = None
        if metric_type:
            try:
                metric_type_enum = MetricType(metric_type)
            except ValueError:
                valid_types = [mt.value for mt in MetricType]
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid metric_type. Valid types: {valid_types}"
                )
        
        events = collector.get_events(
            metric_type=metric_type_enum,
            session_id=session_id,
            limit=limit
        )
        
        logger.info("[METRICS API] Events requested (type=%s, session=%s, limit=%d)",
                   metric_type, session_id, limit)
        
        return [MetricEventResponse(**event) for event in events]
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("[METRICS API] Error getting events: %s", str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve metric events")


@router.get("/session/{session_id}", response_model=SessionMetricsResponse)
async def get_session_metrics(session_id: str) -> SessionMetricsResponse:
    """
    Get all metrics for a specific session.
    
    Args:
        session_id: Session ID to query
        
    Returns:
        Session-specific metrics
    """
    try:
        collector = get_metrics_collector()
        session_data = collector.get_session_metrics(session_id)
        
        logger.info("[METRICS API] Session metrics requested (session=%s)", session_id)
        
        # Convert events to response models
        events = [MetricEventResponse(**event) for event in session_data["events"]]
        
        return SessionMetricsResponse(
            session_id=session_data["session_id"],
            total_events=session_data["total_events"],
            events_by_type=session_data["events_by_type"],
            events=events
        )
    
    except Exception as e:
        logger.error("[METRICS API] Error getting session metrics: %s", str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve session metrics")


@router.get("/guard-failures", response_model=Dict[str, int])
async def get_guard_failures(
    time_window_hours: Optional[int] = Query(None, ge=1, le=168)
) -> Dict[str, int]:
    """
    Get guard failure counts by type.
    
    Args:
        time_window_hours: Optional time window to filter metrics
        
    Returns:
        Dictionary of guard types and their failure counts
    """
    try:
        collector = get_metrics_collector()
        summary = collector.get_summary(time_window_hours=time_window_hours)
        
        logger.info("[METRICS API] Guard failures requested (window=%s hours)", time_window_hours)
        
        return summary.guard_failures_by_type
    
    except Exception as e:
        logger.error("[METRICS API] Error getting guard failures: %s", str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve guard failures")


@router.get("/escalations", response_model=Dict[str, int])
async def get_escalations(
    time_window_hours: Optional[int] = Query(None, ge=1, le=168)
) -> Dict[str, int]:
    """
    Get escalation counts by reason.
    
    Args:
        time_window_hours: Optional time window to filter metrics
        
    Returns:
        Dictionary of escalation reasons and their counts
    """
    try:
        collector = get_metrics_collector()
        summary = collector.get_summary(time_window_hours=time_window_hours)
        
        logger.info("[METRICS API] Escalations requested (window=%s hours)", time_window_hours)
        
        return summary.escalations_by_reason
    
    except Exception as e:
        logger.error("[METRICS API] Error getting escalations: %s", str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve escalations")


@router.get("/intent-overrides", response_model=Dict[str, int])
async def get_intent_overrides(
    time_window_hours: Optional[int] = Query(None, ge=1, le=168)
) -> Dict[str, int]:
    """
    Get intent override patterns and counts.
    
    Args:
        time_window_hours: Optional time window to filter metrics
        
    Returns:
        Dictionary of intent override patterns (from→to) and their counts
    """
    try:
        collector = get_metrics_collector()
        summary = collector.get_summary(time_window_hours=time_window_hours)
        
        logger.info("[METRICS API] Intent overrides requested (window=%s hours)", time_window_hours)
        
        return summary.intent_override_patterns
    
    except Exception as e:
        logger.error("[METRICS API] Error getting intent overrides: %s", str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve intent overrides")


@router.post("/cleanup")
async def cleanup_old_metrics() -> Dict[str, Any]:
    """
    Manually trigger cleanup of old metric events.
    
    Returns:
        Number of events removed
    """
    try:
        collector = get_metrics_collector()
        removed_count = collector.cleanup_old_events()
        
        logger.info("[METRICS API] Manual cleanup triggered (removed=%d)", removed_count)
        
        return {
            "status": "success",
            "events_removed": removed_count
        }
    
    except Exception as e:
        logger.error("[METRICS API] Error during cleanup: %s", str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to cleanup metrics")


@router.get("/health")
async def metrics_health() -> Dict[str, Any]:
    """
    Health check for metrics system.
    
    Returns:
        Status and basic statistics
    """
    try:
        collector = get_metrics_collector()
        summary = collector.get_summary()
        
        return {
            "status": "healthy",
            "total_events": summary.total_events,
            "events_last_hour": summary.events_last_hour,
            "events_last_24h": summary.events_last_24h
        }
    
    except Exception as e:
        logger.error("[METRICS API] Health check failed: %s", str(e), exc_info=True)
        return {
            "status": "unhealthy",
            "error": str(e)
        }

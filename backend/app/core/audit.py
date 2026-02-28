"""
Audit Traceability System
=========================

Provides immutable structured event logging for healthcare compliance.
Tracks critical operations including intent classifications, tool executions,
guard failures, and escalations.

This module ensures HIPAA compliance by maintaining an audit trail of all
system decisions and actions that affect patient data.

Author: Advanced AI Systems Team
Last Modified: 2026-02-26
"""

import json
import datetime
from typing import Dict, Any, Optional, List
from enum import Enum
from zoneinfo import ZoneInfo
from app.core.logger_config import get_application_logger

logger = get_application_logger()


class AuditEventType(Enum):
    """Types of auditable events in the system."""
    
    # Intent and Classification Events
    INTENT_CLASSIFIED = "intent_classified"
    INTENT_LOCKED = "intent_locked"
    INTENT_OVERRIDE_DETECTED = "intent_override_detected"
    
    # Tool Execution Events
    TOOL_CALL_REQUESTED = "tool_call_requested"
    TOOL_CALL_EXECUTED = "tool_call_executed"
    TOOL_CALL_FAILED = "tool_call_failed"
    
    # Guard and Validation Events
    GUARD_TRIGGERED = "guard_triggered"
    GUARD_PASSED = "guard_passed"
    GUARD_FAILED = "guard_failed"
    VALIDATION_FAILED = "validation_failed"
    
    # Transaction Events
    APPOINTMENT_CREATED = "appointment_created"
    APPOINTMENT_UPDATED = "appointment_updated"
    APPOINTMENT_CANCELLED = "appointment_cancelled"
    
    # Escalation Events
    ESCALATION_TRIGGERED = "escalation_triggered"
    NAME_COLLECTION_ESCALATED = "name_collection_escalated"
    
    # State Transition Events
    FLOW_STEP_CHANGED = "flow_step_changed"
    FLOW_COMPLETED = "flow_completed"
    
    # Error Events
    ERROR_OCCURRED = "error_occurred"
    EXCEPTION_CAUGHT = "exception_caught"


class AuditEvent:
    """
    Represents a single immutable audit event.
    
    All audit events are structured with consistent fields for compliance tracking.
    """
    
    def __init__(
        self,
        event_type: AuditEventType,
        user_id: int,
        session_id: str,
        details: Dict[str, Any],
        caller_mobile_number: Optional[str] = None,
        timestamp: Optional[datetime.datetime] = None
    ):
        """
        Create an immutable audit event.
        
        Args:
            event_type: Type of event being audited
            user_id: User ID associated with the event
            session_id: Session/thread ID for correlation
            details: Event-specific details (must be JSON-serializable)
            caller_mobile_number: Masked mobile number for correlation (optional)
            timestamp: Event timestamp (defaults to current time in Asia/Kolkata)
        """
        self.event_type = event_type
        self.user_id = user_id
        self.session_id = session_id
        self.details = details
        self.caller_mobile_number = caller_mobile_number
        self.timestamp = timestamp or datetime.datetime.now(ZoneInfo("Asia/Kolkata"))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for logging."""
        return {
            "event_type": self.event_type.value,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "caller_mobile_number": self.caller_mobile_number,
            "timestamp": self.timestamp.isoformat(),
            "details": self.details
        }
    
    def to_json(self) -> str:
        """Convert event to JSON string."""
        return json.dumps(self.to_dict(), default=str)


class AuditLogger:
    """
    Centralized audit logging service.
    
    Provides methods for logging different types of audit events with
    consistent structure and formatting.
    """
    
    def __init__(self):
        """Initialize audit logger."""
        self.logger = get_application_logger()
    
    def log_event(self, event: AuditEvent) -> None:
        """
        Log an audit event.
        
        Args:
            event: AuditEvent to log
        """
        # Log as structured JSON for easy parsing and compliance reporting
        self.logger.info(
            f"[AUDIT] {event.event_type.value}",
            extra={
                "audit_event": event.to_dict(),
                "event_type": event.event_type.value,
                "user_id": event.user_id,
                "session_id": event.session_id
            }
        )
    
    def log_intent_classification(
        self,
        user_id: int,
        session_id: str,
        intent: str,
        confidence: float,
        raw_message: str,
        caller_mobile_number: Optional[str] = None
    ) -> None:
        """
        Log intent classification event.
        
        Args:
            user_id: User ID
            session_id: Session ID
            intent: Classified intent
            confidence: Classification confidence score
            raw_message: User's message (sanitized)
            caller_mobile_number: Masked mobile number
        """
        event = AuditEvent(
            event_type=AuditEventType.INTENT_CLASSIFIED,
            user_id=user_id,
            session_id=session_id,
            caller_mobile_number=caller_mobile_number,
            details={
                "intent": intent,
                "confidence": confidence,
                "message_length": len(raw_message)
            }
        )
        self.log_event(event)
    
    def log_intent_lock(
        self,
        user_id: int,
        session_id: str,
        active_intent: str,
        flow_step: Optional[str] = None,
        caller_mobile_number: Optional[str] = None
    ) -> None:
        """
        Log intent locking event.
        
        Args:
            user_id: User ID
            session_id: Session ID
            active_intent: Intent being locked
            flow_step: Initial flow step
            caller_mobile_number: Masked mobile number
        """
        event = AuditEvent(
            event_type=AuditEventType.INTENT_LOCKED,
            user_id=user_id,
            session_id=session_id,
            caller_mobile_number=caller_mobile_number,
            details={
                "active_intent": active_intent,
                "flow_step": flow_step
            }
        )
        self.log_event(event)
    
    def log_tool_execution(
        self,
        user_id: int,
        session_id: str,
        tool_name: str,
        tool_args: Dict[str, Any],
        success: bool,
        result: Optional[str] = None,
        error: Optional[str] = None,
        caller_mobile_number: Optional[str] = None
    ) -> None:
        """
        Log tool execution event.
        
        Args:
            user_id: User ID
            session_id: Session ID
            tool_name: Name of tool executed
            tool_args: Tool arguments (sanitized)
            success: Whether execution succeeded
            result: Tool result (if successful)
            error: Error message (if failed)
            caller_mobile_number: Masked mobile number
        """
        event_type = (
            AuditEventType.TOOL_CALL_EXECUTED if success
            else AuditEventType.TOOL_CALL_FAILED
        )
        
        event = AuditEvent(
            event_type=event_type,
            user_id=user_id,
            session_id=session_id,
            caller_mobile_number=caller_mobile_number,
            details={
                "tool_name": tool_name,
                "tool_args": tool_args,
                "success": success,
                "result_preview": result[:200] if result else None,
                "error": error
            }
        )
        self.log_event(event)
    
    def log_guard_failure(
        self,
        user_id: int,
        session_id: str,
        guard_name: str,
        reason: str,
        state_snapshot: Optional[Dict[str, Any]] = None,
        caller_mobile_number: Optional[str] = None
    ) -> None:
        """
        Log guard failure event.
        
        Args:
            user_id: User ID
            session_id: Session ID
            guard_name: Name of guard that failed
            reason: Reason for failure
            state_snapshot: Relevant state fields
            caller_mobile_number: Masked mobile number
        """
        event = AuditEvent(
            event_type=AuditEventType.GUARD_FAILED,
            user_id=user_id,
            session_id=session_id,
            caller_mobile_number=caller_mobile_number,
            details={
                "guard_name": guard_name,
                "reason": reason,
                "state_snapshot": state_snapshot or {}
            }
        )
        self.log_event(event)
    
    def log_escalation(
        self,
        user_id: int,
        session_id: str,
        escalation_type: str,
        reason: str,
        level: Optional[int] = None,
        caller_mobile_number: Optional[str] = None
    ) -> None:
        """
        Log escalation event.
        
        Args:
            user_id: User ID
            session_id: Session ID
            escalation_type: Type of escalation
            reason: Reason for escalation
            level: Escalation level (if applicable)
            caller_mobile_number: Masked mobile number
        """
        event = AuditEvent(
            event_type=AuditEventType.ESCALATION_TRIGGERED,
            user_id=user_id,
            session_id=session_id,
            caller_mobile_number=caller_mobile_number,
            details={
                "escalation_type": escalation_type,
                "reason": reason,
                "level": level
            }
        )
        self.log_event(event)
    
    def log_appointment_transaction(
        self,
        user_id: int,
        session_id: str,
        transaction_type: str,  # "created", "updated", "cancelled"
        appointment_id: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
        caller_mobile_number: Optional[str] = None
    ) -> None:
        """
        Log appointment transaction event.
        
        Args:
            user_id: User ID
            session_id: Session ID
            transaction_type: Type of transaction
            appointment_id: Appointment ID (if applicable)
            details: Transaction details
            caller_mobile_number: Masked mobile number
        """
        event_type_map = {
            "created": AuditEventType.APPOINTMENT_CREATED,
            "updated": AuditEventType.APPOINTMENT_UPDATED,
            "cancelled": AuditEventType.APPOINTMENT_CANCELLED
        }
        
        event = AuditEvent(
            event_type=event_type_map.get(transaction_type, AuditEventType.APPOINTMENT_UPDATED),
            user_id=user_id,
            session_id=session_id,
            caller_mobile_number=caller_mobile_number,
            details={
                "appointment_id": appointment_id,
                "transaction_type": transaction_type,
                **(details or {})
            }
        )
        self.log_event(event)
    
    def log_flow_transition(
        self,
        user_id: int,
        session_id: str,
        from_step: Optional[str],
        to_step: str,
        active_intent: str,
        caller_mobile_number: Optional[str] = None
    ) -> None:
        """
        Log flow step transition event.
        
        Args:
            user_id: User ID
            session_id: Session ID
            from_step: Previous flow step
            to_step: New flow step
            active_intent: Active intent
            caller_mobile_number: Masked mobile number
        """
        event = AuditEvent(
            event_type=AuditEventType.FLOW_STEP_CHANGED,
            user_id=user_id,
            session_id=session_id,
            caller_mobile_number=caller_mobile_number,
            details={
                "from_step": from_step,
                "to_step": to_step,
                "active_intent": active_intent
            }
        )
        self.log_event(event)


# Global audit logger instance
_audit_logger = None


def get_audit_logger() -> AuditLogger:
    """
    Get the global audit logger instance.
    
    Returns:
        AuditLogger instance
    """
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger()
    return _audit_logger

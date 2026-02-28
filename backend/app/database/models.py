"""
SQLAlchemy Models
================

This module defines the database models for the application.

Models:
- User: Represents a user of the system.
- Appointment: Represents an appointment scheduled by a user.
"""

from datetime import datetime
from typing import Optional, List
from sqlalchemy import String, Integer, DateTime, Date, Time, ForeignKey, Text, JSON
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.sql import func

class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""
    pass

class User(Base):
    """
    User Model
    
    Represents a registered user in the system.
    """
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), unique=True, index=True, nullable=True)
    full_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # Nullable for progressive enrichment
    mobile_number: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    appointments: Mapped[List["Appointment"]] = relationship(back_populates="user", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<User(id={self.id}, full_name='{self.full_name}', mobile_number='{self.mobile_number}')>"

class Appointment(Base):
    """
    Appointment Model
    
    Represents an appointment scheduled by a user.
    """
    __tablename__ = "appointments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    
    appointment_type: Mapped[str] = mapped_column(String(50), nullable=False)
    appointment_date: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    appointment_time: Mapped[datetime.time] = mapped_column(Time, nullable=False)
    token_number: Mapped[int] = mapped_column(Integer, nullable=False)
    
    status: Mapped[str] = mapped_column(String(20), default="scheduled", nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    cancellation_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user: Mapped["User"] = relationship(back_populates="appointments")

    def __repr__(self) -> str:
        return f"<Appointment(id={self.id}, date='{self.appointment_date}', time='{self.appointment_time}', status='{self.status}')>"

class CallState(Base):
    """
    Call State Model
    
    Represents the persistent state of a voice call, used for recovery and context.
    """
    __tablename__ = "call_states"

    call_sid: Mapped[str] = mapped_column(String(50), primary_key=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    
    # JSON state storage: history, current_step, variables, etc.
    state: Mapped[dict] = mapped_column(JSON, default=dict)
    
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    user: Mapped["User"] = relationship()

    def __repr__(self) -> str:
        return f"<CallState(call_sid='{self.call_sid}', status='{self.status}', updated_at='{self.updated_at}')>"

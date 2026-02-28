
import sys
import os
import pytest
from datetime import date, time, datetime, timedelta
from unittest.mock import MagicMock, call, patch
from fastapi.testclient import TestClient

# Add the backend directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from app.services.appointments import AppointmentService
from app.database.models import Appointment
from main import app
from app.database.session import get_db

# --- Unit Tests for Service ---

def test_get_upcoming_appointments_basic():
    """Test fetching appointments when data exists."""
    mock_db = MagicMock()
    
    # Setup some mock appointments
    future_date = date.today() + timedelta(days=5)
    
    appt1 = Appointment(
        id=1, user_id=1, status="scheduled",
        appointment_date=future_date, appointment_time=time(10, 0)
    )
    appt2 = Appointment(
        id=2, user_id=1, status="scheduled",
        appointment_date=future_date, appointment_time=time(11, 0)
    )

    mock_query = mock_db.query.return_value
    mock_filter = mock_query.filter.return_value
    mock_order = mock_filter.order_by.return_value
    mock_order.all.return_value = [appt1, appt2]
    
    results = AppointmentService.get_upcoming_appointments(mock_db, 1)
    
    assert len(results) == 2
    assert results[0].id == 1
    assert results[1].id == 2

def test_get_upcoming_appointments_none():
    """Test fetching when no appointments exist."""
    mock_db = MagicMock()
    
    mock_query = mock_db.query.return_value
    mock_filter = mock_query.filter.return_value
    mock_order = mock_filter.order_by.return_value
    mock_order.all.return_value = []
    
    results = AppointmentService.get_upcoming_appointments(mock_db, 1)
    
    assert len(results) == 0

# --- Integration Tests for API ---

client = TestClient(app)

def test_api_get_upcoming_appointments():
    """Test API endpoint for fetching upcoming appointments."""
    
    mock_db = MagicMock()
    future_date = date.today() + timedelta(days=2)
    
    # Mock data
    mock_appt = Appointment(
        id=10, 
        user_id=100,
        appointment_type="Consultation",
        appointment_date=future_date,
        appointment_time=time(9, 30),
        token_number=5,
        status="scheduled",
        notes="Test notes",
        created_at=datetime.now()
    )
    
    mock_query = mock_db.query.return_value
    mock_filter = mock_query.filter.return_value
    mock_order = mock_filter.order_by.return_value
    mock_order.all.return_value = [mock_appt]
    
    app.dependency_overrides[get_db] = lambda: mock_db
    
    response = client.get("/api/appointments/user/100/upcoming")
    
    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == 100
    assert data["count"] == 1
    assert len(data["appointments"]) == 1
    assert data["appointments"][0]["id"] == 10
    
    app.dependency_overrides = {}

# --- Unit Tests for Cancellation ---

def test_cancel_appointment_success():
    """Test cancelling an existing appointment."""
    mock_db = MagicMock()
    mock_appt = Appointment(id=1, status="scheduled")
    
    mock_query = mock_db.query.return_value
    mock_filter = mock_query.filter.return_value
    mock_filter.first.return_value = mock_appt
    
    updated_appt = AppointmentService.cancel_appointment(mock_db, 1)
    
    assert updated_appt is not None
    assert updated_appt.status == "cancelled"
    mock_db.commit.assert_called_once()
    mock_db.refresh.assert_called_once()

def test_cancel_appointment_not_found():
    """Test cancelling a non-existent appointment."""
    mock_db = MagicMock()
    
    mock_query = mock_db.query.return_value
    mock_filter = mock_query.filter.return_value
    mock_filter.first.return_value = None
    
    updated_appt = AppointmentService.cancel_appointment(mock_db, 999)
    
    assert updated_appt is None
    mock_db.commit.assert_not_called()

# --- Integration Tests for Cancellation API ---

def test_api_cancel_appointment_success():
    """Test API endpoint for cancellation."""
    mock_db = MagicMock()
    mock_appt = Appointment(
        id=1, 
        user_id=1, 
        appointment_type="Checkup",
        appointment_date=date.today(),
        appointment_time=time(10, 0),
        token_number=1,
        status="scheduled",
        created_at=datetime.now()
    )
    
    mock_query = mock_db.query.return_value
    mock_filter = mock_query.filter.return_value
    mock_filter.first.return_value = mock_appt
    
    app.dependency_overrides[get_db] = lambda: mock_db
    
    response = client.post("/api/appointments/1/cancel")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "cancelled"
    assert data["id"] == 1
    
    app.dependency_overrides = {}

def test_api_cancel_appointment_not_found():
    """Test API endpoint for cancelling non-existent appointment."""
    mock_db = MagicMock()
    
    mock_query = mock_db.query.return_value
    mock_filter = mock_query.filter.return_value
    mock_filter.first.return_value = None
    
    app.dependency_overrides[get_db] = lambda: mock_db
    
    response = client.post("/api/appointments/999/cancel")
    
    assert response.status_code == 404
    
    app.dependency_overrides = {}

# --- Unit Tests for Rescheduling ---

def test_reschedule_appointment_success():
    """Test rescheduling an existing appointment."""
    mock_db = MagicMock()
    mock_appt = Appointment(id=1, status="scheduled", appointment_date=date.today(), appointment_time=time(10, 0))
    
    mock_query = mock_db.query.return_value
    mock_filter = mock_query.filter.return_value
    mock_filter.first.return_value = mock_appt
    
    new_date = date.today() + timedelta(days=1)
    new_time = time(15, 30)
    
    updated_appt = AppointmentService.reschedule_appointment(mock_db, 1, new_date, new_time)
    
    assert updated_appt is not None
    assert updated_appt.appointment_date == new_date
    assert updated_appt.appointment_time == new_time
    # Should ensure status is scheduled
    assert updated_appt.status == "scheduled"
    
    mock_db.commit.assert_called_once()
    mock_db.refresh.assert_called_once()

def test_reschedule_appointment_not_found():
    """Test rescheduling a non-existent appointment."""
    mock_db = MagicMock()
    
    mock_query = mock_db.query.return_value
    mock_filter = mock_query.filter.return_value
    mock_filter.first.return_value = None
    
    updated_appt = AppointmentService.reschedule_appointment(mock_db, 999, date.today(), time(10, 0))
    
    assert updated_appt is None
    mock_db.commit.assert_not_called()

# --- Integration Tests for Rescheduling API ---

def test_api_reschedule_appointment_success():
    """Test API endpoint for rescheduling."""
    mock_db = MagicMock()
    mock_appt = Appointment(
        id=1, 
        user_id=1, 
        appointment_type="Checkup",
        appointment_date=date.today(),
        appointment_time=time(10, 0),
        token_number=1,
        status="scheduled",
        created_at=datetime.now()
    )
    
    mock_query = mock_db.query.return_value
    mock_filter = mock_query.filter.return_value
    mock_filter.first.return_value = mock_appt
    
    app.dependency_overrides[get_db] = lambda: mock_db
    
    payload = {
        "new_date": str(date.today() + timedelta(days=1)),
        "new_time": "14:00:00"
    }
    
    response = client.post("/api/appointments/1/reschedule", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    assert data["appointment_time"] == "14:00:00"
    
    app.dependency_overrides = {}

# --- Unit Tests for Creation ---

def test_create_appointment_success():
    """Test creating a new appointment."""
    mock_db = MagicMock()
    
    new_appt = AppointmentService.create_appointment(
        mock_db, 
        user_id=1, 
        appointment_type="Consultation", 
        date=date.today(), 
        time=time(10, 0), 
        notes="New appt"
    )
    
    assert new_appt.user_id == 1
    assert new_appt.status == "scheduled"
    assert new_appt.notes == "New appt"
    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()

# --- Integration Tests for Creation API ---

@patch("app.apis.appointments.AppointmentService.create_appointment")
def test_api_create_appointment_success(mock_create):
    """Test API endpoint for creating appointment."""
    # Setup mock return value
    mock_appt = MagicMock()
    mock_appt.id = 100
    mock_appt.user_id = 1
    mock_appt.appointment_type = "Consultation"
    mock_appt.appointment_date = date.today()
    mock_appt.appointment_time = time(12, 0)
    mock_appt.token_number = 1234
    mock_appt.status = "scheduled"
    mock_appt.notes = "API test"
    mock_appt.created_at = datetime.now()
    
    mock_create.return_value = mock_appt
    
    payload = {
        "user_id": 1,
        "appointment_type": "Consultation",
        "date": str(date.today()),
        "time": "12:00:00",
        "notes": "API test"
    }
    
    response = client.post("/api/appointments/", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "scheduled"
    assert data["user_id"] == 1
    assert data["id"] == 100

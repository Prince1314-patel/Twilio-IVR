
import sys
import os
import pytest
from datetime import date, time
from unittest.mock import MagicMock
from fastapi.testclient import TestClient

# Add the backend directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from app.services.availability import AvailabilityService
from app.database.models import Appointment
from main import app
from app.database.session import get_db

# --- Unit Tests for Service ---

def test_generate_slots():
    """Test that slots are generated within business hours."""
    slots = AvailabilityService.generate_slots()
    assert len(slots) > 0
    # Basic sanity check assuming 9-17 hours
    assert any(t.hour == 9 for t in slots)
    assert any(t.hour == 16 for t in slots)

def test_get_available_slots():
    """Test filtering of booked slots."""
    mock_db = MagicMock()
    # Mock one booked appointment at 10:00
    mock_appt = Appointment(appointment_time=time(10, 0))
    
    # Setup mock return
    mock_query = mock_db.query.return_value
    mock_filter = mock_query.filter.return_value
    mock_filter.all.return_value = [mock_appt]
    
    slots = AvailabilityService.get_available_slots(mock_db, date(2025, 12, 25))
    
    # 10:00 should NOT be in the available slots
    assert time(10, 0) not in slots
    # 09:00 should be (assuming it's a start time)
    assert time(9, 0) in slots

def test_get_nearest_slot_exact_match():
    """Test getting nearest slot when search time is available."""
    mock_db = MagicMock()
    # No bookings
    mock_query = mock_db.query.return_value
    mock_filter = mock_query.filter.return_value
    mock_filter.all.return_value = []
    
    nearest = AvailabilityService.get_nearest_slot(mock_db, date(2025, 12, 25), time(10, 0))
    # Should return the same time if available
    assert nearest == time(10, 0)

def test_get_nearest_slot_booked():
    """Test getting nearest slot when target is booked."""
    mock_db = MagicMock()
    # Book 10:00
    mock_appt = Appointment(appointment_time=time(10, 0))
    
    mock_query = mock_db.query.return_value
    mock_filter = mock_query.filter.return_value
    mock_filter.all.return_value = [mock_appt]
    
    # Asking for 10:00, but it's taken. Next closest should be 10:30 (assuming 30m slots) or 9:30
    nearest = AvailabilityService.get_nearest_slot(mock_db, date(2025, 12, 25), time(10, 0))
    
    assert nearest != time(10, 0)
    # Depending on logic, it could be 09:30 or 10:30
    assert nearest in [time(9, 30), time(10, 30)]

# --- Integration Tests for API ---

client = TestClient(app)

def test_api_check_with_nearest():
    """Test API suggestions nearest slot when booked."""
    mock_db = MagicMock()
    # Book 10:00
    mock_appt_obj = Appointment(appointment_time=time(10, 0))
    mock_query = mock_db.query.return_value
    mock_filter = mock_query.filter.return_value
    # For is_slot_available check
    mock_filter.first.return_value = mock_appt_obj
    # For get_available_slots check (called by get_nearest_slot)
    mock_filter.all.return_value = [mock_appt_obj]

    app.dependency_overrides[get_db] = lambda: mock_db
    
    payload = {
        "date": "2025-12-25",
        "time": "10:00:00"
    }
    
    response = client.post("/api/availability/check", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    assert data["available"] is False
    assert data["nearest_slot"] is not None
    
    app.dependency_overrides = {}

def test_api_get_slots():
    """Test /slots endpoint."""
    mock_db = MagicMock()
    mock_query = mock_db.query.return_value
    mock_filter = mock_query.filter.return_value
    mock_filter.all.return_value = [] # No bookings
    
    app.dependency_overrides[get_db] = lambda: mock_db
    
    response = client.get("/api/availability/slots?date=2025-12-25")
    
    assert response.status_code == 200
    data = response.json()
    assert len(data["slots"]) > 0
    assert "09:00:00" in data["slots"] # formatted as string in JSON
    
    app.dependency_overrides = {}

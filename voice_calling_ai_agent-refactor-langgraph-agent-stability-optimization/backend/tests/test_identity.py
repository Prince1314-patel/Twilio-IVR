
import pytest
from datetime import date, time
from unittest.mock import MagicMock
from app.core.identity import IdentityService
from app.database.models import User, Appointment

# ... existing tests ...
def test_extract_phone_number_from_twilio_form():
    """Test extracting phone number from Twilio form data (From field)."""
    form_data = {"From": "+1234567890", "To": "+0987654321"}
    phone_number = IdentityService.extract_phone_number(form_data)
    assert phone_number == "+1234567890"

def test_extract_phone_number_fallback():
    """Test extracting phone number from Caller field if From is missing."""
    form_data = {"Caller": "+1122334455"}
    phone_number = IdentityService.extract_phone_number(form_data)
    assert phone_number == "+1122334455"

def test_extract_phone_number_none():
    """Test extracting phone number when no number is present."""
    form_data = {"Other": "Value"}
    phone_number = IdentityService.extract_phone_number(form_data)
    assert phone_number is None

def test_resolve_user_found():
    """Test resolving an existing user."""
    mock_db = MagicMock()
    mock_user = User(id=1, full_name="Test User", mobile_number="+1234567890")
    
    # Mock the query chain: db.query(User).filter(...).first()
    mock_query = mock_db.query.return_value
    mock_filter = mock_query.filter.return_value
    mock_filter.first.return_value = mock_user
    
    user = IdentityService.resolve_user(mock_db, "+1234567890")
    assert user is not None
    assert user.id == 1
    assert user.full_name == "Test User"
    
def test_resolve_user_not_found():
    """Test resolving a non-existent user."""
    mock_db = MagicMock()
    
    mock_query = mock_db.query.return_value
    mock_filter = mock_query.filter.return_value
    mock_filter.first.return_value = None
    
    user = IdentityService.resolve_user(mock_db, "+0000000000")
    assert user is None

def test_resolve_user_db_error():
    """Test handling database errors gracefully."""
    mock_db = MagicMock()
    mock_db.query.side_effect = Exception("DB Connection Failed")
    
    user = IdentityService.resolve_user(mock_db, "+1234567890")
    assert user is None

def test_get_or_create_user_existing():
    """Test retrieving an existing user via get_or_create."""
    mock_db = MagicMock()
    mock_user = User(id=1, full_name="Existing User", mobile_number="+1234567890")
    
    # Setup mock to return user on first query
    mock_query = mock_db.query.return_value
    mock_filter = mock_query.filter.return_value
    mock_filter.first.return_value = mock_user
    
    user = IdentityService.get_or_create_user(mock_db, "+1234567890")
    
    assert user == mock_user
    # Ensure add was NOT called
    mock_db.add.assert_not_called()

def test_get_or_create_user_new():
    """Test creating a new user when not found."""
    mock_db = MagicMock()
    
    # Setup mock to return None on query
    mock_query = mock_db.query.return_value
    mock_filter = mock_query.filter.return_value
    mock_filter.first.return_value = None
    
    user = IdentityService.get_or_create_user(mock_db, "+9988776655")
    
    assert user is not None
    assert user.mobile_number == "+9988776655"
    assert user.full_name == "Guest"
    
    # Ensure add and commit WERE called
    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()
    mock_db.refresh.assert_called_once()

def test_get_or_create_user_db_error():
    """Test graceful handling of DB error during creation."""
    mock_db = MagicMock()
    
    # Return none first, then error on add
    mock_query = mock_db.query.return_value
    mock_filter = mock_query.filter.return_value
    mock_filter.first.return_value = None
    
    mock_db.add.side_effect = Exception("Insert Failed")
    
    user = IdentityService.get_or_create_user(mock_db, "+1234567890")
    assert user is None
    mock_db.rollback.assert_called_once()

def test_get_last_appointment_found():
    """Test retrieving the last appointment."""
    mock_db = MagicMock()
    mock_appt = Appointment(
        id=101, 
        user_id=1, 
        appointment_date=date(2025, 1, 1),
        appointment_time=time(10, 0),
        status="scheduled"
    )
    
    mock_query = mock_db.query.return_value
    mock_filter = mock_query.filter.return_value
    mock_order = mock_filter.order_by.return_value
    mock_order.first.return_value = mock_appt
    
    appt = IdentityService.get_last_appointment(mock_db, 1)
    
    assert appt is not None
    assert appt.id == 101
    assert appt.status == "scheduled"

def test_get_last_appointment_none():
    """Test when user has no appointments."""
    mock_db = MagicMock()
    
    mock_query = mock_db.query.return_value
    mock_filter = mock_query.filter.return_value
    mock_order = mock_filter.order_by.return_value
    mock_order.first.return_value = None
    
    appt = IdentityService.get_last_appointment(mock_db, 1)
    assert appt is None

def test_get_last_appointment_error():
    """Test handling DB error during appointment fetch."""
    mock_db = MagicMock()
    mock_db.query.side_effect = Exception("DB Error")
    
    appt = IdentityService.get_last_appointment(mock_db, 1)
    assert appt is None

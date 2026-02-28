
import sys
import os
import pytest
from unittest.mock import MagicMock
from sqlalchemy.orm import Session

# Add the backend directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from app.core.identity import IdentityService
from app.database.models import User

def test_update_user_name_success():
    """Test updating user name successfully."""
    mock_db = MagicMock()
    mock_user = User(id=1, full_name=None, mobile_number="+1234567890")
    
    mock_query = mock_db.query.return_value
    mock_filter = mock_query.filter.return_value
    mock_filter.first.return_value = mock_user
    
    updated_user = IdentityService.update_user_name(mock_db, 1, "John Doe")
    
    assert updated_user is not None
    assert updated_user.full_name == "John Doe"
    mock_db.commit.assert_called_once()
    mock_db.refresh.assert_called_once()

def test_update_user_name_not_found():
    """Test updating name for non-existent user."""
    mock_db = MagicMock()
    
    mock_query = mock_db.query.return_value
    mock_filter = mock_query.filter.return_value
    mock_filter.first.return_value = None
    
    updated_user = IdentityService.update_user_name(mock_db, 999, "Jane key")
    
    assert updated_user is None
    mock_db.commit.assert_not_called()

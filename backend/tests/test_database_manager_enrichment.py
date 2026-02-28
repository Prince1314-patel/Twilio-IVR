"""
Simplified Unit Tests for DatabaseManager User Enrichment Methods
==================================================================

Tests for progressive user enrichment functionality in DatabaseManager.
Uses actual database with cleanup to ensure tests work correctly.

Author: Advanced AI Systems Team
Last Modified: 2026-02-03
"""

import pytest
import sys
import os
from datetime import datetime, timedelta

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))

from app.database.manager import DatabaseManager


@pytest.fixture(scope="function")
def db_manager():
    """Create a DatabaseManager instance for testing."""
    return DatabaseManager()


@pytest.fixture(scope="function")
def test_phone_numbers():
    """Generate unique test phone numbers for each test."""
    import random
    base = "+999" + str(random.randint(10000000, 99999999))
    return {
        "primary": base,
        "secondary": base[:-1] + str(int(base[-1]) + 1),
        "tertiary": base[:-1] + str(int(base[-1]) + 2),
    }


class TestGetUserByMobileNumber:
    """Test suite for get_user_by_mobile_number method."""
    
    def test_get_existing_user(self, db_manager, test_phone_numbers):
        """Test retrieving an existing user by mobile number."""
        phone = test_phone_numbers["primary"]
        
        # Create a user first
        create_result = db_manager.create_user_with_phone(phone, "Test User")
        assert create_result["success"], f"Failed to create user: {create_result.get('message')}"
        
        # Retrieve the user
        user_data = db_manager.get_user_by_mobile_number(phone)
        
        # Assertions
        assert user_data is not None
        assert user_data["mobile_number"] == phone
        assert user_data["name"] == "Test User"
        assert "user_id" in user_data
        assert "created_at" in user_data
    
    def test_get_user_with_null_name(self, db_manager, test_phone_numbers):
        """Test retrieving a user with NULL name (progressive enrichment)."""
        phone = test_phone_numbers["primary"]
        
        # Create user without name
        create_result = db_manager.create_user_with_phone(phone, name=None)
        assert create_result["success"], f"Failed to create user: {create_result.get('message')}"
        
        # Retrieve the user
        user_data = db_manager.get_user_by_mobile_number(phone)
        
        # Assertions
        assert user_data is not None
        assert user_data["name"] is None
        assert user_data["mobile_number"] == phone


class TestCreateUserWithPhone:
    """Test suite for create_user_with_phone method."""
    
    def test_create_user_with_name(self, db_manager, test_phone_numbers):
        """Test creating a user with phone number and name."""
        phone = test_phone_numbers["primary"]
        result = db_manager.create_user_with_phone(phone, "Alice Smith")
        
        # Assertions
        assert result["success"] is True
        assert "user_id" in result
        assert result["user_id"] > 0
        assert "User created successfully" in result["message"]
        
        # Verify user was actually created
        user_data = db_manager.get_user_by_mobile_number(phone)
        assert user_data is not None
        assert user_data["name"] == "Alice Smith"
    
    def test_create_user_without_name(self, db_manager, test_phone_numbers):
        """Test creating a user with phone number only (name=None)."""
        phone = test_phone_numbers["primary"]
        result = db_manager.create_user_with_phone(phone, name=None)
        
        # Assertions
        assert result["success"] is True
        assert "user_id" in result
        
        # Verify user was created with NULL name
        user_data = db_manager.get_user_by_mobile_number(phone)
        assert user_data is not None
        assert user_data["name"] is None
    
    def test_create_duplicate_user(self, db_manager, test_phone_numbers):
        """Test that creating a duplicate user fails gracefully."""
        phone = test_phone_numbers["primary"]
        
        # Create first user
        result1 = db_manager.create_user_with_phone(phone, "First User")
        assert result1["success"] is True
        
        # Try to create duplicate
        result2 = db_manager.create_user_with_phone(phone, "Second User")
        
        # Should fail
        assert result2["success"] is False
        assert "already exists" in result2["message"].lower()
        assert "user_id" in result2  # Should still return the existing user_id
    
    def test_create_multiple_users(self, db_manager, test_phone_numbers):
        """Test creating multiple users with different phone numbers."""
        phones = [test_phone_numbers["primary"], test_phone_numbers["secondary"], test_phone_numbers["tertiary"]]
        names = ["User One", "User Two", None]
        
        created_ids = []
        for phone, name in zip(phones, names):
            result = db_manager.create_user_with_phone(phone, name)
            assert result["success"] is True, f"Failed to create user: {result.get('message')}"
            created_ids.append(result["user_id"])
        
        # All IDs should be unique
        assert len(created_ids) == len(set(created_ids))


class TestUpdateUserName:
    """Test suite for update_user_name method."""
    
    def test_update_null_name(self, db_manager, test_phone_numbers):
        """Test updating a user's NULL name (progressive enrichment)."""
        phone = test_phone_numbers["primary"]
        
        # Create user without name
        create_result = db_manager.create_user_with_phone(phone, name=None)
        user_id = create_result["user_id"]
        
        # Update the name
        update_result = db_manager.update_user_name(user_id, "Bob Johnson")
        
        # Assertions
        assert update_result["success"] is True
        assert "updated successfully" in update_result["message"].lower()
        
        # Verify the update
        user_data = db_manager.get_user_by_mobile_number(phone)
        assert user_data["name"] == "Bob Johnson"
    
    def test_update_existing_name(self, db_manager, test_phone_numbers):
        """Test updating a user's existing name."""
        phone = test_phone_numbers["primary"]
        
        # Create user with name
        create_result = db_manager.create_user_with_phone(phone, "Old Name")
        user_id = create_result["user_id"]
        
        # Update the name
        update_result = db_manager.update_user_name(user_id, "New Name")
        
        # Assertions
        assert update_result["success"] is True
        
        # Verify the update
        user_data = db_manager.get_user_by_mobile_number(phone)
        assert user_data["name"] == "New Name"
    
    def test_update_nonexistent_user(self, db_manager):
        """Test updating a user that doesn't exist."""
        update_result = db_manager.update_user_name(999999999, "Test Name")
        
        # Should fail
        assert update_result["success"] is False
        assert "not found" in update_result["message"].lower()
    
    def test_update_name_with_special_characters(self, db_manager, test_phone_numbers):
        """Test updating name with special characters."""
        phone = test_phone_numbers["primary"]
        
        create_result = db_manager.create_user_with_phone(phone, name=None)
        user_id = create_result["user_id"]
        
        # Update with special characters
        special_name = "O'Brien-Smith Jr."
        update_result = db_manager.update_user_name(user_id, special_name)
        
        assert update_result["success"] is True
        
        # Verify
        user_data = db_manager.get_user_by_mobile_number(phone)
        assert user_data["name"] == special_name


class TestGetUserAppointmentHistory:
    """Test suite for get_user_appointment_history method."""
    
    def test_get_history_for_user_without_appointments(self, db_manager, test_phone_numbers):
        """Test retrieving appointment history for a user with no appointments."""
        phone = test_phone_numbers["primary"]
        
        # Create user
        create_result = db_manager.create_user_with_phone(phone, "New User")
        user_id = create_result["user_id"]
        
        # Get appointment history
        history = db_manager.get_user_appointment_history(user_id, limit=5)
        
        # Should return empty list
        assert isinstance(history, list)
        assert len(history) == 0
    
    def test_get_history_for_nonexistent_user(self, db_manager):
        """Test retrieving appointment history for a user that doesn't exist."""
        history = db_manager.get_user_appointment_history(999999999, limit=5)
        
        # Should return empty list
        assert isinstance(history, list)
        assert len(history) == 0


class TestIntegrationScenarios:
    """Integration tests for complete user enrichment flows."""
    
    def test_complete_progressive_enrichment_flow(self, db_manager, test_phone_numbers):
        """Test the complete progressive enrichment flow."""
        phone = test_phone_numbers["primary"]
        
        # Step 1: Create user without name
        create_result = db_manager.create_user_with_phone(phone, name=None)
        assert create_result["success"] is True
        user_id = create_result["user_id"]
        
        # Step 2: Verify user exists with NULL name
        user_data = db_manager.get_user_by_mobile_number(phone)
        assert user_data is not None
        assert user_data["name"] is None
        
        # Step 3: Update name (progressive enrichment)
        update_result = db_manager.update_user_name(user_id, "Progressive User")
        assert update_result["success"] is True
        
        # Step 4: Verify name was updated
        updated_user = db_manager.get_user_by_mobile_number(phone)
        assert updated_user["name"] == "Progressive User"
        
        # Step 5: Get appointment history (should be empty)
        history = db_manager.get_user_appointment_history(user_id)
        assert len(history) == 0
    
    def test_existing_user_flow(self, db_manager, test_phone_numbers):
        """Test flow for an existing user with complete profile."""
        phone = test_phone_numbers["primary"]
        
        # Create user with complete profile
        create_result = db_manager.create_user_with_phone(phone, "Existing User")
        assert create_result["success"] is True
        user_id = create_result["user_id"]
        
        # Retrieve user
        user_data = db_manager.get_user_by_mobile_number(phone)
        assert user_data["name"] == "Existing User"
        
        # Get appointment history
        history = db_manager.get_user_appointment_history(user_id)
        assert isinstance(history, list)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

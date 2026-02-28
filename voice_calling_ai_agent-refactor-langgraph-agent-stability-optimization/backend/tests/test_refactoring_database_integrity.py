#!/usr/bin/env python3
"""
Property-Based Tests for Database Layer Integrity
================================================

These tests verify that the database layer refactoring maintains integrity
and that all database operations work correctly after the reorganization.

Feature: backend-refactoring

Author: Advanced AI Systems Team
Last Modified: 2025-01-28
"""

import unittest
import tempfile
import os
import sys
from pathlib import Path
from hypothesis import given, strategies as st, settings, assume, HealthCheck
from typing import List, Dict, Any
import datetime
from zoneinfo import ZoneInfo

# Add backend to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.database.manager import DatabaseManager
from app.database.tools.appointment_tools import (
    validate_date, validate_time, validate_mobile_number, validate_name,
    validate_appointment_type, is_future_datetime, is_within_business_hours,
    is_slot_granular, mask_mobile_number
)


class TestRefactoringDatabaseIntegrity(unittest.TestCase):
    """Property-based tests for database layer integrity."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create a temporary database for testing
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        
        # Initialize database manager with test database
        self.db_manager = DatabaseManager(db_path=self.temp_db.name)
        
    def tearDown(self):
        """Clean up test fixtures."""
        # Clean up temporary database
        try:
            os.unlink(self.temp_db.name)
        except:
            pass
    
    @settings(max_examples=20, deadline=10000)
    @given(st.dates(min_value=datetime.date(2025, 1, 1), max_value=datetime.date(2030, 12, 31)))
    def test_database_manager_import_and_initialization_property(self, test_date: datetime.date):
        """
        Property 3: Database Layer Integrity
        
        For any valid date, the database manager should be importable from its new location
        and should initialize correctly with all expected methods available.
        
        **Feature: backend-refactoring, Property 3: Database Layer Integrity**
        **Validates: Requirements 3.3, 3.4, 3.5**
        """
        # Test that DatabaseManager can be imported from new location
        self.assertIsNotNone(self.db_manager, "DatabaseManager should be importable")
        
        # Test that all expected methods exist
        expected_methods = [
            'create_appointment', 'check_availability', 'get_available_slots',
            'update_appointment', 'cancel_appointment'
        ]
        
        for method_name in expected_methods:
            self.assertTrue(hasattr(self.db_manager, method_name),
                          f"DatabaseManager should have method {method_name}")
            self.assertTrue(callable(getattr(self.db_manager, method_name)),
                          f"DatabaseManager.{method_name} should be callable")
        
        # Test basic functionality with the test date
        date_str = test_date.strftime("%Y-%m-%d")
        
        try:
            # This should not raise an exception
            slots = self.db_manager.get_available_slots(date_str)
            self.assertIsInstance(slots, list, "get_available_slots should return a list")
            
        except Exception as e:
            self.fail(f"Database manager basic functionality failed: {e}")
    
    @settings(max_examples=15, deadline=10000)
    @given(st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Pc', 'Pd', 'Zs'))))
    def test_validation_functions_integrity_property(self, test_input: str):
        """
        Property: Validation functions integrity
        
        For any input string, validation functions should be importable from the new location
        and should return consistent boolean results without raising exceptions.
        
        **Feature: backend-refactoring, Property 3: Database Layer Integrity**
        **Validates: Requirements 3.3, 3.4, 3.5**
        """
        # Test that validation functions are importable and callable
        validation_functions = [
            validate_date, validate_time, validate_mobile_number,
            validate_name, validate_appointment_type
        ]
        
        for func in validation_functions:
            self.assertTrue(callable(func), f"Validation function {func.__name__} should be callable")
            
            try:
                # All validation functions should return a tuple (bool, str)
                result = func(test_input)
                self.assertIsInstance(result, tuple, 
                                    f"{func.__name__} should return a tuple")
                self.assertEqual(len(result), 2, 
                               f"{func.__name__} should return a 2-tuple")
                self.assertIsInstance(result[0], bool, 
                                    f"{func.__name__} should return (bool, str)")
                self.assertIsInstance(result[1], str, 
                                    f"{func.__name__} should return (bool, str)")
                
            except Exception as e:
                self.fail(f"Validation function {func.__name__} raised exception: {e}")
    
    @settings(max_examples=10, deadline=10000)
    @given(st.dates(min_value=datetime.date(2025, 1, 1), max_value=datetime.date(2030, 12, 31)),
           st.times(min_value=datetime.time(9, 0), max_value=datetime.time(16, 59)))  # Exclude 17:00
    def test_datetime_validation_consistency_property(self, test_date: datetime.date, test_time: datetime.time):
        """
        Property: DateTime validation consistency
        
        For any valid date and time combination, the validation functions should
        work consistently and maintain the same business logic after refactoring.
        
        **Feature: backend-refactoring, Property 3: Database Layer Integrity**
        **Validates: Requirements 3.3, 3.4, 3.5**
        """
        date_str = test_date.strftime("%Y-%m-%d")
        time_str = test_time.strftime("%H:%M:%S")
        
        # Test date validation
        is_valid_date, date_msg = validate_date(date_str)
        self.assertTrue(is_valid_date, f"Valid date {date_str} should pass validation")
        self.assertEqual(date_msg, "", "Valid date should have empty error message")
        
        # Test time validation
        is_valid_time, time_msg = validate_time(time_str)
        self.assertTrue(is_valid_time, f"Valid time {time_str} should pass validation")
        self.assertEqual(time_msg, "", "Valid time should have empty error message")
        
        # Test business hours validation (for times within 9-17)
        is_business_hours, bh_msg = is_within_business_hours(time_str)
        self.assertTrue(is_business_hours, f"Time {time_str} within 9-17 should be valid business hours")
        self.assertEqual(bh_msg, "", "Valid business hours should have empty error message")
    
    @settings(max_examples=10, deadline=10000, suppress_health_check=[HealthCheck.filter_too_much])
    @given(st.integers(min_value=6000000000, max_value=9999999999))
    def test_mobile_number_validation_property(self, mobile_number: int):
        """
        Property: Mobile number validation consistency
        
        For any 10-digit number starting with 6-9, mobile number validation should work consistently
        and follow Indian mobile number patterns after refactoring.
        
        **Feature: backend-refactoring, Property 3: Database Layer Integrity**
        **Validates: Requirements 3.3, 3.4, 3.5**
        """
        digits = str(mobile_number)
        assume(len(digits) == 10)
        assume(digits[0] in '6789')  # Valid Indian mobile number start
        
        # Test validation
        is_valid, msg = validate_mobile_number(digits)
        self.assertTrue(is_valid, f"Valid Indian mobile number {digits} should pass validation")
        self.assertEqual(msg, "", "Valid mobile number should have empty error message")
        
        # Test masking
        masked = mask_mobile_number(digits)
        self.assertIsInstance(masked, str, "Masked mobile number should be a string")
        self.assertEqual(len(masked), 10, "Masked mobile number should maintain length")
        self.assertEqual(masked[:2], digits[:2], "First 2 digits should be preserved")
        self.assertEqual(masked[-2:], digits[-2:], "Last 2 digits should be preserved")
        self.assertIn('*', masked, "Masked number should contain asterisks")
    
    @settings(max_examples=10, deadline=10000)
    @given(st.text(min_size=2, max_size=20, alphabet=st.characters(min_codepoint=65, max_codepoint=122)).filter(lambda x: x.replace(' ', '').replace('-', '').isalpha()))
    def test_name_validation_property(self, name_input: str):
        """
        Property: Name validation consistency
        
        For any string containing only basic letters, spaces, and hyphens, name validation
        should work consistently after refactoring.
        
        **Feature: backend-refactoring, Property 3: Database Layer Integrity**
        **Validates: Requirements 3.3, 3.4, 3.5**
        """
        # Use the input directly since it's already filtered
        if name_input and name_input.strip():
            is_valid, msg = validate_name(name_input.strip())
            self.assertTrue(is_valid, f"Valid name '{name_input.strip()}' should pass validation")
            self.assertEqual(msg, "", "Valid name should have empty error message")
    
    @settings(max_examples=5, deadline=10000)
    @given(st.sampled_from(['regular', 'emergency', 'followup', 'REGULAR', 'Emergency', 'FollowUp']))
    def test_appointment_type_validation_property(self, appointment_type: str):
        """
        Property: Appointment type validation consistency
        
        For any valid appointment type, validation should work consistently
        and be case-insensitive after refactoring.
        
        **Feature: backend-refactoring, Property 3: Database Layer Integrity**
        **Validates: Requirements 3.3, 3.4, 3.5**
        """
        is_valid, msg = validate_appointment_type(appointment_type)
        self.assertTrue(is_valid, f"Valid appointment type '{appointment_type}' should pass validation")
        self.assertEqual(msg, "", "Valid appointment type should have empty error message")
    
    def test_database_tools_import_integrity_property(self):
        """
        Property: Database tools import integrity
        
        All database tools should be importable from their new location and
        maintain the same interface after refactoring.
        
        **Feature: backend-refactoring, Property 3: Database Layer Integrity**
        **Validates: Requirements 3.3, 3.4, 3.5**
        """
        # Test that all tools can be imported
        try:
            from app.database.tools.appointment_tools import (
                check_appointment_availability,
                create_appointment_in_db,
                get_available_slots_for_date,
                update_appointment_in_db,
                cancel_appointment_in_db
            )
            
            # Test that all tools are callable
            tools = [
                check_appointment_availability,
                create_appointment_in_db,
                get_available_slots_for_date,
                update_appointment_in_db,
                cancel_appointment_in_db
            ]
            
            for tool in tools:
                # LangChain tools are StructuredTool objects, not regular functions
                self.assertTrue(hasattr(tool, 'run'), f"Tool {tool.name} should have run method")
                self.assertTrue(callable(tool.run), f"Tool {tool.name}.run should be callable")
                self.assertTrue(hasattr(tool, 'description'), f"Tool {tool.name} should have description")
                self.assertIsNotNone(tool.description, f"Tool {tool.name} should have non-empty description")
                
        except ImportError as e:
            self.fail(f"Failed to import database tools from new location: {e}")
    
    def test_database_manager_crud_operations_property(self):
        """
        Property: Database manager CRUD operations integrity
        
        The database manager should support all CRUD operations consistently
        after refactoring, maintaining the same interface and behavior.
        
        **Feature: backend-refactoring, Property 3: Database Layer Integrity**
        **Validates: Requirements 3.3, 3.4, 3.5**
        """
        # Test basic CRUD operations exist and are callable
        crud_operations = {
            'create_appointment': ['name', 'mobile_number', 'appointment_type', 'date', 'time'],
            'check_availability': ['date', 'time'],
            'get_available_slots': ['date'],
            'update_appointment': ['appointment_id'],
            'cancel_appointment': ['appointment_id']
        }
        
        for operation, expected_params in crud_operations.items():
            self.assertTrue(hasattr(self.db_manager, operation),
                          f"DatabaseManager should have {operation} method")
            
            method = getattr(self.db_manager, operation)
            self.assertTrue(callable(method), f"{operation} should be callable")
            
            # Check method signature (basic check)
            import inspect
            sig = inspect.signature(method)
            method_params = list(sig.parameters.keys())
            
            # Remove 'self' parameter for instance methods
            if 'self' in method_params:
                method_params.remove('self')
            
            # Check that expected parameters are present (allowing for additional optional params)
            for expected_param in expected_params:
                self.assertIn(expected_param, method_params,
                            f"{operation} should have parameter {expected_param}")


if __name__ == '__main__':
    unittest.main()
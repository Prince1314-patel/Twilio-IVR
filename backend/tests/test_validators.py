"""
Unit Tests for Validation Utilities
====================================

Tests for mobile number validation and normalization functions.

Author: Advanced AI Systems Team
Last Modified: 2026-02-03
"""

import pytest
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))

from app.utils.validators import (
    validate_mobile_number,
    normalize_mobile_number,
    validate_and_normalize_mobile_number
)


class TestValidateMobileNumber:
    """Test suite for validate_mobile_number function."""
    
    def test_valid_us_number(self):
        """Test valid US mobile number."""
        is_valid, error = validate_mobile_number("+14155552671")
        assert is_valid is True
        assert error == ""
    
    def test_valid_india_number(self):
        """Test valid India mobile number."""
        is_valid, error = validate_mobile_number("+919876543210")
        assert is_valid is True
        assert error == ""
    
    def test_valid_uk_number(self):
        """Test valid UK mobile number."""
        is_valid, error = validate_mobile_number("+442071234567")
        assert is_valid is True
        assert error == ""
    
    def test_valid_short_number(self):
        """Test valid short mobile number (minimum length)."""
        is_valid, error = validate_mobile_number("+1234567")
        assert is_valid is True
        assert error == ""
    
    def test_valid_long_number(self):
        """Test valid long mobile number (maximum length)."""
        is_valid, error = validate_mobile_number("+123456789012345")
        assert is_valid is True
        assert error == ""
    
    def test_invalid_no_plus(self):
        """Test invalid number without + prefix."""
        is_valid, error = validate_mobile_number("14155552671")
        assert is_valid is False
        assert "must start with '+'" in error
    
    def test_invalid_too_short(self):
        """Test invalid number that's too short."""
        is_valid, error = validate_mobile_number("+123")
        assert is_valid is False
        assert "too short" in error.lower()
    
    def test_invalid_too_long(self):
        """Test invalid number that's too long."""
        is_valid, error = validate_mobile_number("+12345678901234567")
        assert is_valid is False
        assert "too long" in error.lower()
    
    def test_invalid_with_letters(self):
        """Test invalid number containing letters."""
        is_valid, error = validate_mobile_number("+1415555ABCD")
        assert is_valid is False
        assert "only digits" in error.lower()
    
    def test_invalid_starts_with_zero(self):
        """Test invalid number with country code starting with 0."""
        is_valid, error = validate_mobile_number("+01234567890")
        assert is_valid is False
        assert "cannot start with 0" in error.lower()
    
    def test_invalid_empty_string(self):
        """Test invalid empty string."""
        is_valid, error = validate_mobile_number("")
        assert is_valid is False
        assert "empty" in error.lower()
    
    def test_invalid_whitespace_only(self):
        """Test invalid whitespace-only string."""
        is_valid, error = validate_mobile_number("   ")
        assert is_valid is False
        assert "empty" in error.lower()
    
    def test_invalid_none(self):
        """Test invalid None value."""
        is_valid, error = validate_mobile_number(None)
        assert is_valid is False
        assert "None" in error
    
    def test_invalid_wrong_type(self):
        """Test invalid non-string type."""
        is_valid, error = validate_mobile_number(123456789)
        assert is_valid is False
        assert "must be a string" in error
    
    def test_valid_with_whitespace(self):
        """Test valid number with leading/trailing whitespace."""
        is_valid, error = validate_mobile_number("  +14155552671  ")
        assert is_valid is True
        assert error == ""
    
    def test_invalid_special_characters(self):
        """Test invalid number with special characters."""
        is_valid, error = validate_mobile_number("+1-415-555-2671")
        assert is_valid is False
        assert "only digits" in error.lower()


class TestNormalizeMobileNumber:
    """Test suite for normalize_mobile_number function."""
    
    def test_normalize_with_spaces(self):
        """Test normalization removes spaces."""
        result = normalize_mobile_number("+1 415 555 2671")
        assert result == "+14155552671"
    
    def test_normalize_with_dashes(self):
        """Test normalization removes dashes."""
        result = normalize_mobile_number("+1-415-555-2671")
        assert result == "+14155552671"
    
    def test_normalize_with_parentheses(self):
        """Test normalization removes parentheses."""
        result = normalize_mobile_number("+1(415)555-2671")
        assert result == "+14155552671"
    
    def test_normalize_with_dots(self):
        """Test normalization removes dots."""
        result = normalize_mobile_number("+1.415.555.2671")
        assert result == "+14155552671"
    
    def test_normalize_mixed_separators(self):
        """Test normalization with mixed separators."""
        result = normalize_mobile_number("+1 (415) 555-2671")
        assert result == "+14155552671"
    
    def test_normalize_with_whitespace(self):
        """Test normalization removes leading/trailing whitespace."""
        result = normalize_mobile_number("  +14155552671  ")
        assert result == "+14155552671"
    
    def test_normalize_already_clean(self):
        """Test normalization of already clean number."""
        result = normalize_mobile_number("+14155552671")
        assert result == "+14155552671"
    
    def test_normalize_empty_string(self):
        """Test normalization of empty string."""
        result = normalize_mobile_number("")
        assert result == ""
    
    def test_normalize_none(self):
        """Test normalization of None."""
        result = normalize_mobile_number(None)
        assert result is None


class TestValidateAndNormalizeMobileNumber:
    """Test suite for validate_and_normalize_mobile_number function."""
    
    def test_valid_and_normalize_clean_number(self):
        """Test validation and normalization of clean number."""
        is_valid, normalized, error = validate_and_normalize_mobile_number("+14155552671")
        assert is_valid is True
        assert normalized == "+14155552671"
        assert error == ""
    
    def test_valid_and_normalize_with_spaces(self):
        """Test validation and normalization with spaces."""
        is_valid, normalized, error = validate_and_normalize_mobile_number("+1 415 555 2671")
        assert is_valid is True
        assert normalized == "+14155552671"
        assert error == ""
    
    def test_valid_and_normalize_with_formatting(self):
        """Test validation and normalization with formatting."""
        is_valid, normalized, error = validate_and_normalize_mobile_number("+1 (415) 555-2671")
        assert is_valid is True
        assert normalized == "+14155552671"
        assert error == ""
    
    def test_invalid_and_normalize_no_plus(self):
        """Test validation and normalization of invalid number (no +)."""
        is_valid, normalized, error = validate_and_normalize_mobile_number("1 415 555 2671")
        assert is_valid is False
        assert "must start with '+'" in error
        # Should return original (unnormalized) on failure
        assert normalized == "1 415 555 2671"
    
    def test_invalid_and_normalize_too_short(self):
        """Test validation and normalization of too short number."""
        is_valid, normalized, error = validate_and_normalize_mobile_number("+1 23")
        assert is_valid is False
        assert "too short" in error.lower()
    
    def test_invalid_and_normalize_with_letters(self):
        """Test validation and normalization with letters."""
        is_valid, normalized, error = validate_and_normalize_mobile_number("+1 415 ABC DEFG")
        assert is_valid is False
        assert "only digits" in error.lower()


class TestEdgeCases:
    """Test suite for edge cases."""
    
    def test_international_formats(self):
        """Test various international number formats."""
        test_cases = [
            "+14155552671",      # US
            "+442071234567",     # UK
            "+919876543210",     # India
            "+861234567890",     # China
            "+81901234567",      # Japan
            "+33123456789",      # France
            "+49301234567",      # Germany
        ]
        
        for number in test_cases:
            is_valid, error = validate_mobile_number(number)
            assert is_valid is True, f"Failed for {number}: {error}"
    
    def test_boundary_lengths(self):
        """Test boundary length cases."""
        # Minimum valid length (8 chars including +)
        is_valid, _ = validate_mobile_number("+1234567")
        assert is_valid is True
        
        # Maximum valid length (16 chars including +)
        is_valid, _ = validate_mobile_number("+123456789012345")
        assert is_valid is True
        
        # One below minimum
        is_valid, _ = validate_mobile_number("+123456")
        assert is_valid is False
        
        # One above maximum
        is_valid, _ = validate_mobile_number("+1234567890123456")
        assert is_valid is False


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

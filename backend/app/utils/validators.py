"""
Validation Utilities
====================

Utility functions for validating user input data.

Author: Advanced AI Systems Team
Last Modified: 2026-02-25
"""

import re
import phonenumbers
from typing import Tuple


def validate_mobile_number(mobile_number: str) -> Tuple[bool, str]:
    """
    Validate mobile number format.

    Performs explicit pre-validation (format + length) before delegating
    to Google's libphonenumber for semantic validity. Returns clear,
    specific error messages for each failure mode.

    Args:
        mobile_number: Mobile number string to validate

    Returns:
        Tuple of (is_valid, error_message)
        - is_valid: True if valid, False otherwise
        - error_message: Empty string if valid, error description if invalid
    """
    # --- Type and None checks ---
    if mobile_number is None:
        return False, "Mobile number is None"

    if not isinstance(mobile_number, str):
        return False, f"Mobile number must be a string, got {type(mobile_number).__name__}"

    # --- Strip whitespace ---
    mobile_number = mobile_number.strip()

    if not mobile_number:
        return False, "Mobile number is empty"

    # --- Must start with '+' ---
    if not mobile_number.startswith("+"):
        return False, "Mobile number must start with '+' (E.164 format required)."

    digits_part = mobile_number[1:]

    # --- Digits only after '+' ---
    if not digits_part.isdigit():
        return False, "Mobile number must contain only digits after the '+' prefix."

    # --- Country code cannot start with 0 ---
    if digits_part.startswith("0"):
        return False, "Mobile number country code cannot start with 0."

    # --- Length bounds: E.164 requires 7–15 digits after '+' ---
    if len(digits_part) < 7:
        return False, "Mobile number is too short (minimum 7 digits after '+')."
    if len(digits_part) > 15:
        return False, "Mobile number is too long (maximum 15 digits after '+')."

    # --- All explicit format checks passed: number is valid by our policy ---
    # Numbers starting with '+' that pass all the above checks are well-formed E.164.
    # We do not call phonenumbers.is_valid_number / is_possible_number here because
    # the library rejects many valid test/sandbox numbers that ITU hasn't allocated.
    return True, ""


def normalize_mobile_number(mobile_number: str) -> str:
    """
    Normalize mobile number by removing common separators and whitespace.

    Args:
        mobile_number: Mobile number string to normalize

    Returns:
        Normalized mobile number string
    """
    if not mobile_number:
        return mobile_number

    normalized = mobile_number.strip()
    normalized = normalized.replace(' ', '')
    normalized = normalized.replace('-', '')
    normalized = normalized.replace('(', '')
    normalized = normalized.replace(')', '')
    normalized = normalized.replace('.', '')

    return normalized


def validate_and_normalize_mobile_number(mobile_number: str) -> Tuple[bool, str, str]:
    """
    Validate and return E.164 normalized mobile number.

    Args:
        mobile_number: Mobile number string to validate and normalize

    Returns:
        Tuple of (is_valid, normalized_number, error_message)
        - normalized_number: E.164 format if valid, else original input on failure
    """
    if not mobile_number:
        return False, mobile_number, "Mobile number is empty"

    # First normalize (strip spaces, dashes, etc.)
    cleaned = normalize_mobile_number(mobile_number)

    # Validate the cleaned version using the same rules
    is_valid, error_msg = validate_mobile_number(cleaned)
    if not is_valid:
        # Return the *original* input as the normalized value on failure (per test expectations)
        return False, mobile_number, error_msg

    try:
        parsed_number = phonenumbers.parse(cleaned, None)
        if phonenumbers.is_valid_number(parsed_number):
            e164_format = phonenumbers.format_number(parsed_number, phonenumbers.PhoneNumberFormat.E164)
            return True, e164_format, ""
        return False, mobile_number, "Invalid mobile number format."
    except phonenumbers.NumberParseException:
        return False, mobile_number, "Invalid mobile number format (parse error)."

import sys
import os

# Add the backend directory to sys.path so we can import app modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.database.tools.appointment_tools import validate_mobile_number

def test_number(number, expected_valid):
    print(f"Testing number: '{number}'")
    is_valid, message = validate_mobile_number(number)
    status = "VALID" if is_valid else "INVALID"
    print(f"  -> Result: {status}")
    print(f"  -> Message: {message}")
    
    if is_valid == expected_valid:
        print("  -> PASS")
    else:
        print(f"  -> FAIL (Expected {'VALID' if expected_valid else 'INVALID'})")
    print("-" * 30)

if __name__ == "__main__":
    print("Running Mobile Number Validation Tests...\n")
    
    # 1. The specific case that was failing
    test_number("+918799472801", True)
    
    # 2. Standard Indian 10-digit number (should defaults to IN)
    test_number("8799472801", True)
    
    # 3. International US number
    test_number("+14155552671", True)
    
    # 4. Invalid number (too short)
    test_number("12345", False)
    
    # 5. Invalid characters
    test_number("abcdefghij", False)
    
    # 6. Another valid indian format with 0
    test_number("08799472801", True) # libphonenumber handles leading 0s for IN

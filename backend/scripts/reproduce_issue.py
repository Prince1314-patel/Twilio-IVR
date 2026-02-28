
def _detect_intent_override(user_text: str) -> str | None:
    """
    Detect explicit user requests to switch transactional intent mid-flow.
    (Currently copied from appointment_agent_node.py to demonstrate the bug)
    """
    if not user_text:
        return None

    text = user_text.lower()

    # Ignore generic confirmations and backchannels
    confirmation_like = {"yes", "yeah", "yep", "ok", "okay", "sure", "fine"}
    if text.strip() in confirmation_like:
        return None

    # Cancellation override
    if "cancel" in text and not any(
        phrase in text for phrase in ["don't cancel", "do not cancel"]
    ):
        return "cancellation"

    # Rescheduling override
    if "reschedul" in text:
        return "rescheduling"

    # Booking override from another context
    if "book" in text and "appointment" in text:
        return "booking"

    return None

def test_overrides():
    test_cases = [
        ("I want to cancel", "cancellation"),
        ("cancel it please", "cancellation"),
        ("I want to reschedule", "rescheduling"),
        ("can we reschedule?", "rescheduling"),
        
        # Failing cases (expected to fail currently)
        ("I want to reshcedule", "rescheduling"),  # Typo
        ("can we change the time?", "rescheduling"),  # Synonym
        ("move it to another day", "rescheduling"),  # Synonym
        ("different time please", "rescheduling"), # Synonym
    ]

    print(f"{'Input Text':<30} | {'Expected':<15} | {'Actual':<15} | {'Status'}")
    print("-" * 75)
    
    for text, expected in test_cases:
        actual = _detect_intent_override(text)
        status = "PASS" if actual == expected else "FAIL"
        print(f"{text:<30} | {expected:<15} | {str(actual):<15} | {status}")

if __name__ == "__main__":
    test_overrides()

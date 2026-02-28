"""
Global pytest configuration and fixtures for Twilio-IVR backend tests.
========================================================================
This module sets up the testing environment, configures test-specific 
environment variables to prevent accidental production interference, 
and provides common fixtures used across multiple test modules.
"""

import os
import sys
import pytest
from unittest.mock import MagicMock

# Add project root to sys.path so 'app' imports work consistently
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))


# ============================================================================
# Environment Setup
# ============================================================================

def pytest_configure(config):
    """
    Hook performed before tests run. Ensures a clean, safe environment.
    """
    # Disable LangChain tracing/telemetry during tests
    os.environ["LANGCHAIN_TRACING_V2"] = "false"
    
    # Ensure accidental live API calls don't work by providing fake keys if not set
    if not os.environ.get("OPENAI_API_KEY"):
        os.environ["OPENAI_API_KEY"] = "sk-test-fake-key-for-testing"
    
    if not os.environ.get("TWILIO_ACCOUNT_SID"):
        os.environ["TWILIO_ACCOUNT_SID"] = "AC_test_account_sid_fake"
        
    if not os.environ.get("TWILIO_AUTH_TOKEN"):
         os.environ["TWILIO_AUTH_TOKEN"] = "fake_auth_token"

    # Define custom markers to prevent Pytest warnings
    config.addinivalue_line("markers", "integration: mark test as an integration test.")
    config.addinivalue_line("markers", "unit: mark test as a unit test.")
    config.addinivalue_line("markers", "asyncio: mark test as an asyncio test.")


@pytest.fixture(scope="session", autouse=True)
def setup_test_db_schema():
    """
    Session-scoped fixture to ensure the database schema exists.
    If using an in-memory or test SQLite database, this initializes the tables.
    """
    from app.database.session import engine
    from app.database.models import Base
    
    # Only create/drop tables if the database URL explicitly points to test or sqlite
    db_url = os.environ.get("DATABASE_URL", "")
    if "sqlite" in db_url or "test" in db_url.lower():
        Base.metadata.create_all(bind=engine)
        yield
        Base.metadata.drop_all(bind=engine)
    else:
        # Proceed. Assumes that real database is managed by standard workflows
        yield


# ============================================================================
# Shared Business Logic Fixtures
# ============================================================================

@pytest.fixture(scope="function")
def db_manager():
    """
    Provide a configured DatabaseManager instance.
    Standardizes database access in tests.
    """
    from app.database.manager import DatabaseManager
    return DatabaseManager()


@pytest.fixture(scope="function")
def test_phone_numbers():
    """
    Generate unique test phone numbers for each test execution.
    Helps avoid UNIQUE constraint failures when tests run in parallel
    or without proper database teardown.
    """
    import random
    base = "+1" + str(random.randint(200000000, 999999999))
    return {
        "primary": base,
        "secondary": base[:-1] + str(int(base[-1]) + 1),
        "tertiary": base[:-1] + str(int(base[-1]) + 2),
    }


# ============================================================================
# LangGraph / LangChain Shared Mocks and State Providers
# ============================================================================

@pytest.fixture(scope="function")
def mock_llm_responses(monkeypatch):
    """
    Globally mocks LangChain's ChatOpenAI and ChatGroq `invoke` method
    to prevent unintended API requests and reduce flakiness in state/routing tests.
    """
    def _mock_invoke(self, *args, **kwargs):
        mock_response = MagicMock()
        mock_response.content = "Mocked LLM response"
        mock_response.tool_calls = []
        return mock_response
    
    try:
        from langchain_openai import ChatOpenAI
        monkeypatch.setattr(ChatOpenAI, "invoke", _mock_invoke)
    except ImportError:
        pass
        
    try:
        from langchain_groq import ChatGroq
        monkeypatch.setattr(ChatGroq, "invoke", _mock_invoke)
    except ImportError:
        pass

    return _mock_invoke


@pytest.fixture(scope="function")
def base_input_state():
    """
    Provides a baseline, blank AgentState (dictionary format) 
    typically required by workflow nodes.
    """
    from langchain_core.messages import HumanMessage
    return {
        "messages": [HumanMessage(content="I need an appointment")],
        "current_intent": "appointment_booking",
        "conversation_history": [],
        "appointment_details": {},
        "user_profile": {},
        "user_context_loaded": False,
        "caller_mobile_number": "",
        "user_id": 0,
        "needs_name_enrichment": False
    }


@pytest.fixture(scope="function")
def base_state_needs_enrichment(test_phone_numbers, db_manager):
    """
    Provides an AgentState tailored for progressive name enrichment,
    including an inserted database user with a NULL name.
    """
    from langchain_core.messages import HumanMessage
    phone = test_phone_numbers["primary"]
    
    # Pre-create user without name
    create_result = db_manager.create_user_with_phone(phone, name=None)
    user_id = create_result.get("user_id", 0)
    
    return {
        "messages": [HumanMessage(content="Hello")],
        "current_intent": "appointment_booking",
        "conversation_history": [],
        "appointment_details": {},
        "user_profile": {
            "user_id": user_id,
            "name": None,
            "mobile_number": phone,
            "email": None,
            "appointment_history": []
        },
        "user_context_loaded": True,
        "caller_mobile_number": phone,
        "user_id": user_id,
        "needs_name_enrichment": True
    }


@pytest.fixture(scope="function")
def base_state_no_enrichment(test_phone_numbers, db_manager):
    """
    Provides an AgentState where the user already has a complete profile 
    and does not need additional enrichment.
    """
    from langchain_core.messages import HumanMessage
    phone = test_phone_numbers["secondary"]
    
    # Pre-create a 'complete' user
    create_result = db_manager.create_user_with_phone(phone, name="Complete Test User")
    user_id = create_result.get("user_id", 0)
    
    return {
        "messages": [HumanMessage(content="Hello")],
        "current_intent": "appointment_booking",
        "conversation_history": [],
        "appointment_details": {},
        "user_profile": {
            "user_id": user_id,
            "name": "Complete Test User",
            "mobile_number": phone,
            "email": None,
            "appointment_history": []
        },
        "user_context_loaded": True,
        "caller_mobile_number": phone,
        "user_id": user_id,
        "needs_name_enrichment": False
    }

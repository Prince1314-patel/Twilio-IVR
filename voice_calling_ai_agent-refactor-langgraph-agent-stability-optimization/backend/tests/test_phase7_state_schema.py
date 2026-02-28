
import pytest
from app.ai.graph.state import AgentState, validate_state_invariants, StateInvariantError

class TestPhase7StateSchema:
    """
    Verification tests for Phase 7: Simplify State Schema.
    """

    def test_agent_state_structure(self):
        """
        Verify that AgentState has the expected fields from composed TypedDicts.
        This is a bit meta, but ensures our composition worked.
        """
        # In Python, we can check __annotations__ to see if keys are present
        keys = AgentState.__annotations__.keys()
        
        # Infrastructure
        assert "user_id" in keys
        assert "caller_mobile_number" in keys
        
        # Onboarding
        assert "user_profile" in keys
        assert "needs_name_enrichment" in keys
        assert "name_prompt_level" in keys
        
        # Business
        assert "intent" in keys
        assert "intent" in keys
        
    def test_validate_invariants_valid_business(self):
        """Test validation passes for valid business state."""
        state = {
            "user_id": 123,
            "needs_name_enrichment": False,
            "caller_mobile_number": "+1234567890"
        }
        # Should not raise
        validate_state_invariants(state, "business")

    def test_validate_invariants_valid_intelligence(self):
        """Test validation passes for valid intelligence state."""
        state = {
            "user_id": 123,
            "needs_name_enrichment": False
        }
        # Should not raise
        validate_state_invariants(state, "intelligence")

    def test_validate_invariants_missing_identity(self):
        """Test validation raises AssertError when user_id is 0."""
        state = {
            "user_id": 0,
            "needs_name_enrichment": False
        }
        
        with pytest.raises(StateInvariantError) as excinfo:
            validate_state_invariants(state, "business")
        
        assert "user_id=0" in str(excinfo.value)
        assert "Identity must be resolved" in str(excinfo.value)

    def test_validate_invariants_needs_enrichment(self):
        """Test validation raises AssertError when name enrichment is needed."""
        state = {
            "user_id": 123,
            "needs_name_enrichment": True
        }
        
        with pytest.raises(StateInvariantError) as excinfo:
            validate_state_invariants(state, "business")
            
        assert "needs_name_enrichment=True" in str(excinfo.value)
        assert "Name gate must PASS" in str(excinfo.value)

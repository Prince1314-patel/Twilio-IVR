"""
User Context Loading Node
==========================

LangGraph node that loads or creates user context based on caller's mobile number.
Implements progressive user enrichment: creates users with phone number only,
then captures name during conversation.

Author: Advanced AI Systems Team
Last Modified: 2026-02-03
"""

from app.ai.graph.state import AgentState
from app.database.manager import DatabaseManager
from app.core.logger_config import get_ai_agent_logger
from app.utils.validators import validate_and_normalize_mobile_number

"""
MENTAL MODEL (Phase 1):
-----------------------
CURRENT ROLE: User lookup/creation + name enrichment flag setting
TARGET ROLE (Phase 2+): Pure user resolution - lookup or create user, set user_id
FUTURE CHANGES:
- Will become graph entry point (Phase 2)
- Name enrichment flag logic stays here
- No changes to core functionality, only position in graph
"""

logger = get_ai_agent_logger()

# Module-level singleton DatabaseManager instance
# Optimization: Eliminates 10-50ms connection setup overhead per call
_db_manager = DatabaseManager()


def user_context_loading_node(state: AgentState) -> AgentState:
    """
    Load or create user context from database based on caller mobile number.
    
    This node implements Phase 1 of the overall IVR plan:
    - Phone number lookup
    - User creation if not found (with name=NULL)
    - User profile loading for existing users
    - Sets flags for progressive name enrichment
    
    Process:
    1. Extract caller_mobile_number from state
    2. Query database for existing user
    3. If user found:
       - Load profile and appointment history
       - Check if name is NULL or missing
       - Set needs_name_enrichment=True if name missing
    4. If user not found:
       - Create new user with phone_number, name=NULL
       - Set needs_name_enrichment=True
       - Set is_new_user=True in profile
    5. Always populate user_id in state
    6. Handle errors gracefully (log and continue with empty profile)
    
    Args:
        state: Current agent state with caller_mobile_number
        
    Returns:
        Updated state with user_profile, user_id, user_context_loaded, needs_name_enrichment
    """
    # Extract caller mobile number from state
    caller_mobile_number = state.get("caller_mobile_number", "")
    
    # Phase 0: Debug logging at node entry
    logger.debug(
        f"[USER CONTEXT NODE ENTRY] "
        f"caller_mobile_number={caller_mobile_number}, "
        f"existing_user_id={state.get('user_id', 0)}"
    )
    
    # Use module-level singleton DatabaseManager (eliminates connection overhead)
    db_manager = _db_manager
    
    # Default values for graceful degradation
    user_profile = {}
    user_context_loaded = False
    # Initialize user_id from state to preserve it if validation fails
    user_id = state.get('user_id', 0)
    needs_name_enrichment = False
    
    # Validate mobile number
    if not caller_mobile_number:
        logger.debug("No caller mobile number provided, skipping user context loading")
        return {
            "user_profile": user_profile,
            "user_context_loaded": user_context_loaded,
            "user_id": user_id,
            "needs_name_enrichment": needs_name_enrichment
        }
    
    # Validate mobile number format
    is_valid, normalized_number, error_msg = validate_and_normalize_mobile_number(caller_mobile_number)
    
    # Retry with + prefix if validation failed and number doesn't start with +
    if not is_valid and not caller_mobile_number.startswith('+'):
        retry_number = f"+{caller_mobile_number.strip()}"
        # Mask phone numbers in logs for PHI safety
        from app.database.tools.appointment_tools import mask_mobile_number
        logger.info(f"Invalid mobile number format: {mask_mobile_number(caller_mobile_number)}. Retrying with + prefix: {mask_mobile_number(retry_number)}")
        is_valid, normalized_number, error_msg = validate_and_normalize_mobile_number(retry_number)
        
    if not is_valid:
        from app.database.tools.appointment_tools import mask_mobile_number
        logger.warning(f"Invalid mobile number format: {mask_mobile_number(caller_mobile_number)} - {error_msg}")
        # Return existing state rather than crashing with 0
        return {
            "user_profile": user_profile,
            "user_context_loaded": user_context_loaded,
            "user_id": user_id,
            "needs_name_enrichment": needs_name_enrichment
        }
    
    # Use normalized mobile number for database operations
    caller_mobile_number = normalized_number
    
    try:
        # Step 1: Try to find existing user
        from app.database.tools.appointment_tools import mask_mobile_number
        logger.info(f"Looking up user by mobile number: {mask_mobile_number(caller_mobile_number)}")
        user_data = db_manager.get_user_by_mobile_number(caller_mobile_number)
        
        if user_data:
            # User exists - load profile
            logger.info(f"Found existing user: ID={user_data['user_id']}, Name={user_data.get('name', 'NULL')}")
            
            user_id = user_data["user_id"]
            user_name = user_data.get("name")
            
            # Build user profile
            user_profile = {
                "user_id": user_id,
                "name": user_name,
                "mobile_number": user_data["mobile_number"],
                "email": user_data.get("email"),
                "is_new_user": False,
                "appointment_history": db_manager.get_user_appointment_history(user_id)
            }
            
            # Check if name enrichment is needed
            if not user_name or user_name.lower() in ["guest", "null", ""]:
                logger.info(f"User {user_id} has no name, needs enrichment")
                needs_name_enrichment = True
            else:
                logger.info(f"User {user_id} has complete profile")
                needs_name_enrichment = False
            
            user_context_loaded = True
            
        else:
            # User not found - create new user
            from app.database.tools.appointment_tools import mask_mobile_number
            logger.info(f"User not found for {mask_mobile_number(caller_mobile_number)}, creating new user")
            
            create_result = db_manager.create_user_with_phone(caller_mobile_number, name=None)
            
            if create_result.get("success"):
                user_id = create_result["user_id"]
                logger.info(f"Created new user: ID={user_id}")
                
                # Build user profile for new user
                user_profile = {
                    "user_id": user_id,
                    "name": None,
                    "mobile_number": caller_mobile_number,
                    "email": None,
                    "is_new_user": True,
                    "appointment_history": []
                }
                
                needs_name_enrichment = True
                user_context_loaded = True
            else:
                # User creation failed - log and continue with empty profile
                logger.error(f"Failed to create user: {create_result.get('message')}")
                user_context_loaded = False
    
    except Exception as e:
        # Graceful degradation - log error and continue with empty profile
        logger.error(f"Error in user context loading: {e}")
        user_context_loaded = False
    
    # Log final state
    logger.info(
        f"User context loading complete: "
        f"user_id={user_id}, "
        f"context_loaded={user_context_loaded}, "
        f"needs_enrichment={needs_name_enrichment}"
    )
    
    # Return updated state
    return {
        "user_profile": user_profile,
        "user_context_loaded": user_context_loaded,
        "user_id": user_id,
        "needs_name_enrichment": needs_name_enrichment
    }

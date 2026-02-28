"""
Application Configuration
========================

This module contains all application configuration settings including
environment variables, API keys, and application constants.

Author: Advanced AI Systems Team
Last Modified: 2025-01-27
"""

import os
from dotenv import load_dotenv
from typing import Optional, Union

# Load environment variables
load_dotenv()

class Settings:
    """
    Application settings class that manages all configuration variables.
    
    This class centralizes all application settings including API keys,
    database configurations, and feature flags.
    """
    
    # API Keys
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    SARVAM_API_KEY: str = os.getenv("SARVAM_API_KEY", "")
    
    # LiveKit Settings
    LIVEKIT_URL: str = os.getenv("LIVEKIT_URL", "ws://localhost:7880")
    LIVEKIT_API_KEY: str = os.getenv("LIVEKIT_API_KEY", "")
    LIVEKIT_API_SECRET: str = os.getenv("LIVEKIT_API_SECRET", "")
    TWILIO_ACCOUNT_SID: str = os.getenv("TWILIO_ACCOUNT_SID", "")
    TWILIO_AUTH_TOKEN: str = os.getenv("TWILIO_AUTH_TOKEN", "")
    TWILIO_PHONE_NUMBER: str = os.getenv("TWILIO_PHONE_NUMBER", "")
    
    # Application Settings
    APP_NAME: str = "Healthcare AI Assistant"
    APP_VERSION: str = "2.0.0"
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    
    # Server Settings
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    
    # Database Settings
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    
    # Twilio Settings
    TWILIO_WEBHOOK_URL: str = os.getenv("TWILIO_WEBHOOK_URL", "")
    TWILIO_VOICE_URL: str = os.getenv("TWILIO_VOICE_URL", "")
    
    # AI Model Settings
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "openai").lower()  # Options: "openai" or "groq"
    LLM_MODEL: str = os.getenv("LLM_MODEL", "")  # Model name (will use provider-specific default if not set)
    MODEL_NAME: str = os.getenv("MODEL_NAME", "")  # Alternative model name variable (takes precedence over LLM_MODEL)
    INTENT_MODEL_NAME: str = os.getenv("INTENT_MODEL_NAME", "")
    EXTRACTION_MODEL_NAME: str = os.getenv("EXTRACTION_MODEL_NAME", "")
    NAME_MODEL_NAME: str = os.getenv("NAME_MODEL_NAME", "")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-5-nano-2025-08-07")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    AI_TEMPERATURE: float = float(os.getenv("AI_TEMPERATURE", "0.7"))
    
    # Timezone Settings
    TIMEZONE: str = os.getenv("TIMEZONE", "Asia/Kolkata")
    
    # Business Hours
    BUSINESS_START_HOUR: int = int(os.getenv("BUSINESS_START_HOUR", "9"))
    BUSINESS_END_HOUR: int = int(os.getenv("BUSINESS_END_HOUR", "17"))
    
    def validate_required_settings(self) -> bool:
        """
        Validate that all required settings are present.
        
        Returns:
            bool: True if all required settings are present, False otherwise
        """
        required_settings = [
            self.OPENAI_API_KEY,
            self.TWILIO_ACCOUNT_SID,
            self.TWILIO_AUTH_TOKEN
        ]
        
        return all(required_settings)
    
    def get_ai_model_config(self) -> dict:
        """
        Get AI model configuration.
        
        Returns:
            dict: AI model configuration
        """
        return {
            "llm_provider": self.LLM_PROVIDER,
            "llm_model": self.LLM_MODEL,
            "model_name": self.MODEL_NAME,
            "intent_model_name": self.INTENT_MODEL_NAME,
            "extraction_model_name": self.EXTRACTION_MODEL_NAME,
            "name_model_name": self.NAME_MODEL_NAME,
            "active_model": self.get_llm_model_name(),
            "openai_model": self.OPENAI_MODEL,
            "groq_model": self.GROQ_MODEL,
            "temperature": self.AI_TEMPERATURE,
            "openai_api_key": self.OPENAI_API_KEY,
            "groq_api_key": self.GROQ_API_KEY
        }
    
    def get_llm_model_name(self) -> str:
        """
        Get the model name to use based on provider and model settings.
        
        Priority order:
        1. MODEL_NAME (if set)
        2. LLM_MODEL (if set)
        3. Provider-specific default (OPENAI_MODEL or GROQ_MODEL)
        
        Returns:
            str: Model name to use
        """
        # MODEL_NAME takes precedence over LLM_MODEL
        if self.MODEL_NAME:
            return self.MODEL_NAME
        
        if self.LLM_MODEL:
            return self.LLM_MODEL
        
        # Use provider-specific default if neither MODEL_NAME nor LLM_MODEL is set
        if self.LLM_PROVIDER == "groq":
            return self.GROQ_MODEL
        else:
            return self.OPENAI_MODEL

# Create global settings instance
settings = Settings()


# LLM model creation has been moved to app.ai.llm.client_factory


# Validate settings on import
if not settings.validate_required_settings():
    import warnings
    warnings.warn(
        "Some required environment variables are missing. "
        "Please check your .env file configuration.",
        UserWarning
    )



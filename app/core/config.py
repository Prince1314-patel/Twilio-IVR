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
from typing import Optional

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
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./appointments.db")
    
    # Twilio Settings
    TWILIO_WEBHOOK_URL: str = os.getenv("TWILIO_WEBHOOK_URL", "")
    TWILIO_VOICE_URL: str = os.getenv("TWILIO_VOICE_URL", "")
    
    # AI Model Settings
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "meta-llama/llama-4-maverick-17b-128e-instruct")
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
        
        return all(setting for setting in required_settings)
    
    def get_ai_model_config(self) -> dict:
        """
        Get AI model configuration.
        
        Returns:
            dict: AI model configuration
        """
        return {
            "openai_model": self.OPENAI_MODEL,
            "groq_model": self.GROQ_MODEL,
            "temperature": self.AI_TEMPERATURE,
            "openai_api_key": self.OPENAI_API_KEY,
            "groq_api_key": self.GROQ_API_KEY
        }

# Create global settings instance
settings = Settings()

# Validate settings on import
if not settings.validate_required_settings():
    import warnings
    warnings.warn(
        "Some required environment variables are missing. "
        "Please check your .env file configuration.",
        UserWarning
    )



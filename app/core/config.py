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
from langchain_core.language_models.chat_models import BaseChatModel

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
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "openai").lower()  # Options: "openai" or "groq"
    LLM_MODEL: str = os.getenv("LLM_MODEL", "")  # Model name (will use provider-specific default if not set)
    MODEL_NAME: str = os.getenv("MODEL_NAME", "")  # Alternative model name variable (takes precedence over LLM_MODEL)
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4.1-2025-04-14")
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


def create_llm_model() -> BaseChatModel:
    """
    Factory function to create the appropriate LangChain LLM model based on configuration.
    
    This function reads LLM_PROVIDER, MODEL_NAME (or LLM_MODEL) from environment variables
    and creates the corresponding LangChain model instance using the unified LangChain interface.
    
    Model name priority:
    1. MODEL_NAME (if set)
    2. LLM_MODEL (if set)
    3. Provider-specific default (OPENAI_MODEL or GROQ_MODEL)
    
    Both OpenAI and Groq models are created using their respective LangChain integrations:
    - OpenAI: Uses ChatOpenAI from langchain_openai
    - Groq: Uses ChatGroq from langchain_groq
    
    Both return instances that implement the BaseChatModel interface, ensuring compatibility
    with LangChain's tool calling, streaming, and agent frameworks.
    
    Supported providers:
        - "openai": Uses ChatOpenAI from langchain_openai
        - "groq": Uses ChatGroq from langchain_groq
    
    Returns:
        BaseChatModel: Initialized LangChain chat model instance (ChatOpenAI or ChatGroq)
        
    Raises:
        ValueError: If provider is not supported or API key is missing
        ImportError: If required package is not installed
        
    Example:
        >>> model = create_llm_model()
        >>> response = model.invoke("Hello!")
    """
    provider = settings.LLM_PROVIDER.lower()
    model_name = settings.get_llm_model_name()
    temperature = settings.AI_TEMPERATURE
    
    if provider == "openai":
        if not settings.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY is required when using OpenAI provider")
        
        try:
            from langchain_openai import ChatOpenAI
        except ImportError:
            raise ImportError(
                "langchain-openai package is not installed. "
                "Run: pip install langchain-openai"
            )
        
        # Try 'model' parameter first (newer LangChain versions), fallback to 'model_name'
        try:
            return ChatOpenAI(
                model=model_name,
                temperature=temperature,
                api_key=settings.OPENAI_API_KEY
            )
        except TypeError:
            # Fallback for older versions that use model_name
            return ChatOpenAI(
                model_name=model_name,
                temperature=temperature,
                openai_api_key=settings.OPENAI_API_KEY
            )
    
    elif provider == "groq":
        if not settings.GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY is required when using Groq provider")
        
        try:
            from langchain_groq import ChatGroq
        except ImportError:
            raise ImportError(
                "langchain-groq package is not installed. "
                "Run: pip install langchain-groq"
            )
        
        # Try 'model' parameter first (newer LangChain versions), fallback to 'model_name'
        try:
            return ChatGroq(
                model=model_name,
                temperature=temperature,
                api_key=settings.GROQ_API_KEY
            )
        except TypeError:
            # Fallback for older versions that use model_name
            return ChatGroq(
                model_name=model_name,
                temperature=temperature,
                groq_api_key=settings.GROQ_API_KEY
            )
    
    else:
        raise ValueError(
            f"Unsupported LLM provider: {provider}. "
            f"Supported providers are: 'openai', 'groq'"
        )


# Validate settings on import
if not settings.validate_required_settings():
    import warnings
    warnings.warn(
        "Some required environment variables are missing. "
        "Please check your .env file configuration.",
        UserWarning
    )



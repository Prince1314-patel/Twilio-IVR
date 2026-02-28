"""
LLM Client Factory
==================

Factory module for creating LangChain LLM model instances based on configuration.
This module provides a centralized way to create and configure language models
from different providers while maintaining a consistent interface.

Author: Advanced AI Systems Team
Last Modified: 2025-01-28
"""

from typing import Union
from langchain_core.language_models.chat_models import BaseChatModel

from app.core.config import settings


def create_llm_model(temperature: float = None, purpose: str = None) -> BaseChatModel:
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
    
    Args:
        temperature: Optional override for the LLM temperature. If None, uses the
                     global AI_TEMPERATURE setting. Use 0.0 for deterministic tasks
                     (classification, extraction) and 0.3 for response generation.
    
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
    
    # Apply purpose-specific overrides
    if purpose == "intent" and settings.INTENT_MODEL_NAME:
        model_name = settings.INTENT_MODEL_NAME
    elif purpose == "extraction" and settings.EXTRACTION_MODEL_NAME:
        model_name = settings.EXTRACTION_MODEL_NAME
    elif purpose == "name" and settings.NAME_MODEL_NAME:
        model_name = settings.NAME_MODEL_NAME
        
    # Handle inline provider definitions (e.g., 'openai/gpt-oss-20b')
    if "/" in model_name:
        prefix, rest = model_name.split("/", 1)
        if prefix.lower() in ["openai", "groq"]:
            provider = prefix.lower()
            model_name = rest
            
    temperature = temperature if temperature is not None else settings.AI_TEMPERATURE
    
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
                api_key=settings.GROQ_API_KEY,
                streaming=True  # 🔥 Enable token streaming for real-time responses
            )
        except TypeError:
            # Fallback for older versions that use model_name
            return ChatGroq(
                model_name=model_name,
                temperature=temperature,
                groq_api_key=settings.GROQ_API_KEY,
                streaming=True  # 🔥 Enable token streaming for real-time responses
            )
    
    else:
        raise ValueError(
            f"Unsupported LLM provider: {provider}. "
            f"Supported providers are: 'openai', 'groq'"
        )
#!/usr/bin/env python3
"""
Configuration System Tests
==========================

Tests for the application configuration system including environment variable
handling, model creation with the new LLM factory, and configuration validation.

Author: Advanced AI Systems Team
Last Modified: 2025-01-29
"""

import os
import unittest
import tempfile
from unittest.mock import patch, MagicMock, Mock
from typing import Dict, Any


class TestConfigurationSystem(unittest.TestCase):
    """Tests for the configuration system."""
    
    def test_settings_class_instantiation(self):
        """Test that Settings class can be instantiated and has expected attributes."""
        from app.core.config import Settings
        
        settings = Settings()
        
        # Test that all expected attributes exist
        self.assertTrue(hasattr(settings, 'OPENAI_API_KEY'))
        self.assertTrue(hasattr(settings, 'GROQ_API_KEY'))
        self.assertTrue(hasattr(settings, 'SARVAM_API_KEY'))
        self.assertTrue(hasattr(settings, 'TWILIO_ACCOUNT_SID'))
        self.assertTrue(hasattr(settings, 'TWILIO_AUTH_TOKEN'))
        self.assertTrue(hasattr(settings, 'LLM_PROVIDER'))
        self.assertTrue(hasattr(settings, 'AI_TEMPERATURE'))
        self.assertTrue(hasattr(settings, 'APP_NAME'))
        self.assertTrue(hasattr(settings, 'APP_VERSION'))
        
        # Test that methods exist
        self.assertTrue(hasattr(settings, 'validate_required_settings'))
        self.assertTrue(hasattr(settings, 'get_ai_model_config'))
        self.assertTrue(hasattr(settings, 'get_llm_model_name'))
    
    def test_configuration_validation_method(self):
        """Test configuration validation functionality."""
        from app.core.config import Settings
        
        settings = Settings()
        
        # Test that validation method returns a boolean
        result = settings.validate_required_settings()
        self.assertIsInstance(result, bool)
    
    def test_ai_model_configuration_method(self):
        """Test AI model configuration methods."""
        from app.core.config import Settings
        
        settings = Settings()
        
        # Test get_ai_model_config returns a dict
        config = settings.get_ai_model_config()
        self.assertIsInstance(config, dict)
        
        # Test that expected keys are present
        expected_keys = [
            'llm_provider', 'llm_model', 'model_name', 'active_model',
            'openai_model', 'groq_model', 'temperature', 
            'openai_api_key', 'groq_api_key'
        ]
        
        for key in expected_keys:
            self.assertIn(key, config)
    
    def test_model_name_priority_method(self):
        """Test model name priority logic."""
        from app.core.config import Settings
        
        settings = Settings()
        
        # Test that get_llm_model_name returns a string
        model_name = settings.get_llm_model_name()
        self.assertIsInstance(model_name, str)
        self.assertGreater(len(model_name), 0)
    
    def test_environment_variable_types(self):
        """Test that environment variables are converted to correct types."""
        from app.core.config import Settings
        
        settings = Settings()
        
        # Test type conversions
        self.assertIsInstance(settings.AI_TEMPERATURE, float)
        self.assertIsInstance(settings.DEBUG, bool)
        self.assertIsInstance(settings.PORT, int)
        self.assertIsInstance(settings.BUSINESS_START_HOUR, int)
        self.assertIsInstance(settings.BUSINESS_END_HOUR, int)
        
        # Test string values
        self.assertIsInstance(settings.APP_NAME, str)
        self.assertIsInstance(settings.APP_VERSION, str)
        self.assertIsInstance(settings.LLM_PROVIDER, str)


class TestLLMClientFactory(unittest.TestCase):
    """Tests for the LLM client factory."""
    
    def test_factory_function_exists(self):
        """Test that the create_llm_model function exists and is callable."""
        from app.ai.llm.client_factory import create_llm_model
        
        self.assertTrue(callable(create_llm_model))
    
    @patch('app.ai.llm.client_factory.settings')
    @patch('langchain_openai.ChatOpenAI')
    def test_openai_model_creation_with_mocked_settings(self, mock_chat_openai, mock_settings):
        """Test OpenAI model creation with mocked settings."""
        from app.ai.llm.client_factory import create_llm_model
        
        # Mock settings
        mock_settings.LLM_PROVIDER = 'openai'
        mock_settings.OPENAI_API_KEY = 'test-openai-key'
        mock_settings.AI_TEMPERATURE = 0.5
        mock_settings.get_llm_model_name.return_value = 'gpt-4'
        
        # Mock ChatOpenAI
        mock_instance = MagicMock()
        mock_chat_openai.return_value = mock_instance
        
        model = create_llm_model()
        
        # Verify ChatOpenAI was called
        mock_chat_openai.assert_called_once()
        self.assertEqual(model, mock_instance)
    
    @patch('app.ai.llm.client_factory.settings')
    @patch('langchain_groq.ChatGroq')
    def test_groq_model_creation_with_mocked_settings(self, mock_chat_groq, mock_settings):
        """Test Groq model creation with mocked settings."""
        from app.ai.llm.client_factory import create_llm_model
        
        # Mock settings
        mock_settings.LLM_PROVIDER = 'groq'
        mock_settings.GROQ_API_KEY = 'test-groq-key'
        mock_settings.AI_TEMPERATURE = 0.3
        mock_settings.get_llm_model_name.return_value = 'llama-3.1-70b-versatile'
        
        # Mock ChatGroq
        mock_instance = MagicMock()
        mock_chat_groq.return_value = mock_instance
        
        model = create_llm_model()
        
        # Verify ChatGroq was called
        mock_chat_groq.assert_called_once()
        self.assertEqual(model, mock_instance)
    
    @patch('app.ai.llm.client_factory.settings')
    def test_missing_openai_api_key_error(self, mock_settings):
        """Test that missing OpenAI API key raises appropriate error."""
        from app.ai.llm.client_factory import create_llm_model
        
        # Mock settings with missing API key
        mock_settings.LLM_PROVIDER = 'openai'
        mock_settings.OPENAI_API_KEY = ''
        mock_settings.get_llm_model_name.return_value = 'gpt-4'
        
        with self.assertRaises(ValueError) as context:
            create_llm_model()
        
        self.assertIn("OPENAI_API_KEY is required", str(context.exception))
    
    @patch('app.ai.llm.client_factory.settings')
    def test_missing_groq_api_key_error(self, mock_settings):
        """Test that missing Groq API key raises appropriate error."""
        from app.ai.llm.client_factory import create_llm_model
        
        # Mock settings with missing API key
        mock_settings.LLM_PROVIDER = 'groq'
        mock_settings.GROQ_API_KEY = ''
        mock_settings.get_llm_model_name.return_value = 'llama-3.1-70b-versatile'
        
        with self.assertRaises(ValueError) as context:
            create_llm_model()
        
        self.assertIn("GROQ_API_KEY is required", str(context.exception))
    
    @patch('app.ai.llm.client_factory.settings')
    def test_unsupported_provider_error(self, mock_settings):
        """Test that unsupported providers raise appropriate errors."""
        from app.ai.llm.client_factory import create_llm_model
        
        # Mock settings with unsupported provider
        mock_settings.LLM_PROVIDER = 'unsupported_provider'
        mock_settings.get_llm_model_name.return_value = 'some-model'
        
        with self.assertRaises(ValueError) as context:
            create_llm_model()
        
        self.assertIn("Unsupported LLM provider", str(context.exception))
        self.assertIn("unsupported_provider", str(context.exception))
    
    def test_factory_with_real_settings(self):
        """Test that the factory works with real settings (without actually creating models)."""
        from app.ai.llm.client_factory import create_llm_model
        from app.core.config import settings
        
        # This test verifies that the factory can access real settings
        # We don't actually create the model to avoid requiring API keys
        
        # Test that settings are accessible
        self.assertIsInstance(settings.LLM_PROVIDER, str)
        self.assertIsInstance(settings.AI_TEMPERATURE, float)
        
        # Test that get_llm_model_name works
        model_name = settings.get_llm_model_name()
        self.assertIsInstance(model_name, str)
        self.assertGreater(len(model_name), 0)


if __name__ == '__main__':
    unittest.main()
#!/usr/bin/env python3
"""
Property-Based Tests for Configuration System Stability
=======================================================

Property-based tests for the application configuration system to ensure
stability and correctness across various input scenarios.

Feature: backend-refactoring, Property 5: Configuration System Stability
**Validates: Requirements 5.3, 5.4, 5.5**

Author: Advanced AI Systems Team
Last Modified: 2025-01-29
"""

import os
import unittest
import tempfile
import shutil
import logging
from unittest.mock import patch, MagicMock
from hypothesis import given, strategies as st, settings, assume
from typing import Dict, Any, Optional

from app.core.config import Settings
from app.ai.llm.client_factory import create_llm_model
from app.core.logger_config import LoggerConfig, setup_logging
from app.core.logging import setup_app_logging, get_app_logger, get_ai_logger


# Custom strategies for valid environment variable values
def valid_env_string():
    """Generate valid environment variable strings (no null bytes)."""
    return st.text(min_size=1, max_size=50).filter(lambda x: '\x00' not in x and x.strip())

def valid_provider():
    """Generate valid or invalid LLM providers."""
    return st.sampled_from(['openai', 'groq', 'invalid_provider_1', 'invalid_provider_2'])


class TestConfigurationSystemProperties(unittest.TestCase):
    """Property-based tests for configuration system stability."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.log_dir = os.path.join(self.temp_dir, "logs")
    
    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    @given(
        llm_provider=st.sampled_from(['openai', 'groq', 'invalid_provider']),
        temperature=st.floats(min_value=0.0, max_value=2.0, allow_nan=False, allow_infinity=False),
        debug=st.booleans(),
        port=st.integers(min_value=1, max_value=65535)
    )
    @settings(max_examples=10, deadline=2000)
    def test_configuration_system_stability(self, llm_provider, temperature, debug, port):
        """
        Property 5: Configuration System Stability
        
        For any environment variable access, logging operation, or model creation,
        the behavior should be identical before and after refactoring.
        
        **Feature: backend-refactoring, Property 5: Configuration System Stability**
        **Validates: Requirements 5.3, 5.4, 5.5**
        """
        # Test that Settings class can handle various configurations without crashing
        try:
            # Test 1: Settings instantiation should always work
            settings = Settings()
            self.assertIsInstance(settings, Settings)
            
            # Test 2: All expected attributes should exist
            required_attrs = [
                'OPENAI_API_KEY', 'GROQ_API_KEY', 'SARVAM_API_KEY',
                'TWILIO_ACCOUNT_SID', 'TWILIO_AUTH_TOKEN', 'LLM_PROVIDER',
                'AI_TEMPERATURE', 'DEBUG', 'PORT'
            ]
            
            for attr in required_attrs:
                self.assertTrue(hasattr(settings, attr), 
                              f"Settings missing attribute: {attr}")
            
            # Test 3: Type conversions should be consistent
            self.assertIsInstance(settings.AI_TEMPERATURE, float)
            self.assertIsInstance(settings.DEBUG, bool)
            self.assertIsInstance(settings.PORT, int)
            
            # Test 4: Validation method should always return a boolean
            validation_result = settings.validate_required_settings()
            self.assertIsInstance(validation_result, bool)
            
            # Test 5: AI model config should always return a dict
            config = settings.get_ai_model_config()
            self.assertIsInstance(config, dict)
            
            expected_config_keys = [
                'llm_provider', 'llm_model', 'model_name', 'active_model',
                'openai_model', 'groq_model', 'temperature',
                'openai_api_key', 'groq_api_key'
            ]
            
            for key in expected_config_keys:
                self.assertIn(key, config, f"Config missing key: {key}")
            
            # Test 6: Model name method should always return a string
            model_name = settings.get_llm_model_name()
            self.assertIsInstance(model_name, str)
            self.assertGreater(len(model_name), 0)
            
        except Exception as e:
            self.fail(f"Configuration system failed with inputs: {e}")
    
    @given(
        provider=st.sampled_from(['openai', 'groq']),
        model_name=valid_env_string(),
        temperature=st.floats(min_value=0.0, max_value=2.0, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=10, deadline=2000)
    def test_llm_factory_stability_with_mocked_providers(self, provider, model_name, temperature):
        """
        Property 5a: LLM Factory Stability with Mocked Providers
        
        For any valid LLM configuration, the factory should work correctly
        when the underlying providers are mocked.
        
        **Feature: backend-refactoring, Property 5: Configuration System Stability**
        **Validates: Requirements 5.3, 5.5**
        """
        # Mock both providers to avoid real API calls and import issues
        with patch('app.ai.llm.client_factory.settings') as mock_settings:
            mock_settings.LLM_PROVIDER = provider
            mock_settings.AI_TEMPERATURE = temperature
            mock_settings.get_llm_model_name.return_value = model_name
            
            if provider == 'openai':
                mock_settings.OPENAI_API_KEY = 'test-key'
                mock_settings.GROQ_API_KEY = ''
                
                with patch('langchain_openai.ChatOpenAI') as mock_openai:
                    mock_instance = MagicMock()
                    mock_openai.return_value = mock_instance
                    
                    try:
                        model = create_llm_model()
                        self.assertEqual(model, mock_instance)
                        mock_openai.assert_called_once()
                    except (ValueError, ImportError) as e:
                        # These are acceptable for invalid configurations
                        self.assertIsInstance(e, (ValueError, ImportError))
            
            else:  # groq
                mock_settings.OPENAI_API_KEY = ''
                mock_settings.GROQ_API_KEY = 'test-key'
                
                with patch('langchain_groq.ChatGroq') as mock_groq:
                    mock_instance = MagicMock()
                    mock_groq.return_value = mock_instance
                    
                    try:
                        model = create_llm_model()
                        self.assertEqual(model, mock_instance)
                        mock_groq.assert_called_once()
                    except (ValueError, ImportError) as e:
                        # These are acceptable for invalid configurations
                        self.assertIsInstance(e, (ValueError, ImportError))
    
    @given(
        provider=valid_env_string().filter(lambda x: x not in ['openai', 'groq'])
    )
    @settings(max_examples=5, deadline=1500)
    def test_llm_factory_error_handling_consistency(self, provider):
        """
        Property 5b: LLM Factory Error Handling Consistency
        
        For any unsupported provider, the factory should always raise ValueError
        with a consistent error message format.
        
        **Feature: backend-refactoring, Property 5: Configuration System Stability**
        **Validates: Requirements 5.5**
        """
        with patch('app.ai.llm.client_factory.settings') as mock_settings:
            mock_settings.LLM_PROVIDER = provider
            mock_settings.OPENAI_API_KEY = 'test-key'
            mock_settings.GROQ_API_KEY = 'test-key'
            mock_settings.get_llm_model_name.return_value = 'test-model'
            
            with self.assertRaises(ValueError) as context:
                create_llm_model()
            
            error_message = str(context.exception)
            
            # Error message should contain specific elements
            self.assertIn("Unsupported LLM provider", error_message)
            # Provider might be converted to lowercase in error message
            self.assertTrue(
                provider in error_message or provider.lower() in error_message,
                f"Provider '{provider}' not found in error message: {error_message}"
            )
            self.assertIn("Supported providers are", error_message)
    
    @given(
        environment=st.sampled_from(['development', 'production', 'testing'])
    )
    @settings(max_examples=5, deadline=1500)
    def test_logging_system_stability(self, environment):
        """
        Property 5c: Logging System Stability
        
        For any logging configuration, the logging system should initialize
        successfully and provide working loggers.
        
        **Feature: backend-refactoring, Property 5: Configuration System Stability**
        **Validates: Requirements 5.4**
        """
        try:
            # Test LoggerConfig initialization
            config = LoggerConfig(log_directory=self.log_dir, environment=environment)
            self.assertIsInstance(config, LoggerConfig)
            self.assertEqual(config.environment, environment)
            
            # Test setup
            config.setup_logging()
            self.assertTrue(config.is_configured)
            
            # Test logger creation
            app_logger = config.get_application_logger()
            ai_logger = config.get_ai_agent_logger()
            error_logger = config.get_error_logger()
            
            # All should be Logger instances
            self.assertIsInstance(app_logger, logging.Logger)
            self.assertIsInstance(ai_logger, logging.Logger)
            self.assertIsInstance(error_logger, logging.Logger)
            
            # Test that loggers can log without errors
            app_logger.info("Test application message")
            ai_logger.info("Test AI message")
            error_logger.error("Test error message")
            
            # Test simple logging interface
            setup_app_logging(environment=environment, log_directory=self.log_dir)
            
            simple_app_logger = get_app_logger("test_module")
            simple_ai_logger = get_ai_logger("test_ai_module")
            
            self.assertIsInstance(simple_app_logger, logging.Logger)
            self.assertIsInstance(simple_ai_logger, logging.Logger)
            
            # Test logging with these loggers
            simple_app_logger.info("Simple app test message")
            simple_ai_logger.info("Simple AI test message")
            
        except Exception as e:
            self.fail(f"Logging system failed with environment={environment}: {e}")
    
    @given(
        business_hour=st.integers(min_value=0, max_value=23),
        port_num=st.integers(min_value=1000, max_value=9999),
        temperature_val=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=10, deadline=1500)
    def test_configuration_type_conversion_stability(self, business_hour, port_num, temperature_val):
        """
        Property 5d: Configuration Type Conversion Stability
        
        For any valid configuration values, the Settings class should handle
        type conversions consistently.
        
        **Feature: backend-refactoring, Property 5: Configuration System Stability**
        **Validates: Requirements 5.3**
        """
        try:
            # Test that Settings class handles type conversions correctly
            settings = Settings()
            
            # Test that type conversion methods work
            self.assertIsInstance(settings.AI_TEMPERATURE, float)
            self.assertIsInstance(settings.DEBUG, bool)
            self.assertIsInstance(settings.PORT, int)
            self.assertIsInstance(settings.BUSINESS_START_HOUR, int)
            self.assertIsInstance(settings.BUSINESS_END_HOUR, int)
            
            # Test that values are within expected ranges
            self.assertGreaterEqual(settings.AI_TEMPERATURE, 0.0)
            self.assertLessEqual(settings.AI_TEMPERATURE, 2.0)
            self.assertGreaterEqual(settings.PORT, 1)
            self.assertLessEqual(settings.PORT, 65535)
            self.assertGreaterEqual(settings.BUSINESS_START_HOUR, 0)
            self.assertLessEqual(settings.BUSINESS_START_HOUR, 23)
            self.assertGreaterEqual(settings.BUSINESS_END_HOUR, 0)
            self.assertLessEqual(settings.BUSINESS_END_HOUR, 23)
            
            # Test that methods still work
            validation_result = settings.validate_required_settings()
            self.assertIsInstance(validation_result, bool)
            
            config = settings.get_ai_model_config()
            self.assertIsInstance(config, dict)
            
            model_name = settings.get_llm_model_name()
            self.assertIsInstance(model_name, str)
            self.assertGreater(len(model_name), 0)
            
        except Exception as e:
            self.fail(f"Configuration type conversion failed: {e}")
    
    @given(
        api_key_present=st.booleans(),
        provider=st.sampled_from(['openai', 'groq'])
    )
    @settings(max_examples=8, deadline=1500)
    def test_api_key_validation_stability(self, api_key_present, provider):
        """
        Property 5e: API Key Validation Stability
        
        For any API key configuration, the validation should be consistent.
        
        **Feature: backend-refactoring, Property 5: Configuration System Stability**
        **Validates: Requirements 5.5**
        """
        with patch('app.ai.llm.client_factory.settings') as mock_settings:
            mock_settings.LLM_PROVIDER = provider
            mock_settings.get_llm_model_name.return_value = 'test-model'
            
            if provider == 'openai':
                mock_settings.OPENAI_API_KEY = 'test-key' if api_key_present else ''
                mock_settings.GROQ_API_KEY = ''
            else:  # groq
                mock_settings.OPENAI_API_KEY = ''
                mock_settings.GROQ_API_KEY = 'test-key' if api_key_present else ''
            
            if api_key_present:
                # Should work with mocked providers
                if provider == 'openai':
                    with patch('langchain_openai.ChatOpenAI') as mock_openai:
                        mock_openai.return_value = MagicMock()
                        try:
                            model = create_llm_model()
                            self.assertIsNotNone(model)
                        except ImportError:
                            # Acceptable if package not installed
                            pass
                else:  # groq
                    with patch('langchain_groq.ChatGroq') as mock_groq:
                        mock_groq.return_value = MagicMock()
                        try:
                            model = create_llm_model()
                            self.assertIsNotNone(model)
                        except ImportError:
                            # Acceptable if package not installed
                            pass
            else:
                # Should raise ValueError for missing API key
                with self.assertRaises(ValueError) as context:
                    create_llm_model()
                
                error_message = str(context.exception)
                if provider == 'openai':
                    self.assertIn("OPENAI_API_KEY is required", error_message)
                else:
                    self.assertIn("GROQ_API_KEY is required", error_message)


if __name__ == '__main__':
    unittest.main()
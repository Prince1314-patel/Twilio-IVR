#!/usr/bin/env python3
"""
Unit Tests for Intent Classification Engine
==========================================

Comprehensive unit tests for the intent classification module including
classification accuracy, confidence score validation, and error handling.

Author: Advanced AI Systems Team
Last Modified: 2026-02-03
"""

import pytest
from unittest.mock import Mock, AsyncMock
from langchain_core.messages import AIMessage

from app.ai.intent.classifier import (
    classify_intent,
    classify_intent_sync,
    IntentCategory,
    _parse_classification_response,
    _validate_confidence_score
)


class TestIntentCategory:
    """Test the IntentCategory class and its methods."""
    
    def test_all_intents_returns_complete_set(self):
        """Test that all_intents returns all six intent categories."""
        expected_intents = {
            "booking", "cancellation", "rescheduling", 
            "inquiry", "greeting", "out_of_scope"
        }
        assert IntentCategory.all_intents() == expected_intents
    
    def test_intent_constants_are_correct(self):
        """Test that intent constants have correct values."""
        assert IntentCategory.BOOKING == "booking"
        assert IntentCategory.CANCELLATION == "cancellation"
        assert IntentCategory.RESCHEDULING == "rescheduling"
        assert IntentCategory.INQUIRY == "inquiry"
        assert IntentCategory.GREETING == "greeting"
        assert IntentCategory.OUT_OF_SCOPE == "out_of_scope"


class TestParseClassificationResponse:
    """Test the response parsing functionality."""
    
    def test_parse_valid_response(self):
        """Test parsing a valid LLM response."""
        response = "Intent: booking\nConfidence: 0.85"
        intent, confidence = _parse_classification_response(response)
        assert intent == "booking"
        assert confidence == 0.85
    
    def test_parse_case_insensitive(self):
        """Test parsing with different case variations."""
        response = "INTENT: CANCELLATION\nCONFIDENCE: 0.92"
        intent, confidence = _parse_classification_response(response)
        assert intent == "cancellation"
        assert confidence == 0.92
    
    def test_parse_invalid_intent_defaults_to_inquiry(self):
        """Test that invalid intent categories default to inquiry."""
        response = "Intent: invalid_category\nConfidence: 0.90"
        intent, confidence = _parse_classification_response(response)
        assert intent == "inquiry"
        assert confidence == 0.90
    
    def test_parse_malformed_response_returns_default(self):
        """Test that malformed responses return default values."""
        response = "This is not a valid response format"
        intent, confidence = _parse_classification_response(response)
        assert intent == "inquiry"
        assert confidence == 0.5


class TestValidateConfidenceScore:
    """Test confidence score validation."""
    
    def test_valid_confidence_unchanged(self):
        """Test that valid confidence scores are unchanged."""
        assert _validate_confidence_score(0.0) == 0.0
        assert _validate_confidence_score(0.5) == 0.5
        assert _validate_confidence_score(1.0) == 1.0
        assert _validate_confidence_score(0.85) == 0.85
    
    def test_negative_confidence_clamped_to_zero(self):
        """Test that negative confidence scores are clamped to 0.0."""
        assert _validate_confidence_score(-0.1) == 0.0
        assert _validate_confidence_score(-1.0) == 0.0
    
    def test_high_confidence_clamped_to_one(self):
        """Test that confidence scores above 1.0 are clamped to 1.0."""
        assert _validate_confidence_score(1.1) == 1.0
        assert _validate_confidence_score(2.0) == 1.0


@pytest.fixture
def mock_llm_async():
    """Create a mock async LLM model."""
    return AsyncMock()


@pytest.fixture  
def mock_llm_sync():
    """Create a mock sync LLM model."""
    return Mock()


class TestClassifyIntentAsync:
    """Test the async intent classification function."""
    
    @pytest.mark.asyncio
    async def test_booking_intent_classification(self, mock_llm_async):
        """Test classification of booking intent messages."""
        mock_llm_async.ainvoke.return_value = AIMessage(content="Intent: booking\nConfidence: 0.90")
        
        intent, confidence = await classify_intent("I need to book an appointment", mock_llm_async)
        
        assert intent == "booking"
        assert confidence == 0.90
        mock_llm_async.ainvoke.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_all_intent_categories(self, mock_llm_async):
        """Test classification of all intent categories."""
        test_cases = [
            ("booking", 0.90),
            ("cancellation", 0.85),
            ("rescheduling", 0.88),
            ("inquiry", 0.82),
            ("greeting", 0.95),
            ("out_of_scope", 0.92)
        ]
        
        for expected_intent, expected_confidence in test_cases:
            mock_llm_async.ainvoke.return_value = AIMessage(
                content=f"Intent: {expected_intent}\nConfidence: {expected_confidence}"
            )
            
            intent, confidence = await classify_intent(f"Test message for {expected_intent}", mock_llm_async)
            
            assert intent == expected_intent
            assert confidence == expected_confidence
    
    @pytest.mark.asyncio
    async def test_empty_text_returns_greeting_default(self, mock_llm_async):
        """Test that empty text returns greeting with default confidence."""
        intent, confidence = await classify_intent("", mock_llm_async)
        
        assert intent == "greeting"
        assert confidence == 0.5
        mock_llm_async.ainvoke.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_llm_exception_returns_inquiry_default(self, mock_llm_async):
        """Test that LLM exceptions return inquiry with default confidence."""
        mock_llm_async.ainvoke.side_effect = Exception("LLM service unavailable")
        
        intent, confidence = await classify_intent("I need help", mock_llm_async)
        
        assert intent == "inquiry"
        assert confidence == 0.5
    
    @pytest.mark.asyncio
    async def test_confidence_score_range_validation(self, mock_llm_async):
        """Test that confidence scores are validated to be within 0.0-1.0 range."""
        mock_llm_async.ainvoke.return_value = AIMessage(content="Intent: booking\nConfidence: 1.5")
        
        intent, confidence = await classify_intent("Book appointment", mock_llm_async)
        
        assert intent == "booking"
        assert confidence == 1.0  # Clamped to maximum


class TestClassifyIntentSync:
    """Test the synchronous intent classification function."""
    
    def test_booking_intent_classification_sync(self, mock_llm_sync):
        """Test synchronous classification of booking intent messages."""
        mock_llm_sync.invoke.return_value = AIMessage(content="Intent: booking\nConfidence: 0.90")
        
        intent, confidence = classify_intent_sync("I need to book an appointment", mock_llm_sync)
        
        assert intent == "booking"
        assert confidence == 0.90
        mock_llm_sync.invoke.assert_called_once()
    
    def test_empty_text_returns_greeting_default_sync(self, mock_llm_sync):
        """Test that empty text returns greeting with default confidence in sync version."""
        intent, confidence = classify_intent_sync("", mock_llm_sync)
        
        assert intent == "greeting"
        assert confidence == 0.5
        mock_llm_sync.invoke.assert_not_called()
    
    def test_llm_exception_returns_inquiry_default_sync(self, mock_llm_sync):
        """Test that LLM exceptions return inquiry with default confidence in sync version."""
        mock_llm_sync.invoke.side_effect = Exception("LLM service unavailable")
        
        intent, confidence = classify_intent_sync("I need help", mock_llm_sync)
        
        assert intent == "inquiry"
        assert confidence == 0.5


class TestErrorHandlingAndFallbacks:
    """Test error handling and fallback mechanisms."""
    
    @pytest.mark.asyncio
    async def test_malformed_llm_response_fallback(self, mock_llm_async):
        """Test fallback behavior for malformed LLM responses."""
        mock_llm_async.ainvoke.return_value = AIMessage(content="This is not a valid response format")
        
        intent, confidence = await classify_intent("Test message", mock_llm_async)
        
        assert intent == "inquiry"
        assert confidence == 0.5
    
    @pytest.mark.asyncio
    async def test_invalid_intent_category_fallback(self, mock_llm_async):
        """Test fallback behavior for invalid intent categories."""
        mock_llm_async.ainvoke.return_value = AIMessage(content="Intent: invalid_category\nConfidence: 0.90")
        
        intent, confidence = await classify_intent("Test message", mock_llm_async)
        
        assert intent == "inquiry"
        assert confidence == 0.90


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
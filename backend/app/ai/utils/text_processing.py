"""
Text Processing Utilities
========================

This module contains text processing utilities for AI responses,
including cleaning and sanitizing text for text-to-speech engines.

Author: Advanced AI Systems Team
Last Modified: 2025-01-28
"""

import re


def clean_agent_response(response: str) -> str:
    """
    Clean and sanitize agent response to remove markdown, special characters, and formatting.
    
    This function ensures the response is plain text suitable for text-to-speech engines.
    
    Args:
        response (str): Raw agent response that may contain markdown or special formatting.
        
    Returns:
        str: Clean plain text response.
    """
    if not response:
        return response
    
    # Remove markdown formatting
    # Remove bold/italic markers
    response = re.sub(r'\*\*([^*]+)\*\*', r'\1', response)  # **bold**
    response = re.sub(r'\*([^*]+)\*', r'\1', response)  # *italic*
    response = re.sub(r'__([^_]+)__', r'\1', response)  # __bold__
    response = re.sub(r'_([^_]+)_', r'\1', response)  # _italic_
    
    # Remove code blocks
    response = re.sub(r'```[\s\S]*?```', '', response)  # ```code blocks```
    response = re.sub(r'`([^`]+)`', r'\1', response)  # `inline code`
    
    # Remove markdown headers
    response = re.sub(r'^#+\s*', '', response, flags=re.MULTILINE)
    
    # Remove markdown links [text](url) -> text
    response = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', response)
    
    # Remove markdown lists markers
    response = re.sub(r'^\s*[-*+]\s+', '', response, flags=re.MULTILINE)
    response = re.sub(r'^\s*\d+\.\s+', '', response, flags=re.MULTILINE)
    
    # Remove special Unicode characters that might cause issues (zero-width spaces, etc.)
    response = re.sub(r'[\u200B-\u200D\uFEFF]', '', response)  # Zero-width spaces
    
    # Normalize whitespace - replace multiple spaces/newlines with single space
    response = re.sub(r'\s+', ' ', response)
    
    # Strip leading/trailing whitespace
    response = response.strip()
    
    return response
"""
Intent Classification Module
===========================

Intent detection and classification for appointment booking conversations.
Provides LLM-based classification of user messages into predefined intent categories.

Author: Advanced AI Systems Team
Last Modified: 2026-02-03
"""

from .classifier import classify_intent, classify_intent_sync, IntentCategory

__all__ = ["classify_intent", "classify_intent_sync", "IntentCategory"]
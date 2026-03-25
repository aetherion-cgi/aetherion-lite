"""Pytest configuration for Aetherion agents tests"""

import pytest
import os

# Set test environment
os.environ["ANTHROPIC_API_KEY"] = os.getenv("ANTHROPIC_API_KEY", "test-key")


@pytest.fixture
def mock_anthropic_response():
    """Mock Anthropic API response for testing"""
    return {
        "content": [{"text": '{"test": "response"}'}],
        "usage": {"input_tokens": 100, "output_tokens": 50}
    }

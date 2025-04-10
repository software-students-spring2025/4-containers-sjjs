"""Unit tests for voiceai module functionality using pytest and mocks."""

import sys
import os
from unittest.mock import patch, AsyncMock
import asyncio
import pytest
from aiohttp import ClientResponseError
import voiceai # pylint: disable= import-error

# Add the parent directory to sys.path to enable importing voiceai.py
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


@patch("voiceai.gpt_call", new_callable=AsyncMock)
def test_run_prompt_with_mock(mock_gpt_call):
    """Test run_prompt returns correct summary using mocked GPT call."""
    mock_gpt_call.return_value = "This is a test summary."
    text = "This is a transcription"
    result = asyncio.run(voiceai.run_prompt(text))
    assert result == "This is a test summary."
    mock_gpt_call.assert_awaited_once()


@patch("aiohttp.ClientSession.post")
def test_gpt_call_mock_response(mock_post):
    """Test gpt_call returns parsed response from OpenAI when mocked."""
    mock_response = AsyncMock()
    mock_response.json = AsyncMock(
        return_value={"choices": [{"message": {"content": "Mocked GPT summary"}}]}
    )
    mock_post.return_value.__aenter__.return_value = mock_response

    result = asyncio.run(voiceai.gpt_call("Test input", "Prompt: {text}"))
    assert result == "Mocked GPT summary"


@patch("voiceai.gpt_call", new_callable=AsyncMock)
def test_run_prompt_with_empty_transcription(mock_gpt_call):
    """Test run_prompt handles empty transcription gracefully."""
    mock_gpt_call.return_value = "Empty input response."
    text = ""
    result = asyncio.run(voiceai.run_prompt(text))
    assert result == "Empty input response."
    mock_gpt_call.assert_awaited_once()


@patch("aiohttp.ClientSession.post")
def test_gpt_call_missing_keys(mock_post):
    """Test gpt_call raises KeyError when expected JSON keys are missing."""
    mock_response = AsyncMock()
    # Simulate OpenAI response missing the 'choices' key
    mock_response.json = AsyncMock(return_value={"unexpected": "structure"})
    mock_post.return_value.__aenter__.return_value = mock_response

    with pytest.raises(KeyError):
        asyncio.run(voiceai.gpt_call("Test input", "Prompt: {text}"))


@patch("aiohttp.ClientSession.post")
def test_gpt_call_raises_http_error(mock_post):
    """Test gpt_call handles HTTP error gracefully."""
    # Simulate aiohttp post raising a ClientResponseError
    mock_post.side_effect = ClientResponseError(
        request_info=None, history=(), status=500, message="Server error"
    )

    with pytest.raises(ClientResponseError):
        asyncio.run(voiceai.gpt_call("This won't work", "Prompt: {text}"))


@patch("voiceai.gpt_call", new_callable=AsyncMock)
def test_run_prompt_returns_string(mock_gpt_call):
    """ Test gpt_call to see if it returns a string"""
    mock_gpt_call.return_value = "This is a test."
    result = asyncio.run(voiceai.run_prompt("hello"))
    assert isinstance(result, str)

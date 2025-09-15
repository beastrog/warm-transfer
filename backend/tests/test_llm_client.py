import pytest
import os
import sys
from unittest.mock import patch, MagicMock

# Add the parent directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.llm_client import generate_summary, _build_prompt


def test_build_prompt():
    """Test that _build_prompt correctly formats the prompt."""
    text = "This is a test transcript."
    prompt = _build_prompt(text)
    
    assert "You are an assistant" in prompt
    assert "Context:\nThis is a test transcript.\n\nSummary:" in prompt


@patch('services.llm_client.Groq')
def test_generate_summary_with_groq(mock_groq):
    """Test that generate_summary uses Groq when available."""
    # Set up the mock
    mock_groq_instance = MagicMock()
    mock_completion = MagicMock()
    mock_choice = MagicMock()
    mock_message = MagicMock()
    mock_message.content = "This is a mock summary."
    mock_choice.message = mock_message
    mock_completion.choices = [mock_choice]
    mock_groq_instance.chat.completions.create.return_value = mock_completion
    mock_groq.return_value = mock_groq_instance
    
    # Set environment variables
    os.environ["GROQ_API_KEY"] = "test-key"
    
    # Call the function
    result = generate_summary("This is a test transcript.")
    
    # Verify the result
    assert result == "This is a mock summary."
    mock_groq_instance.chat.completions.create.assert_called_once()


@patch('services.llm_client.Groq', None)
@patch('services.llm_client.OpenAI')
def test_generate_summary_with_openai(mock_openai):
    """Test that generate_summary falls back to OpenAI when Groq is not available."""
    # Set up the mock
    mock_openai_instance = MagicMock()
    mock_completion = MagicMock()
    mock_choice = MagicMock()
    mock_message = MagicMock()
    mock_message.content = "This is a mock summary from OpenAI."
    mock_choice.message = mock_message
    mock_completion.choices = [mock_choice]
    mock_openai_instance.chat.completions.create.return_value = mock_completion
    mock_openai.return_value = mock_openai_instance
    
    # Set environment variables
    os.environ["OPENAI_API_KEY"] = "test-key"
    
    # Call the function
    result = generate_summary("This is a test transcript.")
    
    # Verify the result
    assert result == "This is a mock summary from OpenAI."
    mock_openai_instance.chat.completions.create.assert_called_once()


@patch('services.llm_client.Groq', None)
@patch('services.llm_client.OpenAI', None)
def test_generate_summary_fallback():
    """Test that generate_summary falls back to a default summary when no LLM is available."""
    # Call the function
    result = generate_summary("This is a test transcript that should be included in the fallback summary.")
    
    # Verify the result
    assert "LLM unavailable" in result
    assert "This is a test transcript" in result


def test_generate_summary_empty_input():
    """Test that generate_summary handles empty input correctly."""
    # Call the function with empty input
    result = generate_summary("")
    
    # Verify the result
    assert "No transcript available" in result


@patch('services.llm_client._retry_with_backoff')
def test_retry_mechanism(mock_retry):
    """Test that the retry mechanism is used when calling LLMs."""
    # Set up the mock
    mock_retry.return_value = "Retried summary"
    
    # Set environment variables
    os.environ["GROQ_API_KEY"] = "test-key"
    
    # Call the function
    with patch('services.llm_client.Groq') as mock_groq:
        mock_groq_instance = MagicMock()
        mock_groq.return_value = mock_groq_instance
        
        result = generate_summary("This is a test transcript.")
    
    # Verify the result
    assert result == "Retried summary"
    mock_retry.assert_called_once()
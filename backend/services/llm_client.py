import os
import time
import logging
import httpx
from typing import Optional, Dict, Any
from requests.exceptions import HTTPError
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log
)
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Add console handler if not already configured
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

# Import Groq
try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    logger.error("Groq SDK not installed. Please install it with: pip install groq")
    GROQ_AVAILABLE = False
    Groq = None

# Configuration
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
API_TIMEOUT = int(os.getenv("GROQ_TIMEOUT", "30"))
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))

# Log configuration for debugging
logger.info(f"GROQ_API_KEY: {'*' * 8 + GROQ_API_KEY[-4:] if GROQ_API_KEY else 'Not set'}")
logger.info(f"GROQ_MODEL: {GROQ_MODEL}")
logger.info(f"API_TIMEOUT: {API_TIMEOUT}")
logger.info(f"MAX_RETRIES: {MAX_RETRIES}")


def _build_prompt(text: str) -> str:
    return (
        "You are an assistant creating a concise handoff summary between two human agents. "
        "Summarize the following caller context in 2-3 short sentences, focusing on intent, status, and next steps.\n\n"
        f"Context:\n{text}\n\nSummary:"
    )


def _retry_with_backoff(func, max_retries: int = MAX_RETRIES):
    """Retry a function with exponential backoff."""
    retry_count = 0
    last_exception = None
    
    while retry_count < max_retries:
        try:
            return func()
        except Exception as e:
            last_exception = e
            retry_count += 1
            logger.warning(f"Attempt {retry_count} failed: {e}")
            if retry_count < max_retries:
                # Exponential backoff: 1s, 2s, 4s, etc.
                sleep_time = 2 ** (retry_count - 1)
                time.sleep(sleep_time)
    
    # If we get here, all retries failed
    logger.error(f"All {max_retries} attempts failed. Last error: {last_exception}")
    raise last_exception


def _get_groq_client(api_key: str, timeout: int = 30):
    """Initialize and return a Groq client with proper configuration."""
    try:
        # Create a custom HTTP client with timeout
        import httpx
        
        # Configure the HTTP client with timeout
        http_client = httpx.Client(timeout=timeout)
        
        # Initialize Groq client with the custom HTTP client
        return Groq(
            api_key=api_key,
            http_client=http_client
        )
    except Exception as e:
        logger.error(f"Failed to initialize Groq client: {str(e)}", exc_info=True)
        raise

def generate_summary(text: str) -> str:
    """
    Generate a concise summary of the conversation using Groq API.
    
    Args:
        text: The conversation text to summarize
        
    Returns:
        A summary of the conversation or an error message if generation fails
    """
    logger.info("Starting summary generation...")
    
    # Check if Groq is available
    if not GROQ_AVAILABLE:
        error_msg = "Groq SDK is not installed. Please install it with: pip install groq"
        logger.error(error_msg)
        return _fallback_summary(text)
    
    # Check if API key is configured
    if not GROQ_API_KEY:
        error_msg = "GROQ_API_KEY is not set in environment variables"
        logger.error(error_msg)
        return _fallback_summary(text)
    
    if not text or not text.strip():
        logger.warning("Empty text provided for summary generation")
        return "No conversation to summarize."
        
    # Truncate very long text to avoid API issues
    max_text_length = 8000  # Leave some room for the prompt
    if len(text) > max_text_length:
        logger.warning(f"Truncating long input text from {len(text)} to {max_text_length} characters")
        text = text[:max_text_length]
        
    # Check if Groq API key is configured
    groq_api_key = os.getenv("GROQ_API_KEY")
    if not groq_api_key:
        error_msg = "GROQ_API_KEY environment variable is not set"
        logger.error(error_msg)
        return _fallback_summary(text)
        
    # Ensure the API key is properly formatted
    groq_api_key = groq_api_key.strip()
    if not groq_api_key.startswith('gsk_'):
        error_msg = "Invalid GROQ_API_KEY format. It should start with 'gsk_'"
        logger.error(error_msg)
        return _fallback_summary(text)

    # Build the prompt
    def _build_prompt(conversation: str) -> str:
        return f"""
        Please provide a concise handoff summary of the following conversation between a caller and an agent.
        Focus on key points, issues, and next steps. Keep it brief but informative.
        
        Conversation:
        {conversation}
        
        Summary:
        """

    # Define retryable exceptions at module level
    RETRYABLE_EXCEPTIONS = (
        Exception,
        ConnectionError,
        TimeoutError,
        HTTPError,
        httpx.RequestError,
        httpx.HTTPStatusError,
        httpx.TimeoutException,
        httpx.NetworkError
    )
    
    # Call Groq API with retry logic
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(RETRYABLE_EXCEPTIONS),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True
    )
    def _call_groq():
        try:
            logger.info("Initializing Groq client...")
            logger.debug(f"Using API key: {groq_api_key[:5]}...{groq_api_key[-5:] if groq_api_key else ''}")
            
            # Set a reasonable timeout
            timeout = int(os.getenv("GROQ_TIMEOUT", "30"))
            
            try:
                client = _get_groq_client(groq_api_key, timeout)
                prompt = _build_prompt(text)
                logger.info("Sending request to Groq API...")
                logger.debug(f"Using model: llama-3.1-8b-instant")
                logger.debug(f"Prompt length: {len(prompt)} characters")
                
                # Prepare the request data
                request_data = {
                    "model": "llama-3.1-8b-instant",
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are an assistant creating a concise handoff summary between two human agents. Focus on key points, next steps, and any important context."
                        },
                        {
                            "role": "user", 
                            "content": prompt
                        }
                    ],
                    "temperature": 0.2,
                    "max_tokens": min(300, int(os.getenv("MAX_TOKENS", "300"))),
                    "top_p": 1.0,
                    "stream": False
                }
                
                logger.debug(f"Sending request to Groq API with timeout: {timeout}s")
                
                # Make the API call with error handling
                response = client.chat.completions.create(**request_data)
                
                # Log response details without sensitive data
                if hasattr(response, 'usage'):
                    logger.debug(f"API usage - Prompt tokens: {getattr(response.usage, 'prompt_tokens', 'N/A')}, "
                                f"Completion tokens: {getattr(response.usage, 'completion_tokens', 'N/A')}, "
                                f"Total tokens: {getattr(response.usage, 'total_tokens', 'N/A')}")
                
                if not response.choices:
                    error_msg = "No choices in API response"
                    logger.error(error_msg)
                    raise ValueError(error_msg)
                    
                message = response.choices[0].message
                if not message or not message.content:
                    error_msg = "Empty content in API response"
                    logger.error(error_msg)
                    raise ValueError(error_msg)
                    
                return message.content.strip()
                
            except Exception as api_error:
                logger.error(f"Groq API error: {str(api_error)}")
                if hasattr(api_error, 'response') and hasattr(api_error.response, 'text'):
                    logger.error(f"API error response: {api_error.response.text}")
                raise
                
        except Exception as e:
            logger.error(f"Error in _call_groq: {str(e)}", exc_info=True)
            raise

    try:
        logger.info("Starting summary generation")
        start_time = time.time()
        
        # Use the retry mechanism to call the Groq API
        summary = _retry_with_backoff(_call_groq)
        
        duration = time.time() - start_time
        logger.info(f"Successfully generated summary in {duration:.2f}s")
        logger.debug(f"Generated summary: {summary[:100]}...")  # Log first 100 chars
        
        return summary
        
    except Exception as e:
        logger.error(f"Groq summarization failed: {str(e)}", exc_info=True)
        return _fallback_summary(text)


def _fallback_summary(text: str) -> str:
    """
    Return a fallback summary when LLM is not available.
    
    Args:
        text: The original conversation text
        
    Returns:
        A fallback summary with the original text or a default message
    """
    try:
        # Try to get a meaningful fallback from the text
        if not text or not text.strip():
            return "LLM unavailable — No call notes available. Please verify details with the caller."
            
        # If we have some text, provide a more helpful message
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        if lines:
            last_message = lines[-1][:200]  # Take first 200 chars of last message
            return f"LLM unavailable — Call notes (partial): {last_message}... Please verify all details with the caller."
            
        return "LLM unavailable — Please verify all details with the caller."
        
    except Exception as e:
        logger.warning(f"Error in fallback summary: {str(e)}")
        return "LLM unavailable — No summary available. Please verify all details with the caller."

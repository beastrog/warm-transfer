import os
import time
import logging
from typing import Optional, Dict, Any

# Configure logging
logger = logging.getLogger(__name__)

# Prefer Groq if available
try:
    from groq import Groq
except Exception:  # pragma: no cover
    logger.warning("Groq SDK not available")
    Groq = None  # type: ignore

# Fallback to OpenAI
try:
    from openai import OpenAI
except Exception:  # pragma: no cover
    logger.warning("OpenAI SDK not available")
    OpenAI = None  # type: ignore


GROQ_API_KEY = os.getenv("GROQ_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Configure timeouts and retries
API_TIMEOUT = int(os.getenv("API_TIMEOUT", "10"))
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))


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


def generate_summary(text: str) -> str:
    """Generate a summary of the conversation transcript.
    
    Args:
        text: The conversation transcript to summarize
        
    Returns:
        A concise summary of the conversation
        
    Raises:
        Exception: If all LLM providers fail
    """
    if not text or not text.strip():
        logger.warning("Empty transcript provided for summarization")
        return "No transcript available. Please verify details with the caller."

    # Primary: Groq
    if GROQ_API_KEY and Groq is not None:
        try:
            logger.info("Attempting to generate summary using Groq")
            
            def _call_groq():
                client = Groq(api_key=GROQ_API_KEY)
                completion = client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=[
                        {"role": "system", "content": "You create short, crisp handoff summaries."},
                        {"role": "user", "content": _build_prompt(text)},
                    ],
                    temperature=0.3,
                    max_tokens=160,
                    timeout=API_TIMEOUT,
                )
                return completion.choices[0].message.content.strip()  # type: ignore
            
            return _retry_with_backoff(_call_groq)
        except Exception as e:
            logger.error(f"Groq summarization failed: {e}")

    # Secondary: OpenAI
    if OPENAI_API_KEY and OpenAI is not None:
        try:
            logger.info("Falling back to OpenAI for summary generation")
            
            def _call_openai():
                client = OpenAI(api_key=OPENAI_API_KEY)
                completion = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "You create short, crisp handoff summaries."},
                        {"role": "user", "content": _build_prompt(text)},
                    ],
                    temperature=0.3,
                    max_tokens=160,
                    timeout=API_TIMEOUT,
                )
                return completion.choices[0].message.content.strip()  # type: ignore
            
            return _retry_with_backoff(_call_openai)
        except Exception as e:
            logger.error(f"OpenAI summarization failed: {e}")

    # Fallback if all LLM providers fail
    logger.warning("All LLM providers failed, using fallback summary")
    first_120_chars = text[:120].replace('\n', ' ').strip()
    return f"LLM unavailable — Notes: {first_120_chars} — please verify details."


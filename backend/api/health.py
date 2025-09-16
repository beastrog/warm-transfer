from fastapi import APIRouter
from typing import Dict, Any
import os
from services.llm_client import GROQ_AVAILABLE, GROQ_API_KEY

router = APIRouter()

@router.get("/health", response_model=Dict[str, Any])
async def health_check() -> Dict[str, Any]:
    """Health check endpoint that verifies backend and LLM status"""
    llm_status = {
        "available": False,
        "provider": "groq",
        "model": os.getenv("GROQ_MODEL", "llama-3.1-8b-instant"),
        "error": None
    }
    
    # Check if LLM is properly configured
    if not GROQ_AVAILABLE:
        llm_status["error"] = "Groq SDK not installed"
    elif not GROQ_API_KEY:
        llm_status["error"] = "GROQ_API_KEY not configured"
    else:
        llm_status["available"] = True
    
    return {
        "status": "ok",
        "llm": llm_status,
        "version": "1.0.0"
    }

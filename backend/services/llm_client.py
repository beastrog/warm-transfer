import os
from typing import Optional

# Prefer Groq if available
try:
    from groq import Groq
except Exception:  # pragma: no cover
    Groq = None  # type: ignore

# Fallback to OpenAI
try:
    from openai import OpenAI
except Exception:  # pragma: no cover
    OpenAI = None  # type: ignore


GROQ_API_KEY = os.getenv("GROQ_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


def _build_prompt(text: str) -> str:
    return (
        "You are an assistant creating a concise handoff summary between two human agents. "
        "Summarize the following caller context in 2-3 short sentences, focusing on intent, status, and next steps.\n\n"
        f"Context:\n{text}\n\nSummary:"
    )


def generate_summary(text: str) -> str:
    if not text:
        return "Dummy summary: transfer context"

    # Primary: Groq
    if GROQ_API_KEY and Groq is not None:
        try:
            client = Groq(api_key=GROQ_API_KEY)
            completion = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[
                    {"role": "system", "content": "You create short, crisp handoff summaries."},
                    {"role": "user", "content": _build_prompt(text)},
                ],
                temperature=0.3,
                max_tokens=160,
            )
            return completion.choices[0].message.content.strip()  # type: ignore
        except Exception:
            pass

    # Secondary: OpenAI
    if OPENAI_API_KEY and OpenAI is not None:
        try:
            client = OpenAI(api_key=OPENAI_API_KEY)
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You create short, crisp handoff summaries."},
                    {"role": "user", "content": _build_prompt(text)},
                ],
                temperature=0.3,
                max_tokens=120,
            )
            return resp.choices[0].message.content.strip()  # type: ignore
        except Exception:
            pass

    # Fallback
    return "Dummy summary: transfer context"

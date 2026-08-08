"""
Central LLM configuration with multi-provider support (OpenRouter, Groq, OpenAI).
"""
import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()


def get_llm(temperature: float = 0.3, model: str = None) -> ChatOpenAI:
    """Returns an LLM instance wired to OpenRouter, Groq, or OpenAI."""
    load_dotenv(override=True)
    
    # 1. Check for Groq (High-speed free tier: 14,400 requests/day)
    groq_key = os.getenv("GROQ_API_KEY")
    if groq_key:
        return ChatOpenAI(
            openai_api_base="https://api.groq.com/openai/v1",
            openai_api_key=groq_key,
            model_name=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
            temperature=temperature,
            max_retries=3,
        )

    # 2. OpenRouter (Default)
    openrouter_key = os.getenv("OPENROUTER_API_KEY")
    if openrouter_key:
        chosen_model = model or os.getenv("OPENROUTER_MODEL", "openrouter/free")
        return ChatOpenAI(
            openai_api_base="https://openrouter.ai/api/v1",
            openai_api_key=openrouter_key,
            model_name=chosen_model,
            temperature=temperature,
            max_retries=3,
            default_headers={
                "HTTP-Referer": "http://localhost:8501",
                "X-Title": "AlphaVest AI Assistant",
            },
        )

    raise RuntimeError(
        "No API key found. Add OPENROUTER_API_KEY or GROQ_API_KEY to your .env file."
    )


# Active default instance and model identifier
groq_active = os.getenv("GROQ_API_KEY")
MODEL_NAME = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile") if groq_active else os.getenv("OPENROUTER_MODEL", "openrouter/free")
llm = get_llm()

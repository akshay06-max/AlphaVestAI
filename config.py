"""
Central LLM configuration with multi-provider support (Groq, OpenRouter, OpenAI, Streamlit Secrets).
"""
import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()

# Check Streamlit Cloud st.secrets
try:
    import streamlit as st
    if hasattr(st, "secrets"):
        for k in ["GROQ_API_KEY", "GROQ_MODEL", "OPENROUTER_API_KEY", "OPENROUTER_MODEL", "EMAIL_SENDER", "EMAIL_PASSWORD", "SMTP_SERVER", "SMTP_PORT"]:
            if k in st.secrets and not os.getenv(k):
                os.environ[k] = str(st.secrets[k])
except Exception:
    pass


def get_active_model_name() -> str:
    """Return active model name string."""
    if os.getenv("GROQ_API_KEY"):
        return os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    if os.getenv("OPENROUTER_API_KEY"):
        return os.getenv("OPENROUTER_MODEL", "openrouter/free")
    return "llama-3.3-70b-versatile"


def get_llm(temperature: float = 0.3, model: str = None) -> ChatOpenAI:
    """Returns an LLM instance wired to Groq, OpenRouter, or OpenAI."""
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

    # 2. OpenRouter (Alternative)
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

    # 3. Fallback dummy key to prevent import-time crash on Streamlit Cloud boot
    return ChatOpenAI(
        openai_api_base="https://api.groq.com/openai/v1",
        openai_api_key="missing_key_enter_in_sidebar_or_secrets",
        model_name="llama-3.3-70b-versatile",
        temperature=temperature,
        max_retries=1,
    )


# Active default instance and model identifier
MODEL_NAME = get_active_model_name()
llm = get_llm()

"""
LLM provider initialization
"""

from enum import Enum
import os


class LLMProvider(str, Enum):
    OPENAI = "openai"
    GEMINI = "gemini"
    OLLAMA = "ollama"


def get_llm(provider: LLMProvider, model_name: str = None):
    """Initialize LLM based on provider"""
    
    if provider == LLMProvider.OPENAI:
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=model_name or "gpt-4o",
            temperature=0.7,  # Slightly lower for more consistent output
            api_key=os.getenv("OPENAI_API_KEY")
        )
    
    elif provider == LLMProvider.GEMINI:
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(
            model=model_name or "gemini-1.5-pro",
            temperature=0.7,
            google_api_key=os.getenv("GOOGLE_API_KEY")
        )
    
    elif provider == LLMProvider.OLLAMA:
        from langchain_ollama import ChatOllama
        model = model_name or "qwen2.5:latest"
        return ChatOllama(
            model=model,
            temperature=0.7,
            base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        )
    
    else:
        raise ValueError(f"Unsupported provider: {provider}")

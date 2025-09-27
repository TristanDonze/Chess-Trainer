# config.py
"""
Simplified configuration for Chess Trainer AI
"""

import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass
class OpenAIConfig:
    """OpenAI API configuration"""
    api_key: str = os.getenv("OPENAI_API_KEY", "")
    chat_model: str = "gpt-4o"
    max_completion_tokens: int = 4096
    temperature: float = 0.7

@dataclass 
class WeaviateConfig:
    """Weaviate configuration"""
    url: str = os.getenv("WEAVIATE_REST_ENDPOINT", "")
    api_key: str = os.getenv("WEAVIATE_API_KEY", "")
    collection_name: str = "ChessKnowledgeBase"

class Config:
    """Main configuration class"""
    openai = OpenAIConfig()
    weaviate = WeaviateConfig()
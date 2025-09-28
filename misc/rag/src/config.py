# config.py
"""
Configuration for Chess Trainer AI with Voice Support
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

@dataclass
class VoiceConfig:
    """Voice configuration settings"""
    # Audio settings
    sample_rate: int = 24000
    channels: int = 1
    audio_dtype: str = "int16"
    
    # TTS settings
    tts_voice: str = "alloy"  # Options: alloy, echo, fable, onyx, nova, shimmer
    tts_speed: float = 0.9    # Slightly slower for educational content
    
    # STT settings
    stt_model: str = "gpt-4o-transcribe"  # OpenAI STT model
    
    # Recording settings
    default_recording_duration: int = 5  # seconds
    
    # Voice agent settings
    voice_instructions_suffix: str = "Speak naturally and conversationally. Keep responses concise but informative for voice interaction."

class Config:
    """Main configuration class"""
    openai = OpenAIConfig()
    weaviate = WeaviateConfig()
    voice = VoiceConfig()
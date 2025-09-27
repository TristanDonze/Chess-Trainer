# config.py
"""
Configuration management for Chess Trainer AI
"""
import os
from dataclasses import dataclass
from typing import Optional, Dict, Any
from dotenv import load_dotenv

load_dotenv()

@dataclass
class OpenAIConfig:
    """OpenAI API configuration"""
    api_key: str
    base_url: Optional[str] = None
    organization: Optional[str] = None
    
    # Model configurations
    chat_model: str = "gpt-4o"  # Using GPT-4o as primary model
    chat_fallback_model: str = "gpt-4o-mini"  # Fallback model
    realtime_model: str = "gpt-4o-realtime-preview"  # Realtime model
    transcribe_model: str = "whisper-1"  # Transcription model
    tts_model: str = "tts-1"  # TTS model
    
    # Voice settings
    voice: str = "nova"  # Default voice for TTS
    speaking_style: str = "speak as a friendly, knowledgeable chess instructor with enthusiasm but not overwhelming"
    
    # API limits and settings
    max_completion_tokens: int = 4096  # Updated parameter name
    temperature: float = 0.7
    
@dataclass 
class WeaviateConfig:
    """Weaviate vector database configuration"""
    url: str
    api_key: str
    collection_name: str = "ChessKnowledgeBase"
    headers: Optional[Dict[str, str]] = None
    
    def __post_init__(self):
        # Headers will be set later in Config class to avoid circular dependency
        pass

@dataclass
class AgentConfig:
    """Agent behavior configuration"""
    max_conversation_turns: int = 50
    max_context_tokens: int = 28672  # gpt-realtime context limit
    enable_function_calling: bool = True
    enable_rag: bool = True
    rag_results_limit: int = 3
    
    # Chess-specific settings
    chess_personality: str = """You are an expert chess instructor and coach. You're passionate about chess 
    and love helping players improve. You provide clear, actionable advice and can reference specific games, 
    openings, and positions from your knowledge base. Keep responses conversational and encouraging."""
    
    chess_instructions: str = """
    - Always provide practical, actionable chess advice
    - Reference specific positions, games, or theory when helpful
    - Ask clarifying questions about the player's level and goals
    - Use chess notation when appropriate but explain it
    - Be encouraging and patient with students
    - If you're unsure about something, use your knowledge retrieval function
    """

class Config:
    """Main configuration class"""
    
    # Load from environment variables
    openai = OpenAIConfig(
        api_key=os.getenv("OPENAI_API_KEY", ""),
        base_url=os.getenv("OPENAI_BASE_URL"),
        organization=os.getenv("OPENAI_ORGANIZATION")
    )
    
    weaviate = WeaviateConfig(
        url=os.getenv("WEAVIATE_REST_ENDPOINT", ""),
        api_key=os.getenv("WEAVIATE_API_KEY", "")
    )
    
    agent = AgentConfig()
    
    # Set up weaviate headers after both configs are created
    @classmethod 
    def _initialize_headers(cls):
        """Initialize headers that depend on other config values"""
        if cls.weaviate.headers is None:
            cls.weaviate.headers = {"X-OpenAI-Api-Key": cls.openai.api_key}
    
    @classmethod
    def validate(cls) -> bool:
        """Validate that required configuration is present"""
        required_fields = [
            (cls.openai.api_key, "OPENAI_API_KEY"),
            (cls.weaviate.url, "WEAVIATE_REST_ENDPOINT"), 
            (cls.weaviate.api_key, "WEAVIATE_API_KEY")
        ]
        
        missing = []
        for value, name in required_fields:
            if not value:
                missing.append(name)
        
        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")
        
        return True
    
    @classmethod
    def get_model_config(cls, model_type: str = "chat") -> Dict[str, Any]:
        """Get model configuration for different use cases"""
        base_config = {
            "max_completion_tokens": cls.openai.max_completion_tokens,
            "temperature": cls.openai.temperature
        }
        
        if model_type == "chat":
            return {
                **base_config,
                "model": cls.openai.chat_model
            }
        elif model_type == "realtime":
            return {
                "model": cls.openai.realtime_model,
                "voice": cls.openai.voice,
                "modalities": ["audio"],
                "input_audio_format": "pcm16",
                "output_audio_format": "pcm16",
                "turn_detection": {
                    "type": "server_vad",
                    "threshold": 0.5,
                    "prefix_padding_ms": 300,
                    "silence_duration_ms": 500
                }
            }
        elif model_type == "transcribe":
            return {"model": cls.openai.transcribe_model}
        elif model_type == "tts":
            return {
                "model": cls.openai.tts_model,
                "voice": cls.openai.voice,
                "response_format": "mp3"
            }
        else:
            return base_config

# Initialize dependent configurations on import
Config._initialize_headers()

# Optionally validate - allows tests to run without full configuration
try:
    Config.validate()
except ValueError as e:
    # Configuration validation failed - this is expected in test/development environments
    import os
    if os.getenv("CHESS_TRAINER_SKIP_CONFIG_VALIDATION") != "true":
        print(f"Warning: Configuration validation failed: {e}")
        print("Set CHESS_TRAINER_SKIP_CONFIG_VALIDATION=true to skip this warning")
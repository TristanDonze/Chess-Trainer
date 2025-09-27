# openai_client.py
"""
Multi-modal OpenAI Client
Supports chat, realtime speech-to-speech, transcription, and TTS
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional, Union, AsyncGenerator
from dataclasses import dataclass
import json

from openai import OpenAI, AsyncOpenAI
from openai.types.chat import ChatCompletion, ChatCompletionMessage
from openai.types.audio import Transcription
from .config import Config

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class ChatMessage:
    """Standardized chat message"""
    role: str  # "system", "user", "assistant", "tool"
    content: str
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_call_id: Optional[str] = None
    name: Optional[str] = None

@dataclass
class AudioResponse:
    """Response from audio processing"""
    text: Optional[str] = None
    audio_data: Optional[bytes] = None
    duration: Optional[float] = None
    model_used: Optional[str] = None

class OpenAIClient:
    """Enhanced OpenAI client supporting multiple modalities"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the OpenAI client with configuration"""
        self.config = config or Config.openai
        
        # Initialize sync and async clients
        client_kwargs = {
            "api_key": self.config.api_key,
            "base_url": self.config.base_url,
            "organization": self.config.organization
        }
        # Remove None values
        client_kwargs = {k: v for k, v in client_kwargs.items() if v is not None}
        
        self.client = OpenAI(**client_kwargs)
        self.async_client = AsyncOpenAI(**client_kwargs)
        
        logger.info("OpenAI client initialized")
    
    def chat_completion(self, 
                       messages: List[ChatMessage],
                       model: Optional[str] = None,
                       tools: Optional[List[Dict[str, Any]]] = None,
                       **kwargs) -> ChatCompletion:
        """
        Create a chat completion with function calling support
        
        Args:
            messages: List of chat messages
            model: Model to use (defaults to config)
            tools: List of tools/functions available to the model
            **kwargs: Additional parameters for the API call
        """
        try:
            # Convert our ChatMessage objects to OpenAI format
            openai_messages = []
            for msg in messages:
                openai_msg = {
                    "role": msg.role,
                    "content": msg.content
                }
                if msg.tool_calls:
                    openai_msg["tool_calls"] = msg.tool_calls
                if msg.tool_call_id:
                    openai_msg["tool_call_id"] = msg.tool_call_id
                if msg.name:
                    openai_msg["name"] = msg.name
                openai_messages.append(openai_msg)
            
            # Prepare API call parameters
            api_params = {
                "model": model or self.config.chat_model,
                "messages": openai_messages,
                **Config.get_model_config("chat"),
                **kwargs
            }
            
            # Add tools if provided
            if tools:
                api_params["tools"] = tools
                api_params["tool_choice"] = "auto"
            
            response = self.client.chat.completions.create(**api_params)
            logger.info(f"Chat completion successful with model: {api_params['model']}")
            return response
            
        except Exception as e:
            logger.error(f"Chat completion error: {e}")
            # Try fallback model if primary fails
            if model is None and self.config.chat_fallback_model != self.config.chat_model:
                logger.info(f"Trying fallback model: {self.config.chat_fallback_model}")
                api_params["model"] = self.config.chat_fallback_model
                try:
                    return self.client.chat.completions.create(**api_params)
                except Exception as fallback_error:
                    logger.error(f"Fallback model also failed: {fallback_error}")
            raise
    
    async def async_chat_completion(self,
                                   messages: List[ChatMessage],
                                   model: Optional[str] = None,
                                   tools: Optional[List[Dict[str, Any]]] = None,
                                   **kwargs) -> ChatCompletion:
        """Async version of chat completion"""
        try:
            # Convert messages (same as sync version)
            openai_messages = []
            for msg in messages:
                openai_msg = {
                    "role": msg.role,
                    "content": msg.content
                }
                if msg.tool_calls:
                    openai_msg["tool_calls"] = msg.tool_calls
                if msg.tool_call_id:
                    openai_msg["tool_call_id"] = msg.tool_call_id
                if msg.name:
                    openai_msg["name"] = msg.name
                openai_messages.append(openai_msg)
            
            api_params = {
                "model": model or self.config.chat_model,
                "messages": openai_messages,
                **Config.get_model_config("chat"),
                **kwargs
            }
            
            if tools:
                api_params["tools"] = tools
                api_params["tool_choice"] = "auto"
            
            response = await self.async_client.chat.completions.create(**api_params)
            logger.info(f"Async chat completion successful")
            return response
            
        except Exception as e:
            logger.error(f"Async chat completion error: {e}")
            raise
    
    def transcribe_audio(self, 
                        audio_file: Union[str, bytes],
                        model: Optional[str] = None,
                        **kwargs) -> Transcription:
        """
        Transcribe audio using the latest transcription model
        
        Args:
            audio_file: Path to audio file or audio bytes
            model: Transcription model to use
            **kwargs: Additional parameters
        """
        try:
            api_params = {
                "model": model or self.config.transcribe_model,
                **Config.get_model_config("transcribe"),
                **kwargs
            }
            
            if isinstance(audio_file, str):
                with open(audio_file, "rb") as f:
                    api_params["file"] = f
                    response = self.client.audio.transcriptions.create(**api_params)
            else:
                # Assume bytes
                api_params["file"] = audio_file
                response = self.client.audio.transcriptions.create(**api_params)
            
            logger.info("Audio transcription successful")
            return response
            
        except Exception as e:
            logger.error(f"Transcription error: {e}")
            raise
    
    def text_to_speech(self,
                      text: str,
                      voice: Optional[str] = None,
                      model: Optional[str] = None,
                      speaking_style: Optional[str] = None,
                      **kwargs) -> bytes:
        """
        Convert text to speech using OpenAI TTS
        
        Args:
            text: Text to convert to speech
            voice: Voice to use
            model: TTS model to use
            speaking_style: How the model should speak (for future implementation)
            **kwargs: Additional parameters
        """
        try:
            # For now, speaking_style is not directly supported in TTS API
            # It would be handled at the content generation level
            input_text = text
            
            api_params = {
                "model": model or self.config.tts_model,
                "input": input_text,
                "voice": voice or self.config.voice,
                **Config.get_model_config("tts"),
                **kwargs
            }
            
            response = self.client.audio.speech.create(**api_params)
            logger.info("Text-to-speech conversion successful")
            return response.content
            
        except Exception as e:
            logger.error(f"TTS error: {e}")
            raise
    
    async def create_realtime_session(self,
                                    instructions: str,
                                    tools: Optional[List[Dict[str, Any]]] = None,
                                    **kwargs):
        """
        Create a realtime speech-to-speech session
        This would need to be implemented with WebSocket connections
        For now, this is a placeholder showing the interface
        """
        logger.warning("Realtime session creation not fully implemented - would need WebSocket handling")
        
        session_config = {
            "model": self.config.realtime_model,
            "instructions": instructions,
            **Config.get_model_config("realtime"),
            **kwargs
        }
        
        if tools:
            session_config["tools"] = tools
        
        # In a real implementation, this would establish a WebSocket connection
        # and return a session object for handling audio streams
        return session_config
    
    def create_chat_tools(self, functions: List[callable]) -> List[Dict[str, Any]]:
        """
        Convert Python functions to OpenAI tool format
        
        Args:
            functions: List of Python functions to convert
            
        Returns:
            List of tool definitions for OpenAI API
        """
        tools = []
        
        for func in functions:
            # Extract function info
            func_name = func.__name__
            func_doc = func.__doc__ or "No description available"
            
            # Basic tool definition
            tool = {
                "type": "function",
                "function": {
                    "name": func_name,
                    "description": func_doc.strip(),
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                }
            }
            
            # Try to extract parameter info from function signature
            import inspect
            sig = inspect.signature(func)
            
            for param_name, param in sig.parameters.items():
                param_info = {
                    "type": "string"  # Default type
                }
                
                # Try to get type from annotation
                if param.annotation != inspect.Parameter.empty:
                    if param.annotation == int:
                        param_info["type"] = "integer"
                    elif param.annotation == float:
                        param_info["type"] = "number"
                    elif param.annotation == bool:
                        param_info["type"] = "boolean"
                    elif param.annotation == list:
                        param_info["type"] = "array"
                
                tool["function"]["parameters"]["properties"][param_name] = param_info
                
                # Add to required if no default value
                if param.default == inspect.Parameter.empty:
                    tool["function"]["parameters"]["required"].append(param_name)
            
            tools.append(tool)
        
        return tools
    
    def execute_function_call(self, 
                             function_call: Dict[str, Any],
                             available_functions: Dict[str, callable]) -> Any:
        """
        Execute a function call from the model
        
        Args:
            function_call: Function call from the model
            available_functions: Dict mapping function names to callable functions
            
        Returns:
            Result of the function call
        """
        function_name = function_call.get("name")
        function_args = function_call.get("arguments", "{}")
        
        if function_name not in available_functions:
            raise ValueError(f"Function {function_name} not available")
        
        try:
            # Parse arguments
            if isinstance(function_args, str):
                args = json.loads(function_args)
            else:
                args = function_args
            
            # Execute function
            func = available_functions[function_name]
            result = func(**args)
            
            logger.info(f"Function {function_name} executed successfully")
            return result
            
        except Exception as e:
            logger.error(f"Error executing function {function_name}: {e}")
            raise

# Global client instance
_openai_client_instance = None

def get_openai_client() -> OpenAIClient:
    """Get a singleton OpenAI client instance"""
    global _openai_client_instance
    if _openai_client_instance is None:
        _openai_client_instance = OpenAIClient()
    return _openai_client_instance

if __name__ == "__main__":
    # Test the OpenAI client
    print("Testing OpenAI Client...")
    
    client = OpenAIClient()
    
    # Test chat completion
    messages = [
        ChatMessage(role="system", content="You are a helpful chess instructor."),
        ChatMessage(role="user", content="What's the best opening for beginners?")
    ]
    
    try:
        response = client.chat_completion(messages)
        print(f"Chat response: {response.choices[0].message.content}")
    except Exception as e:
        print(f"Chat completion failed: {e}")
    
    # Test function calling capability
    def test_function(query: str) -> str:
        """Test function for function calling"""
        return f"Test result for: {query}"
    
    tools = client.create_chat_tools([test_function])
    print(f"Created tools: {tools}")
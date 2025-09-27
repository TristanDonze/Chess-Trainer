# openai_client.py
"""
Simplified OpenAI Client
"""

import json
from typing import List, Dict, Any
from dataclasses import dataclass
from openai import OpenAI
from .config import Config

@dataclass
class ChatMessage:
    """Chat message"""
    role: str
    content: str
    tool_calls: List[Dict[str, Any]] = None
    tool_call_id: str = None

class OpenAIClient:
    """Simplified OpenAI client"""
    
    def __init__(self):
        self.client = OpenAI(api_key=Config.openai.api_key)
    
    def chat_completion(self, messages: List[ChatMessage], tools: List[Dict[str, Any]] = None, **kwargs):
        """Create a chat completion"""
        # Convert messages to OpenAI format
        openai_messages = []
        for msg in messages:
            openai_msg = {"role": msg.role, "content": msg.content}
            if msg.tool_calls:
                openai_msg["tool_calls"] = msg.tool_calls
            if msg.tool_call_id:
                openai_msg["tool_call_id"] = msg.tool_call_id
            openai_messages.append(openai_msg)
        
        # API parameters
        api_params = {
            "model": Config.openai.chat_model,
            "messages": openai_messages,
            "max_completion_tokens": Config.openai.max_completion_tokens,
            "temperature": Config.openai.temperature,
            **kwargs
        }
        
        if tools:
            api_params["tools"] = tools
            api_params["tool_choice"] = "auto"
        
        return self.client.chat.completions.create(**api_params)
    
    def create_chat_tools(self, functions: List[callable]) -> List[Dict[str, Any]]:
        """Convert Python functions to OpenAI tool format"""
        tools = []
        
        for func in functions:
            tool = {
                "type": "function",
                "function": {
                    "name": func.__name__,
                    "description": func.__doc__ or "No description available",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                }
            }
            
            # Basic parameter extraction from function signature
            import inspect
            sig = inspect.signature(func)
            
            for param_name, param in sig.parameters.items():
                param_info = {"type": "string"}  # Default type
                
                if param.annotation == int:
                    param_info["type"] = "integer"
                elif param.annotation == float:
                    param_info["type"] = "number"
                elif param.annotation == bool:
                    param_info["type"] = "boolean"
                elif param.annotation == list:
                    param_info["type"] = "array"
                
                tool["function"]["parameters"]["properties"][param_name] = param_info
                
                if param.default == inspect.Parameter.empty:
                    tool["function"]["parameters"]["required"].append(param_name)
            
            tools.append(tool)
        
        return tools
    
    def execute_function_call(self, function_call: Dict[str, Any], available_functions: Dict[str, callable]):
        """Execute a function call"""
        function_name = function_call.get("name")
        function_args = function_call.get("arguments", "{}")
        
        if function_name not in available_functions:
            raise ValueError(f"Function {function_name} not available")
        
        if isinstance(function_args, str):
            args = json.loads(function_args)
        else:
            args = function_args
        
        func = available_functions[function_name]
        return func(**args)

# Global client instance
_openai_client_instance = None

def get_openai_client() -> OpenAIClient:
    """Get singleton OpenAI client"""
    global _openai_client_instance
    if _openai_client_instance is None:
        _openai_client_instance = OpenAIClient()
    return _openai_client_instance
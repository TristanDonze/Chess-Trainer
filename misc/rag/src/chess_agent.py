# chess_agent.py
"""
Simplified Chess Trainer Agent with Voice Support - FIXED VERSION
"""

import json
import asyncio
from typing import List, Dict, Any, Optional, AsyncIterator
from dataclasses import dataclass, field
from datetime import datetime

from agents import ModelSettings

from .config import Config
from .chess_rag import retrieve_chess_knowledge, get_weaviate_client
from .openai_client import OpenAIClient, ChatMessage, get_openai_client

# Voice imports
try:
    from agents import Agent, Runner, function_tool
    from agents.voice import (
        VoicePipeline, 
        SingleAgentVoiceWorkflow, 
        VoicePipelineConfig,
        TTSModelSettings,
        AudioInput
    )
    VOICE_AVAILABLE = True
except ImportError:
    VOICE_AVAILABLE = False


@dataclass
class ConversationContext:
    """Simple conversation context"""
    session_id: str = field(default_factory=lambda: f"chess_session_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    message_count: int = 0
    conversation_history: List[Dict[str, Any]] = field(default_factory=list)

class ChessTrainerAgent:
    """Simplified Chess Trainer Agent with Voice Support"""
    
    def __init__(self):
        self.openai_client = get_openai_client()
        self.context = ConversationContext()
        
        # Current chess position (FEN notation) - will be updated by server
        self.current_fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"  # Starting position
        
        # Stockfish analysis - will be updated by server with real analysis
        self.stockfish_input = "No analysis available yet"
        
        # Available functions
        self.available_functions = {
            "retrieve_chess_knowledge": retrieve_chess_knowledge,
            "update_game_state": self.update_game_state,
            "get_stockfish_analysis": self.get_stockfish_analysis
        }
        
        # Voice-related properties
        self.voice_pipeline = None
        self.voice_agent = None
        if VOICE_AVAILABLE:
            self._setup_voice_agent()
    
    def _setup_voice_agent(self):
        """Setup voice agent if available"""
        if not VOICE_AVAILABLE:
            return
            
        # Create function tools for the voice agent
        @function_tool
        def retrieve_chess_knowledge_tool(query: str, limit: int = 2) -> dict:
            """Retrieve relevant chess knowledge from the knowledge base."""
            return retrieve_chess_knowledge(query, limit)
        
        @function_tool
        def update_game_state_tool(fen: str) -> str:
            """Update the current game state"""
            return self.update_game_state(fen)
        
        @function_tool
        def get_stockfish_analysis_tool() -> str:
            """Get Stockfish analysis of current position"""
            return self.get_stockfish_analysis()
        from openai.types.shared import Reasoning

        # Create the voice agent
        self.voice_agent = Agent(
            name="Chess Trainer",
            instructions=f"""You are an expert chess trainer and coach. You help players improve their chess skills by:

1. Analyzing chess positions and suggesting the best moves
2. Explaining chess strategies, tactics, and principles
3. Teaching chess openings, middlegame plans, and endgame techniques
4. Providing feedback on chess positions and games

Current Position: {self.current_fen}
Stockfish Analysis: {self.stockfish_input}

Speak naturally and conversationally. Keep responses concise but informative for voice interaction.
Always consider the current board position when giving advice.""",
            model="gpt-4o",
            model_settings=ModelSettings(
                verbosity="medium",
            ),
            tools=[retrieve_chess_knowledge_tool, update_game_state_tool, get_stockfish_analysis_tool]
        )
        
        # Setup voice pipeline with custom TTS settings
        if self.voice_agent:
            # Configure TTS settings for better chess instruction
            tts_settings = TTSModelSettings(
                voice="alloy",  # Clear, professional voice
                speed=0.9,      # Slightly slower for educational content
            )
            
            voice_config = VoicePipelineConfig(
                tts_settings=tts_settings
            )
            
            self.voice_pipeline = VoicePipeline(
                workflow=SingleAgentVoiceWorkflow(self.voice_agent),
                config=voice_config
            )
    
    def update_game_state(self, fen: str) -> str:
        """Update the current game state"""
        self.current_fen = fen
        # Update voice agent instructions if available
        if self.voice_agent:
            self.voice_agent.instructions = f"""You are an expert chess trainer and coach. You help players improve their chess skills by:

1. Analyzing chess positions and suggesting the best moves
2. Explaining chess strategies, tactics, and principles
3. Teaching chess openings, middlegame plans, and endgame techniques
4. Providing feedback on chess positions and games

Current Position: {fen}
Stockfish Analysis: {self.stockfish_input}

Speak naturally and conversationally. Keep responses concise but informative for voice interaction.
Always consider the current board position when giving advice."""
        
        return f"Game state updated to: {fen}"
    
    def get_stockfish_analysis(self) -> str:
        """Get Stockfish analysis of current position"""
        return self.stockfish_input
    
    async def chat_voice(self, audio_input: Any) -> AsyncIterator[Dict[str, Any]]:
        """Voice chat interface - MINIMAL FIX VERSION"""
        if not VOICE_AVAILABLE or not self.voice_pipeline:
            raise RuntimeError("Voice functionality not available")
        
        self.context.message_count += 1
        
        # Process voice input through pipeline
        result = await self.voice_pipeline.run(audio_input)
        
        # Stream events (both text and audio)
        text_response = ""
        async for event in result.stream():
            # Handle different event types
            if event.type == "voice_stream_event_audio":
                yield {
                    "type": "audio",
                    "data": event.data
                }
            elif event.type == "voice_stream_event_content":
                text_chunk = event.data
                text_response += text_chunk
                yield {
                    "type": "text", 
                    "data": text_chunk
                }
            elif event.type == "voice_stream_event_lifecycle":
                # MINIMAL FIX: Just acknowledge lifecycle events without accessing problematic attributes
                print(f"Lifecycle event occurred: {event.type}")
                yield {
                    "type": "lifecycle",
                    "data": "lifecycle_event"
                }
            elif event.type == "voice_stream_event_error":
                # Handle error events
                error_msg = "Unknown error"
                if hasattr(event, 'error'):
                    error_msg = str(event.error)
                elif hasattr(event, 'message'):
                    error_msg = str(event.message)
                
                yield {
                    "type": "error",
                    "data": error_msg
                }
            else:
                # Handle any other unknown event types
                print(f"Unknown event type: {event.type}")
        
        # Add to conversation history
        self.context.conversation_history.append({
            "timestamp": datetime.now().isoformat(),
            "role": "assistant",
            "content": text_response,
            "type": "voice"
        })
    
    def chat(self, message: str) -> str:
        """Original text chat interface"""
        self.context.message_count += 1
        
        # Add to conversation history
        self.context.conversation_history.append({
            "timestamp": datetime.now().isoformat(),
            "role": "user",
            "content": message
        })
        
        # FIX: Ensure Weaviate connection is available
        try:
            weaviate_client = get_weaviate_client()
            if not weaviate_client.is_connected():
                weaviate_client.connect()
        except Exception as e:
            print(f"Warning: Weaviate connection issue: {e}")
        
        # Build simple prompt with just query + game state + stockfish input
        prompt_content = f"""Query: {message}

Current Game State (FEN): {self.current_fen}

Stockfish Analysis: {self.stockfish_input}

Respond as a chess expert."""
        
        messages = [
            ChatMessage(role="user", content=prompt_content)
        ]
        
        # Add recent conversation history (last 5 messages)
        recent_history = self.context.conversation_history[-10:]
        for msg in recent_history[:-1]:  # Exclude the current message we just added
            messages.insert(-1, ChatMessage(
                role=msg["role"],
                content=msg["content"]
            ))
        
        # Create tools
        tools = self.openai_client.create_chat_tools(list(self.available_functions.values()))
        
        # Get response
        response = self.openai_client.chat_completion(
            messages=messages,
            tools=tools
        )
        
        assistant_message = response.choices[0].message
        
        # Handle function calls if present
        if assistant_message.tool_calls:
            # Execute function calls
            function_results = []
            for tool_call in assistant_message.tool_calls:
                function_name = tool_call.function.name
                result = self.openai_client.execute_function_call(
                    {
                        "name": function_name,
                        "arguments": tool_call.function.arguments
                    },
                    self.available_functions
                )
                function_results.append({
                    "tool_call_id": tool_call.id,
                    "result": str(result)
                })
            
            # Add function call message
            messages.append(ChatMessage(
                role="assistant",
                content=assistant_message.content or "",
                tool_calls=[{
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments
                    }
                } for tc in assistant_message.tool_calls]
            ))
            
            # Add function results
            for result in function_results:
                messages.append(ChatMessage(
                    role="tool",
                    content=result["result"],
                    tool_call_id=result["tool_call_id"]
                ))
            
            # Get final response
            final_response = self.openai_client.chat_completion(
                messages=messages,
                tools=tools
            )
            
            final_content = final_response.choices[0].message.content
        else:
            final_content = assistant_message.content
        
        # Add response to history
        self.context.conversation_history.append({
            "timestamp": datetime.now().isoformat(),
            "role": "assistant",
            "content": final_content,
            "type": "text"
        })
        
        return final_content or "I apologize, but I couldn't generate a response."
    
    def update_fen_position(self, fen: str):
        """Update the current FEN position"""
        self.current_fen = fen
        print(f"Updated FEN position: {fen}")
    
    def update_stockfish_input(self, stockfish_analysis: str):
        """Update the Stockfish analysis"""
        self.stockfish_input = stockfish_analysis
        print(f"Updated Stockfish analysis: {stockfish_analysis}")
    
    def get_conversation_summary(self) -> Dict[str, Any]:
        """Get conversation summary"""
        return {
            "session_id": self.context.session_id,
            "message_count": self.context.message_count,
            "current_position": self.current_fen,
            "conversation_length": len(self.context.conversation_history),
            "voice_available": VOICE_AVAILABLE,
        }
    
    def reset_conversation(self):
        """Reset conversation context"""
        self.context = ConversationContext()
        print("Conversation context reset")
    
    def close(self):
        """Close connections - don't close Weaviate connection here"""
        # Don't close Weaviate connection as it might be needed by other parts
        # The connection will be managed by the module itself
        pass

# Global agent instance
_chess_agent_instance = None

def get_chess_agent() -> ChessTrainerAgent:
    """Get singleton chess agent"""
    global _chess_agent_instance
    if _chess_agent_instance is None:
        _chess_agent_instance = ChessTrainerAgent()
    return _chess_agent_instance
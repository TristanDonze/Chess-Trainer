# chess_agent.py
"""
Simplified Chess Trainer Agent
"""

import json
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime

from .config import Config
from .chess_rag import retrieve_chess_knowledge, close_connection
from .openai_client import OpenAIClient, ChatMessage, get_openai_client

@dataclass
class ConversationContext:
    """Simple conversation context"""
    session_id: str = field(default_factory=lambda: f"chess_session_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    message_count: int = 0
    conversation_history: List[Dict[str, Any]] = field(default_factory=list)

class ChessTrainerAgent:
    """Simplified Chess Trainer Agent"""
    
    def __init__(self):
        self.openai_client = get_openai_client()
        self.context = ConversationContext()
        
        # Current chess position (FEN notation)
        self.current_fen = "r3r1k1/ppp2ppp/8/3P4/3KP1b1/6P1/PP2NP2/2R4R w - - 3 23"
        
        # Stockfish input (placeholder for now)
        self.stockfish_input = "Best move: Rc8+, Evaluation: +2.3"
        
        # Available functions
        self.available_functions = {
            "retrieve_chess_knowledge": retrieve_chess_knowledge,
            "update_game_state": self.update_game_state,
            "get_stockfish_analysis": self.get_stockfish_analysis
        }
    
    def update_game_state(self, fen: str) -> str:
        """Update the current game state"""
        self.current_fen = fen
        return f"Game state updated to: {fen}"
    
    def get_stockfish_analysis(self) -> str:
        """Get Stockfish analysis of current position"""
        return self.stockfish_input
    
    def chat(self, message: str) -> str:
        """Simple chat interface"""
        self.context.message_count += 1
        
        # Add to conversation history
        self.context.conversation_history.append({
            "timestamp": datetime.now().isoformat(),
            "role": "user",
            "content": message
        })
        
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
            "content": final_content
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
        }
    
    def reset_conversation(self):
        """Reset conversation context"""
        self.context = ConversationContext()
        print("Conversation context reset")
    
    def close(self):
        """Close connections"""
        close_connection()

# Global agent instance
_chess_agent_instance = None

def get_chess_agent() -> ChessTrainerAgent:
    """Get singleton chess agent"""
    global _chess_agent_instance
    if _chess_agent_instance is None:
        _chess_agent_instance = ChessTrainerAgent()
    return _chess_agent_instance
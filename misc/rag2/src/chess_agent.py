# chess_agent.py
"""
Chess Trainer Agent Implementation
Uses OpenAI Agents SDK with RAG integration and conversation management
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass, field
import json
from datetime import datetime

# Try to import OpenAI Agents SDK, but handle gracefully if not available
try:
    from agents import Agent, Runner
    from agents.function_tool import function_tool
    from agents.session import Session
    AGENTS_SDK_AVAILABLE = True
    print("✅ OpenAI Agents SDK is available")
except ImportError as e:
    print(f"⚠️ OpenAI Agents SDK not available: {e}")
    print("To install: pip install openai-agents")
    AGENTS_SDK_AVAILABLE = False
    
    # Create dummy decorator for when SDK is not available
    def function_tool(func):
        """Dummy decorator when Agents SDK is not available"""
        func._is_function_tool = True
        return func

from .config import Config
from .chess_rag import retrieve_chess_knowledge, get_chess_rag
from .openai_client import OpenAIClient, ChatMessage, get_openai_client

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class ConversationContext:
    """Context for the current chess conversation"""
    player_level: Optional[str] = None  # beginner, intermediate, advanced
    current_game_position: Optional[str] = None  # FEN notation
    current_topic: Optional[str] = None  # opening, middlegame, endgame, tactics
    session_id: str = field(default_factory=lambda: f"chess_session_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    message_count: int = 0
    conversation_history: List[Dict[str, Any]] = field(default_factory=list)

class ChessTrainerAgent:
    """Main Chess Trainer Agent with multiple interaction modes"""
    
    def __init__(self, use_agents_sdk: bool = True):
        """Initialize the chess trainer agent"""
        self.use_agents_sdk = use_agents_sdk and AGENTS_SDK_AVAILABLE
        self.openai_client = get_openai_client()
        
        # Initialize RAG with fallback
        try:
            self.chess_rag = get_chess_rag()
            self.rag_available = True
            logger.info("✅ RAG system initialized")
        except Exception as e:
            logger.warning(f"⚠️ RAG system initialization failed: {e}")
            self.chess_rag = None
            self.rag_available = False
        
        self.context = ConversationContext()
        
        # Current chess position (you can update this variable as needed)
        self.current_fen = "r3r1k1/ppp2ppp/8/3P4/3KP1b1/6P1/PP2NP2/2R4R w - - 3 23"
        
        # Agent configuration
        self.instructions = self._build_instructions()
        self.available_functions = self._get_available_functions()
        
        if self.use_agents_sdk:
            self._setup_agents_sdk()
        else:
            logger.info("Using custom chat implementation (Agents SDK not available)")
    
    def _build_instructions(self) -> str:
        """Build comprehensive instructions for the chess agent"""
        base_instructions = Config.agent.chess_personality
        
        detailed_instructions = f"""
        {base_instructions}
        
        {Config.agent.chess_instructions}
        
        Additional Guidelines:
        - Always speak in the style: {Config.openai.speaking_style}
        - Track the conversation context (player level, current topic, game position)
        - Use your retrieve_chess_knowledge function when you need specific information
        - Reference retrieved knowledge naturally in your responses
        - Ask follow-up questions to better understand the player's needs
        - Provide practical examples and specific advice
        - Be encouraging and supportive of the player's chess journey
        
        CURRENT CHESS POSITION:
        You are currently analyzing this position: {self.current_fen}
        This is in FEN notation representing the current board state.
        Always consider this position when giving advice about the current game.
        
        Available Tools:
        - retrieve_chess_knowledge: Search your chess knowledge database for specific information
        - update_conversation_context: Update what you know about the current conversation
        - get_position_analysis: Analyze the current chess position
        - suggest_study_plan: Create personalized study plans
        """
        
        return detailed_instructions
    
    def update_fen_position(self, fen: str):
        """Update the current FEN position and rebuild instructions"""
        self.current_fen = fen
        self.context.current_game_position = fen
        self.instructions = self._build_instructions()
        logger.info(f"Updated FEN position: {fen}")
    
    def _get_available_functions(self) -> Dict[str, callable]:
        """Get all available functions for the agent"""
        functions = {
            "update_conversation_context": self._update_context,
            "get_position_analysis": self._analyze_position,
            "suggest_study_plan": self._suggest_study_plan
        }
        
        # Only add RAG function if available
        if self.rag_available:
            functions["retrieve_chess_knowledge"] = retrieve_chess_knowledge
        
        return functions
    
    def _setup_agents_sdk(self):
        """Setup the OpenAI Agents SDK"""
        try:
            if not AGENTS_SDK_AVAILABLE:
                logger.warning("Agents SDK not available, falling back to custom implementation")
                self.use_agents_sdk = False
                return
                
            # Create tools list
            tools = [
                function_tool(self._update_context),
                function_tool(self._analyze_position),
                function_tool(self._suggest_study_plan)
            ]
            
            # Add RAG tool if available
            if self.rag_available:
                tools.append(function_tool(retrieve_chess_knowledge))
            
            # Create the agent with tools
            self.agent = Agent(
                name="ChessTrainer",
                instructions=self.instructions,
                model=Config.openai.chat_model,
                tools=tools
            )
            
            logger.info("✅ Agents SDK agent created successfully")
            
        except Exception as e:
            logger.error(f"Failed to setup Agents SDK: {e}")
            self.use_agents_sdk = False
    
    # Agent tool functions
    @function_tool
    def _update_context(self, 
                       player_level: Optional[str] = None,
                       current_topic: Optional[str] = None,
                       game_position: Optional[str] = None) -> str:
        """
        Update the conversation context with new information about the player or current discussion.
        
        Args:
            player_level: Player's chess level (beginner, intermediate, advanced)
            current_topic: Current topic being discussed (opening, middlegame, endgame, tactics)
            game_position: Current chess position in FEN notation
            
        Returns:
            Confirmation message about the context update
        """
        if player_level:
            self.context.player_level = player_level
        if current_topic:
            self.context.current_topic = current_topic
        if game_position:
            self.context.current_game_position = game_position
            self.current_fen = game_position
        
        logger.info(f"Context updated: level={player_level}, topic={current_topic}")
        return f"Context updated successfully. Player level: {self.context.player_level}, Current topic: {self.context.current_topic}"
    
    @function_tool
    def _analyze_position(self, fen_position: Optional[str] = None) -> str:
        """
        Analyze a chess position and provide insights.
        
        Args:
            fen_position: Chess position in FEN notation (uses current position if not provided)
            
        Returns:
            Analysis of the position with suggestions
        """
        position = fen_position or self.current_fen
        
        # Store the position in context
        self.context.current_game_position = position
        
        # Basic position analysis
        analysis_parts = [
            f"Position Analysis (FEN: {position}):",
            "",
            "Based on the FEN notation, I can analyze:",
            "1. Piece placement and material balance",
            "2. Castling rights and king safety",
            "3. En passant possibilities",
            "4. Move count and game phase",
            "",
            "Key strategic considerations:",
            "- Look for tactical motifs (pins, forks, skewers)",
            "- Evaluate pawn structure strengths/weaknesses", 
            "- Assess piece activity and coordination",
            "- Consider king safety for both sides",
            "",
            "Would you like me to focus on any specific aspect of this position?"
        ]
        
        # Try to get RAG insights if available
        if self.rag_available:
            try:
                analysis_query = f"chess position analysis strategic plans tactical motifs {position}"
                rag_results = retrieve_chess_knowledge(analysis_query, limit=2)
                if rag_results and "No relevant chess knowledge found" not in rag_results:
                    analysis_parts.insert(-2, f"From my knowledge base:\n{rag_results}")
            except Exception as e:
                logger.warning(f"RAG search failed: {e}")
        
        return "\n".join(analysis_parts)
    
    @function_tool
    def _suggest_study_plan(self, 
                          player_level: str,
                          focus_areas: Optional[str] = None,
                          time_available: Optional[str] = None) -> str:
        """
        Suggest a personalized chess study plan.
        
        Args:
            player_level: Player's current level (beginner, intermediate, advanced)
            focus_areas: Areas they want to improve (tactics, openings, endgames, etc.)
            time_available: How much time they can dedicate to study
            
        Returns:
            Personalized study plan recommendations
        """
        # Update context
        self.context.player_level = player_level
        
        plan_parts = [
            f"Personalized Chess Study Plan for {player_level.title()} Player:",
            "",
            "📚 Core Recommendations:",
            "• Daily tactical puzzles (15-20 minutes)",
            "• Opening repertoire development",
            "• Endgame technique study", 
            "• Game analysis and review",
            "",
            f"⏰ Time allocation: {time_available or 'Adjust based on your schedule'}",
            f"🎯 Focus areas: {focus_areas or 'Balanced improvement across all areas'}",
            ""
        ]
        
        # Add level-specific advice
        if player_level.lower() == "beginner":
            plan_parts.extend([
                "Beginner-specific priorities:",
                "1. Learn basic checkmate patterns",
                "2. Master fundamental tactics",
                "3. Understand opening principles",
                "4. Practice basic endgames"
            ])
        elif player_level.lower() == "intermediate":
            plan_parts.extend([
                "Intermediate-specific priorities:",
                "1. Deepen tactical pattern recognition",
                "2. Study positional concepts",
                "3. Build opening repertoire",
                "4. Analyze your games regularly"
            ])
        elif player_level.lower() == "advanced":
            plan_parts.extend([
                "Advanced-specific priorities:",
                "1. Complex tactical combinations",
                "2. Deep positional understanding",
                "3. Opening theory and preparation",
                "4. Psychological aspects of play"
            ])
        
        # Try to get RAG insights if available
        if self.rag_available:
            try:
                query_parts = [f"{player_level} chess study plan"]
                if focus_areas:
                    query_parts.append(focus_areas)
                if time_available:
                    query_parts.append(f"time management {time_available}")
                
                study_query = " ".join(query_parts)
                rag_results = retrieve_chess_knowledge(study_query, limit=2)
                if rag_results and "No relevant chess knowledge found" not in rag_results:
                    plan_parts.extend(["", "Additional insights from my knowledge base:", rag_results])
            except Exception as e:
                logger.warning(f"RAG search failed: {e}")
        
        plan_parts.append("\nWould you like me to elaborate on any specific part of this plan?")
        
        return "\n".join(plan_parts)
    
    def chat(self, message: str, **kwargs) -> str:
        """
        Main chat interface - handles both SDK and custom implementations
        
        Args:
            message: User's message
            **kwargs: Additional parameters
            
        Returns:
            Agent's response
        """
        self.context.message_count += 1
        
        # Add to conversation history
        self.context.conversation_history.append({
            "timestamp": datetime.now().isoformat(),
            "role": "user",
            "content": message
        })
        
        try:
            if self.use_agents_sdk:
                response = self._chat_with_agents_sdk(message, **kwargs)
            else:
                response = self._chat_with_custom_implementation(message, **kwargs)
            
            # Add response to history
            self.context.conversation_history.append({
                "timestamp": datetime.now().isoformat(),
                "role": "assistant",
                "content": response
            })
            
            return response
            
        except Exception as e:
            logger.error(f"Chat error: {e}")
            return f"I apologize, but I encountered an error: {str(e)}. Please try rephrasing your question."
    
    def _chat_with_agents_sdk(self, message: str, **kwargs) -> str:
        """Chat using OpenAI Agents SDK"""
        try:
            # Run the agent
            result = Runner.run_sync(
                agent=self.agent,
                message=message,
                **kwargs
            )
            
            # Extract the response text
            if hasattr(result, 'response') and hasattr(result.response, 'output_text'):
                return result.response.output_text
            elif hasattr(result, 'output_text'):
                return result.output_text
            elif hasattr(result, 'final_output'):
                return result.final_output
            else:
                return str(result)
                
        except Exception as e:
            logger.error(f"Agents SDK error: {e}")
            # Fallback to custom implementation
            return self._chat_with_custom_implementation(message, **kwargs)
    
    def _chat_with_custom_implementation(self, message: str, **kwargs) -> str:
        """Chat using custom implementation with function calling"""
        try:
            # Build conversation messages with FEN integration
            system_message = f"""
            {self.instructions}
            
            IMPORTANT: The current chess position is: {self.current_fen}
            Always consider this position when providing advice about the current game.
            If the user asks about "this position" or "current position", they're referring to this FEN.
            """
            
            messages = [
                ChatMessage(role="system", content=system_message)
            ]
            
            # Add recent conversation history (last 10 messages to manage context)
            recent_history = self.context.conversation_history[-10:]
            for msg in recent_history:
                messages.append(ChatMessage(
                    role=msg["role"],
                    content=msg["content"]
                ))
            
            # Add current message
            messages.append(ChatMessage(role="user", content=message))
            
            # Prepare tools for function calling
            tools = self.openai_client.create_chat_tools(list(self.available_functions.values()))
            
            # Get response from OpenAI
            response = self.openai_client.chat_completion(
                messages=messages,
                tools=tools if tools else None,
                **kwargs
            )
            
            assistant_message = response.choices[0].message
            
            # Handle function calls if present
            if assistant_message.tool_calls:
                # Execute function calls
                function_results = []
                for tool_call in assistant_message.tool_calls:
                    function_name = tool_call.function.name
                    try:
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
                    except Exception as e:
                        function_results.append({
                            "tool_call_id": tool_call.id,
                            "result": f"Error: {str(e)}"
                        })
                
                # Add function call message to conversation
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
                    tools=tools if tools else None
                )
                
                return final_response.choices[0].message.content
            
            return assistant_message.content or "I apologize, but I couldn't generate a response."
            
        except Exception as e:
            logger.error(f"Custom implementation error: {e}")
            raise
    
    async def async_chat(self, message: str, **kwargs) -> str:
        """Async version of chat"""
        # For now, run sync version in executor
        # In a full implementation, this would use async throughout
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.chat, message)
    
    def get_conversation_summary(self) -> Dict[str, Any]:
        """Get a summary of the current conversation"""
        return {
            "session_id": self.context.session_id,
            "message_count": self.context.message_count,
            "player_level": self.context.player_level,
            "current_topic": self.context.current_topic,
            "current_position": self.context.current_game_position or self.current_fen,
            "conversation_length": len(self.context.conversation_history),
            "agents_sdk_available": AGENTS_SDK_AVAILABLE,
            "rag_available": self.rag_available
        }
    
    def reset_conversation(self):
        """Reset the conversation context"""
        self.context = ConversationContext()
        logger.info("Conversation context reset")
    
    def export_conversation(self) -> Dict[str, Any]:
        """Export the full conversation for analysis or storage"""
        return {
            "context": self.context.__dict__,
            "instructions": self.instructions,
            "current_fen": self.current_fen,
            "agents_sdk_available": AGENTS_SDK_AVAILABLE,
            "rag_available": self.rag_available,
            "exported_at": datetime.now().isoformat()
        }

# Global agent instance
_chess_agent_instance = None

def get_chess_agent() -> ChessTrainerAgent:
    """Get a singleton chess agent instance"""
    global _chess_agent_instance
    if _chess_agent_instance is None:
        _chess_agent_instance = ChessTrainerAgent()
    return _chess_agent_instance

if __name__ == "__main__":
    # Test the chess agent
    print("Testing Chess Trainer Agent...")
    
    agent = ChessTrainerAgent()
    
    test_messages = [
        "Hi, I'm a beginner chess player. Can you help me?",
        "What opening should I learn first?",
        "Can you analyze the current position?",
        "What should I look for in this position?",
        "Can you suggest a study plan for me?"
    ]
    
    for message in test_messages:
        print(f"\nUser: {message}")
        try:
            response = agent.chat(message)
            print(f"Agent: {response}")
        except Exception as e:
            print(f"Error: {e}")
    
    # Show conversation summary
    summary = agent.get_conversation_summary()
    print(f"\nConversation Summary: {summary}")
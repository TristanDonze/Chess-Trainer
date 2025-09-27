# main.py
"""
Main interface for the Chess Trainer AI system
Demonstrates how to use the chess agent with both text and voice capabilities
"""

import asyncio
import logging
import sys
from typing import Optional
import argparse

from .config import Config
from .chess_agent import ChessTrainerAgent, get_chess_agent
from .chess_rag import get_chess_rag
from .openai_client import get_openai_client

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ChessTrainerInterface:
    """Main interface for interacting with the Chess Trainer AI"""
    
    def __init__(self, mode: str = "text"):
        """
        Initialize the chess trainer interface
        
        Args:
            mode: Interface mode - "text", "voice", or "mixed"
        """
        self.mode = mode
        self.agent = get_chess_agent()
        self.running = False
        
        print("🏁 Chess Trainer AI initialized!")
        print(f"Mode: {mode}")
        print(f"Using model: {Config.openai.chat_model}")
        print(f"RAG enabled: {Config.agent.enable_rag}")
    
    def start_text_session(self):
        """Start an interactive text-based chat session"""
        print("\n♟️ Welcome to Chess Trainer AI!")
        print("Type 'quit', 'exit', or 'bye' to end the session")
        print("Type 'help' for available commands")
        print("Type 'summary' to see conversation summary")
        print("-" * 50)
        
        self.running = True
        
        while self.running:
            try:
                user_input = input("\nYou: ").strip()
                
                if not user_input:
                    continue
                
                # Handle special commands
                if user_input.lower() in ['quit', 'exit', 'bye']:
                    self._handle_quit()
                    break
                elif user_input.lower() == 'help':
                    self._show_help()
                    continue
                elif user_input.lower() == 'summary':
                    self._show_summary()
                    continue
                elif user_input.lower() == 'reset':
                    self._reset_conversation()
                    continue
                elif user_input.lower() == 'export':
                    self._export_conversation()
                    continue
                
                # Get response from agent
                print("\nChess Trainer: ", end="", flush=True)
                response = self.agent.chat(user_input)
                print(response)
                
            except KeyboardInterrupt:
                print("\n\nGoodbye! Keep practicing your chess! ♟️")
                break
            except Exception as e:
                logger.error(f"Error in chat session: {e}")
                print(f"\nSorry, I encountered an error: {e}")
                print("Please try again or type 'quit' to exit.")
    
    async def start_voice_session(self):
        """Start a voice-based session (placeholder for future implementation)"""
        print("\n🎤 Voice mode is not fully implemented yet.")
        print("This would use the OpenAI Realtime API for speech-to-speech interaction.")
        print("Falling back to text mode...")
        self.start_text_session()
    
    def start_mixed_session(self):
        """Start a mixed text/voice session"""
        print("\n🗣️ Mixed mode: You can type or use voice commands")
        print("Voice features coming soon! Using text for now...")
        self.start_text_session()
    
    def _handle_quit(self):
        """Handle quit command"""
        summary = self.agent.get_conversation_summary()
        print(f"\n📊 Session Summary:")
        print(f"   Messages exchanged: {summary['message_count']}")
        print(f"   Session ID: {summary['session_id']}")
        if summary['player_level']:
            print(f"   Your level: {summary['player_level']}")
        if summary['current_topic']:
            print(f"   Last topic: {summary['current_topic']}")
        
        print("\nThanks for training with Chess Trainer AI! ♟️")
        print("Keep practicing and improving your game!")
        self.running = False
    
    def _show_help(self):
        """Show help information"""
        print("\n📖 Chess Trainer AI Commands:")
        print("  help     - Show this help message")
        print("  summary  - Show conversation summary")
        print("  reset    - Reset the conversation")
        print("  export   - Export conversation history")
        print("  quit     - End the session")
        print("\n💡 Chess Trainer AI can help with:")
        print("  • Opening principles and specific openings")
        print("  • Middlegame strategy and tactics")
        print("  • Endgame techniques")
        print("  • Position analysis (provide FEN notation)")
        print("  • Study plans and improvement advice")
        print("  • General chess questions")
        print("\nJust ask naturally! For example:")
        print("  'I'm a beginner, what opening should I learn?'")
        print("  'Analyze this position: rnbqkb1r/pppp1ppp/5n2/4p3/2B1P3/8/PPPP1PPP/RNBQK1NR'")
        print("  'Give me a study plan for improving my tactics'")
    
    def _show_summary(self):
        """Show conversation summary"""
        summary = self.agent.get_conversation_summary()
        print(f"\n📊 Conversation Summary:")
        print(f"   Session ID: {summary['session_id']}")
        print(f"   Messages: {summary['message_count']}")
        print(f"   Player Level: {summary['player_level'] or 'Not specified'}")
        print(f"   Current Topic: {summary['current_topic'] or 'General'}")
        print(f"   Current Position: {summary['current_position'] or 'None'}")
        print(f"   History Length: {summary['conversation_length']}")
    
    def _reset_conversation(self):
        """Reset the conversation"""
        self.agent.reset_conversation()
        print("\n🔄 Conversation reset! We're starting fresh.")
    
    def _export_conversation(self):
        """Export conversation history"""
        try:
            export_data = self.agent.export_conversation()
            filename = f"chess_conversation_{export_data['context']['session_id']}.json"
            
            import json
            with open(filename, 'w') as f:
                json.dump(export_data, f, indent=2)
            
            print(f"💾 Conversation exported to: {filename}")
        except Exception as e:
            print(f"❌ Export failed: {e}")

def demo_agent_capabilities():
    """Demonstrate the agent's capabilities"""
    print("\n🎯 Demonstrating Chess Trainer AI Capabilities")
    print("=" * 50)
    
    agent = get_chess_agent()
    
    demo_conversations = [
        {
            "title": "🔰 Beginner Guidance",
            "messages": [
                "I'm completely new to chess. Where should I start?",
                "What's the most important opening principle?"
            ]
        },
        {
            "title": "📚 Opening Advice",
            "messages": [
                "I want to learn the Sicilian Defense. Can you help?",
            ]
        },
        {
            "title": "🔍 Position Analysis",
            "messages": [
                "Can you analyze this position: rnbqkb1r/pppp1ppp/5n2/4p3/2B1P3/8/PPPP1PPP/RNBQK1NR w KQkq - 2 3"
            ]
        },
        {
            "title": "📈 Study Plan",
            "messages": [
                "I'm an intermediate player. Can you create a study plan for me?"
            ]
        }
    ]
    
    for demo in demo_conversations:
        print(f"\n{demo['title']}")
        print("-" * 30)
        
        for message in demo['messages']:
            print(f"\n👤 User: {message}")
            try:
                response = agent.chat(message)
                print(f"🤖 Chess Trainer: {response[:300]}...")
                if len(response) > 300:
                    print("   [Response truncated for demo]")
            except Exception as e:
                print(f"❌ Error: {e}")
        
        print("\n" + "·" * 50)
    
    # Show final summary
    summary = agent.get_conversation_summary()
    print(f"\n📊 Demo Summary: {summary['message_count']} messages exchanged")

async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Chess Trainer AI")
    parser.add_argument(
        "--mode", 
        choices=["text", "voice", "mixed"],
        default="text",
        help="Interface mode (default: text)"
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Run capability demonstration"
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Run test suite"
    )
    
    args = parser.parse_args()
    
    try:
        # Validate configuration
        Config.validate()
        print("✅ Configuration validated")
        
        if args.test:
            # Run tests
            from test_scripts import main as run_tests
            print("🧪 Running test suite...")
            success = run_tests()
            return 0 if success else 1
        
        if args.demo:
            # Run demo
            demo_agent_capabilities()
            return 0
        
        # Start interactive session
        interface = ChessTrainerInterface(mode=args.mode)
        
        if args.mode == "text":
            interface.start_text_session()
        elif args.mode == "voice":
            await interface.start_voice_session()
        elif args.mode == "mixed":
            interface.start_mixed_session()
        
        return 0
        
    except KeyboardInterrupt:
        print("\n\nSession interrupted. Goodbye! ♟️")
        return 0
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        print(f"\n❌ Fatal error: {e}")
        print("\nPlease check your configuration and try again.")
        return 1

if __name__ == "__main__":
    # Run the main function
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
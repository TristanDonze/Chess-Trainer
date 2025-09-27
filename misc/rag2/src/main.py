# main.py
"""
Simplified main interface for Chess Trainer AI
"""

import sys
from .chess_agent import get_chess_agent
from .config import Config

class ChessTrainerInterface:
    """Simple chess trainer interface"""
    
    def __init__(self):
        self.agent = get_chess_agent()
        print("Chess Trainer AI initialized!")
        print(f"Using model: {Config.openai.chat_model}")
    
    def start_text_session(self):
        """Start interactive text session"""
        print("\nWelcome to Chess Trainer AI!")
        print("Type 'quit' to exit, 'help' for commands")
        print("-" * 50)
        
        while True:
            try:
                user_input = input("\nYou: ").strip()
                
                if not user_input:
                    continue
                
                if user_input.lower() in ['quit', 'exit']:
                    print("Thanks for using Chess Trainer AI!")
                    break
                elif user_input.lower() == 'help':
                    self._show_help()
                    continue
                elif user_input.lower() == 'summary':
                    self._show_summary()
                    continue
                elif user_input.lower() == 'reset':
                    self.agent.reset_conversation()
                    continue
                
                # Get response
                print("\nChess Trainer: ", end="", flush=True)
                response = self.agent.chat(user_input)
                print(response)
                
            except KeyboardInterrupt:
                print("\nGoodbye!")
                break
            except Exception as e:
                print(f"\nError: {e}")
    
    def _show_help(self):
        """Show help"""
        print("\nCommands:")
        print("  help    - Show this help")
        print("  summary - Show conversation summary")
        print("  reset   - Reset conversation")
        print("  quit    - Exit")
        print("\nJust ask chess questions naturally!")
    
    def _show_summary(self):
        """Show summary"""
        summary = self.agent.get_conversation_summary()
        print(f"\nSummary:")
        print(f"  Messages: {summary['message_count']}")
        print(f"  Position: {summary['current_position']}")

def main():
    """Main entry point"""
    try:
        interface = ChessTrainerInterface()
        interface.start_text_session()
        return 0
    except Exception as e:
        print(f"Error: {e}")
        return 1
    finally:
        # Cleanup
        agent = get_chess_agent()
        agent.close()

if __name__ == "__main__":
    sys.exit(main())
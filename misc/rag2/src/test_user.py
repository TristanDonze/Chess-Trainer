#!/usr/bin/env python3
"""
Simplified test script for Chess Trainer AI
"""

import sys
import os
from datetime import datetime

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.chess_agent import ChessTrainerAgent
from src.config import Config

def test_chess_conversation():
    """Test chess conversation with simplified system"""
    
    print("=" * 60)
    print(" Chess Trainer AI - Simplified Test")
    print("=" * 60)
    print(f"Test started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Initialize agent
    print("\nInitializing Chess Trainer Agent...")
    agent = ChessTrainerAgent()
    print("Agent initialized successfully")
    
    # Display current state
    print(f"\nCurrent FEN: {agent.current_fen}")
    print(f"Stockfish Analysis: {agent.stockfish_input}")
    
    # Test questions
    test_questions = [
        "What's the best move in this position? White to play.",
        "Analyze the tactical opportunities for both sides.",
        "Should I be worried about my king safety?",
        "What's the strategic plan for White here?"
    ]
    
    print("\nStarting conversation test...")
    print("-" * 60)
    
    for i, question in enumerate(test_questions, 1):
        print(f"\nQuestion {i}: {question}")
        print("\nResponse:")
        print("-" * 30)
        
        try:
            response = agent.chat(question)
            print(response)
            print("-" * 30)
            
        except Exception as e:
            print(f"Error: {e}")
            return False
    
    # Final summary
    summary = agent.get_conversation_summary()
    print(f"\nTest Summary:")
    print(f"Total messages: {summary['message_count']}")
    print(f"Session ID: {summary['session_id']}")
    
    # Cleanup
    agent.close()
    
    return True

def test_rag_system():
    """Test RAG system directly"""
    print("\nTesting RAG system...")
    
    from src.chess_rag import retrieve_chess_knowledge
    
    test_queries = [
        "Sicilian Defense opening principles",
        "endgame king and pawn techniques",
        "middlegame pawn structure strategy"
    ]
    
    for query in test_queries:
        print(f"\nQuery: {query}")
        try:
            results = retrieve_chess_knowledge(query, limit=1)
            if results:
                print(f"Found {len(results)} result(s)")
                if results[0]:
                    title = results[0].get('title', 'No title')
                    content = results[0].get('content', 'No content')[:100]
                    print(f"Title: {title}")
                    print(f"Content: {content}...")
            else:
                print("No results found")
        except Exception as e:
            print(f"Error: {e}")
            return False
    
    return True

def main():
    """Main test function"""
    print("Starting Chess Trainer AI Test Suite")
    
    # Test RAG first
    print("\n" + "=" * 60)
    print("Testing RAG System")
    print("=" * 60)
    
    rag_success = test_rag_system()
    print(f"\nRAG Test: {'PASSED' if rag_success else 'FAILED'}")
    
    # Test full conversation
    print("\n" + "=" * 60)
    print("Testing Full Conversation")
    print("=" * 60)
    
    conversation_success = test_chess_conversation()
    print(f"\nConversation Test: {'PASSED' if conversation_success else 'FAILED'}")
    
    # Final results
    print("\n" + "=" * 60)
    print("Test Results")
    print("=" * 60)
    
    if rag_success and conversation_success:
        print("All tests PASSED! Chess Trainer AI is working correctly.")
        return 0
    else:
        print("Some tests FAILED. Please check the errors above.")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
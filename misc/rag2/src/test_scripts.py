# test_scripts.py
"""
Comprehensive test scripts for the Chess Trainer AI system
Tests RAG, OpenAI client, and agent functionality independently and together
"""

import asyncio
import time
import sys
import logging
from typing import Dict, Any, List
import traceback

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def print_test_header(test_name: str):
    """Print a formatted test header"""
    print("\n" + "="*60)
    print(f"TESTING: {test_name}")
    print("="*60)

def print_test_result(test_name: str, success: bool, details: str = ""):
    """Print test results"""
    status = "✅ PASSED" if success else "❌ FAILED"
    print(f"\n{status}: {test_name}")
    if details:
        print(f"Details: {details}")

def test_rag_only():
    """Test RAG functionality without OpenAI"""
    print_test_header("RAG System (Without OpenAI)")
    
    try:
        from .chess_rag import ChessRAG, retrieve_chess_knowledge
        
        # Test 1: RAG Connection
        print("\n1. Testing RAG Connection...")
        try:
            with ChessRAG() as rag:
                stats = rag.get_collection_stats()
                print(f"Collection stats: {stats}")
                print_test_result("RAG Connection", True, f"Connected to {stats.get('collection_name', 'Unknown')}")
        except Exception as e:
            print_test_result("RAG Connection", False, str(e))
            return False
        
        # Test 2: Basic Retrieval
        print("\n2. Testing Basic Knowledge Retrieval...")
        test_queries = [
            "Sicilian Defense opening principles",
            "endgame king and pawn versus king",
            "middlegame pawn structure strategies",
            "tactical motifs pins forks skewers"
        ]
        
        for query in test_queries:
            try:
                result = retrieve_chess_knowledge(query, limit=2)
                # Fix the success criteria - should check for actual content, not just length
                success = (len(result) > 50 and  # Should have substantial content
                          "Error" not in result and 
                          "No relevant chess knowledge found" not in result)
                print_test_result(f"Query: '{query[:30]}...'", success, 
                                f"Found {'relevant' if success else 'no'} results")
            except Exception as e:
                print_test_result(f"Query: '{query[:30]}...'", False, str(e))
        
        # Test 3: RAG Formatting
        print("\n3. Testing Result Formatting...")
        try:
            with ChessRAG() as rag:
                results = rag.retrieve("chess tactics", limit=2)
                formatted = rag.format_results_for_llm(results)
                # Adjusted success criteria to handle empty results
                success = (len(formatted) > 50 and 
                          "No relevant chess knowledge found" not in formatted)
                print_test_result("Result Formatting", success, 
                                f"Formatted length: {len(formatted)} chars")
        except Exception as e:
            print_test_result("Result Formatting", False, str(e))
        
        return True
        
    except Exception as e:
        print_test_result("RAG System", False, str(e))
        return False

def test_openai_client():
    """Test OpenAI client functionality"""
    print_test_header("OpenAI Client")
    
    try:
        from .openai_client import OpenAIClient, ChatMessage
        from .config import Config
        
        # Test 1: Client Initialization
        print("\n1. Testing Client Initialization...")
        try:
            client = OpenAIClient()
            print_test_result("Client Init", True, f"Using model: {Config.openai.chat_model}")
        except Exception as e:
            print_test_result("Client Init", False, str(e))
            return False
        
        # Test 2: Basic Chat Completion
        print("\n2. Testing Basic Chat Completion...")
        try:
            messages = [
                ChatMessage(role="system", content="You are a helpful chess instructor."),
                ChatMessage(role="user", content="What is the most important chess opening principle?")
            ]
            
            response = client.chat_completion(messages)
            success = response and response.choices and len(response.choices[0].message.content) > 0
            print_test_result("Basic Chat", success, 
                            f"Response length: {len(response.choices[0].message.content) if success else 0} chars")
        except Exception as e:
            print_test_result("Basic Chat", False, str(e))
        
        # Test 3: Function Calling Setup
        print("\n3. Testing Function Call Setup...")
        try:
            def test_function(query: str) -> str:
                """Test function for chess knowledge"""
                return f"Test response for: {query}"
            
            tools = client.create_chat_tools([test_function])
            success = len(tools) == 1 and tools[0]["type"] == "function"
            print_test_result("Function Tools", success, 
                            f"Created {len(tools)} tool(s)")
        except Exception as e:
            print_test_result("Function Tools", False, str(e))
        
        # Test 4: Function Execution
        print("\n4. Testing Function Execution...")
        try:
            function_call = {
                "name": "test_function",
                "arguments": '{"query": "test query"}'
            }
            available_functions = {"test_function": test_function}
            
            result = client.execute_function_call(function_call, available_functions)
            success = "test query" in result
            print_test_result("Function Execution", success, f"Result: {result}")
        except Exception as e:
            print_test_result("Function Execution", False, str(e))
        
        return True
        
    except Exception as e:
        print_test_result("OpenAI Client", False, str(e))
        return False

def test_agent_without_openai():
    """Test agent functionality with mocked OpenAI responses"""
    print_test_header("Chess Agent (Mocked OpenAI)")
    
    try:
        # Mock the OpenAI responses for testing
        class MockOpenAIClient:
            def chat_completion(self, messages, tools=None, **kwargs):
                class MockResponse:
                    def __init__(self):
                        self.choices = [MockChoice()]
                
                class MockChoice:
                    def __init__(self):
                        self.message = MockMessage()
                
                class MockMessage:
                    def __init__(self):
                        self.content = "This is a mocked chess response about opening principles."
                        self.tool_calls = None
                
                return MockResponse()
            
            def create_chat_tools(self, functions):
                return [{"type": "function", "function": {"name": f.__name__}} for f in functions]
            
            def execute_function_call(self, call, functions):
                return "Mocked function result"
        
        # Test agent initialization with mocked client
        print("\n1. Testing Agent Initialization...")
        try:
            from .chess_agent import ChessTrainerAgent
            
            agent = ChessTrainerAgent(use_agents_sdk=False)  # Force custom implementation
            agent.openai_client = MockOpenAIClient()  # Replace with mock
            
            print_test_result("Agent Init", True, "Agent initialized with mocked client")
        except NameError as e:
            if "function_tool" in str(e):
                print_test_result("Agent Init", False, f"function_tool not defined: {e}")
            else:
                print_test_result("Agent Init", False, str(e))
            return False
        except Exception as e:
            print_test_result("Agent Init", False, str(e))
            return False
        
        # Test 2: Basic Chat
        print("\n2. Testing Basic Chat...")
        try:
            response = agent.chat("What's the best opening for beginners?")
            success = len(response) > 0
            print_test_result("Basic Chat", success, f"Response: {response[:100]}...")
        except Exception as e:
            print_test_result("Basic Chat", False, str(e))
        
        # Test 3: Context Management
        print("\n3. Testing Context Management...")
        try:
            agent.chat("I'm a beginner player")
            agent.chat("I want to learn about tactics")
            
            summary = agent.get_conversation_summary()
            success = summary["message_count"] >= 2
            print_test_result("Context Management", success, f"Messages: {summary['message_count']}")
        except Exception as e:
            print_test_result("Context Management", False, str(e))
        
        return True
        
    except Exception as e:
        print_test_result("Agent (Mocked)", False, str(e))
        return False

def test_full_integration():
    """Test full system integration with real OpenAI"""
    print_test_header("Full System Integration (With OpenAI)")
    
    try:
        from .chess_agent import ChessTrainerAgent
        
        # Test 1: Full Agent Creation
        print("\n1. Testing Full Agent Creation...")
        try:
            agent = ChessTrainerAgent()
            print_test_result("Full Agent Init", True, "Agent created with all components")
        except Exception as e:
            print_test_result("Full Agent Init", False, str(e))
            return False
        
        # Test 2: RAG Integration
        print("\n2. Testing RAG Integration...")
        try:
            response = agent.chat("Can you search your knowledge base for Sicilian Defense advice?")
            success = len(response) > 0 and "error" not in response.lower()
            print_test_result("RAG Integration", success, f"Response length: {len(response)}")
            if success:
                print(f"Response preview: {response[:200]}...")
        except Exception as e:
            print_test_result("RAG Integration", False, str(e))
        
        # Test 3: Function Calling
        print("\n3. Testing Function Calling...")
        try:
            response = agent.chat("I'm an intermediate player, can you suggest a study plan?")
            success = len(response) > 0
            print_test_result("Function Calling", success, f"Response length: {len(response)}")
        except Exception as e:
            print_test_result("Function Calling", False, str(e))
        
        # Test 4: Conversation Flow
        print("\n4. Testing Conversation Flow...")
        try:
            responses = []
            test_conversation = [
                "Hi, I'm new to chess",
                "What opening should I learn?",
                "Can you analyze this position: rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR",
                "What should I study next?"
            ]
            
            for msg in test_conversation:
                response = agent.chat(msg)
                responses.append(len(response))
            
            success = all(r > 0 for r in responses)
            print_test_result("Conversation Flow", success, 
                            f"Responses: {len(responses)}, avg length: {sum(responses)/len(responses):.0f}")
            
            # Show final summary
            summary = agent.get_conversation_summary()
            print(f"Final summary: {summary}")
            
        except Exception as e:
            print_test_result("Conversation Flow", False, str(e))
        
        return True
        
    except Exception as e:
        print_test_result("Full Integration", False, str(e))
        return False

def test_audio_capabilities():
    """Test audio capabilities (TTS/STT) if available"""
    print_test_header("Audio Capabilities (TTS/STT)")
    
    try:
        from .openai_client import OpenAIClient
        
        client = OpenAIClient()
        
        # Test 1: Text-to-Speech
        print("\n1. Testing Text-to-Speech...")
        try:
            text = "Welcome to chess training! Let's improve your game together."
            audio_data = client.text_to_speech(
                text=text,
                speaking_style="speak as an enthusiastic chess coach"
            )
            success = len(audio_data) > 1000  # Audio should be substantial
            print_test_result("TTS", success, f"Generated {len(audio_data)} bytes of audio")
        except Exception as e:
            print_test_result("TTS", False, str(e))
        
        # Test 2: Realtime Session Config
        print("\n2. Testing Realtime Session Configuration...")
        try:
            session_config = asyncio.run(client.create_realtime_session(
                instructions="You are a chess instructor",
                tools=[]
            ))
            success = "model" in session_config
            print_test_result("Realtime Config", success, f"Model: {session_config.get('model', 'Unknown')}")
        except Exception as e:
            print_test_result("Realtime Config", False, str(e))
        
        return True
        
    except Exception as e:
        print_test_result("Audio Capabilities", False, str(e))
        return False

async def run_async_tests():
    """Run async-specific tests"""
    print_test_header("Async Functionality")
    
    try:
        from .chess_agent import ChessTrainerAgent
        
        agent = ChessTrainerAgent()
        
        # Test async chat
        print("\n1. Testing Async Chat...")
        try:
            response = await agent.async_chat("What's a good tactical exercise for beginners?")
            success = len(response) > 0
            print_test_result("Async Chat", success, f"Response length: {len(response)}")
        except Exception as e:
            print_test_result("Async Chat", False, str(e))
        
        return True
        
    except Exception as e:
        print_test_result("Async Tests", False, str(e))
        return False

def main():
    """Run all tests"""
    print("🏁 Starting Chess Trainer AI Test Suite")
    print(f"Python version: {sys.version}")
    
    test_results = {}
    
    try:
        # Test 1: RAG only (no OpenAI needed)
        try:
            test_results["RAG"] = test_rag_only()
        except Exception as e:
            print(f"RAG test failed with exception: {e}")
            test_results["RAG"] = False
        
        # Test 2: OpenAI client
        try:
            test_results["OpenAI"] = test_openai_client()
        except Exception as e:
            print(f"OpenAI test failed with exception: {e}")
            test_results["OpenAI"] = False
        
        # Test 3: Agent without OpenAI (mocked)
        try:
            test_results["Agent_Mocked"] = test_agent_without_openai()
        except Exception as e:
            print(f"Mocked agent test failed with exception: {e}")
            test_results["Agent_Mocked"] = False
        
        # Test 4: Full integration (requires OpenAI API)
        if test_results.get("RAG", False) and test_results.get("OpenAI", False):
            try:
                test_results["Integration"] = test_full_integration()
            except Exception as e:
                print(f"Integration test failed with exception: {e}")
                test_results["Integration"] = False
        else:
            print("⚠️ Skipping integration test due to failed prerequisites")
            test_results["Integration"] = False
        
        # Test 5: Audio capabilities
        if test_results.get("OpenAI", False):
            try:
                test_results["Audio"] = test_audio_capabilities()
            except Exception as e:
                print(f"Audio test failed with exception: {e}")
                test_results["Audio"] = False
        else:
            print("⚠️ Skipping audio test due to failed OpenAI client test")
            test_results["Audio"] = False
        
        # Test 6: Async functionality
        if test_results.get("Integration", False):
            try:
                test_results["Async"] = asyncio.run(run_async_tests())
            except Exception as e:
                print(f"Async test failed with exception: {e}")
                test_results["Async"] = False
        else:
            print("⚠️ Skipping async test due to failed integration test")
            test_results["Async"] = False
        
    finally:
        # Cleanup resources
        try:
            from .chess_rag import close_chess_rag
            close_chess_rag()
        except Exception:
            pass  # Ignore cleanup errors
    
    # Summary
    print_test_header("TEST SUMMARY")
    total_tests = len(test_results)
    passed_tests = sum(test_results.values())
    
    print(f"\nResults ({passed_tests}/{total_tests} passed):")
    for test_name, passed in test_results.items():
        status = "✅" if passed else "❌"
        print(f"  {status} {test_name}")
    
    if passed_tests == total_tests:
        print("\n🎉 All tests passed! The Chess Trainer AI system is ready to use.")
    elif passed_tests >= total_tests // 2:
        print(f"\n⚠️ {passed_tests}/{total_tests} tests passed. System partially functional.")
    else:
        print(f"\n❌ Only {passed_tests}/{total_tests} tests passed. Please check configuration and dependencies.")
    
    return passed_tests == total_tests

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
    
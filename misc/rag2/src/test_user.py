#!/usr/bin/env python3
"""
Voice-enabled test script for Chess Trainer AI - FIXED VERSION
"""

import sys
import os
import asyncio
import numpy as np
from datetime import datetime

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.chess_agent import ChessTrainerAgent
from src.config import Config

try:
    import sounddevice as sd
    from agents.voice import AudioInput
    AUDIO_AVAILABLE = True
except ImportError:
    AUDIO_AVAILABLE = False
    print("⚠️ Audio dependencies not available. Install with: pip install sounddevice 'openai-agents[voice]'")


class AudioRecorder:
    """Simple audio recorder using sounddevice"""
    
    def __init__(self, samplerate=24000, channels=1, dtype=np.int16):
        self.samplerate = samplerate
        self.channels = channels
        self.dtype = dtype
        self.recording = False
        self.audio_frames = []
    
    async def record_audio(self, duration=5) -> np.ndarray:
        """Record audio for specified duration"""
        if not AUDIO_AVAILABLE:
            raise RuntimeError("Audio functionality not available")
        
        print(f"🎤 Recording for {duration} seconds... (speak now)")
        self.audio_frames = []
        
        def audio_callback(indata, frames, time, status):
            if status:
                print(f"Audio status: {status}")
            self.audio_frames.append(indata.copy())
        
        # Record audio
        try:
            with sd.InputStream(
                samplerate=self.samplerate,
                channels=self.channels,
                dtype=self.dtype,
                callback=audio_callback
            ):
                await asyncio.sleep(duration)
        except Exception as e:
            print(f"❌ Error during recording: {e}")
            return np.zeros(self.samplerate * duration, dtype=self.dtype)
        
        # Combine all frames
        if self.audio_frames:
            audio_data = np.concatenate(self.audio_frames, axis=0)
            # Flatten if needed (remove channel dimension for mono)
            if audio_data.ndim > 1:
                audio_data = audio_data.flatten()
            print(f"✅ Recording complete. Captured {len(audio_data)} samples")
            return audio_data
        else:
            print("⚠️ No audio captured")
            return np.zeros(self.samplerate * duration, dtype=self.dtype)

class AudioPlayer:
    """Simple audio player using sounddevice"""
    
    def __init__(self, samplerate=24000, channels=1, dtype=np.int16):
        self.samplerate = samplerate
        self.channels = channels
        self.dtype = dtype
        self.stream = None
        self.is_active = False
    
    def start(self):
        """Start the audio output stream"""
        if not AUDIO_AVAILABLE:
            return
        
        try:
            self.stream = sd.OutputStream(
                samplerate=self.samplerate,
                channels=self.channels,
                dtype=self.dtype
            )
            self.stream.start()
            self.is_active = True
            print("🔊 Audio player started")
        except Exception as e:
            print(f"❌ Error starting audio player: {e}")
    
    def play_chunk(self, audio_data):
        """Play an audio chunk"""
        if self.stream and AUDIO_AVAILABLE and self.is_active:
            try:
                self.stream.write(audio_data)
            except Exception as e:
                print(f"❌ Error playing audio chunk: {e}")
    
    def stop(self):
        """Stop the audio stream"""
        if self.stream and self.is_active:
            try:
                self.stream.stop()
                self.stream.close()
                self.is_active = False
                print("🔇 Audio player stopped")
            except Exception as e:
                print(f"❌ Error stopping audio player: {e}")
            finally:
                self.stream = None

async def test_voice_conversation():
    """Test voice conversation with the chess agent"""
    
    print("=" * 60)
    print(" Chess Trainer AI - Voice Test")
    print("=" * 60)
    print(f"Test started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    if not AUDIO_AVAILABLE:
        print("❌ Audio functionality not available")
        print("Install requirements: pip install sounddevice 'openai-agents[voice]'")
        return False
    
    # Initialize agent
    print("\n🚀 Initializing Chess Trainer Agent with Voice...")
    agent = ChessTrainerAgent()
    
    # Check if voice is available
    summary = agent.get_conversation_summary()
    if not summary.get('voice_available', False):
        print("❌ Voice functionality not available in agent")
        return False
    
    print("✅ Agent initialized successfully with voice support")
    
    # Display current state
    print(f"\n📋 Current FEN: {agent.current_fen}")
    print(f"🔍 Stockfish Analysis: {agent.stockfish_input}")
    
    # Initialize audio components
    recorder = AudioRecorder()
    player = AudioPlayer()
    
    print("\n🎙️ Starting voice conversation test...")
    print("Press Enter to record your question, or 'q' to quit")
    print("-" * 60)
    
    conversation_count = 0
    
    try:
        while True:
            # Get user input
            user_input = input(f"\n[Turn {conversation_count + 1}] Press Enter to speak (or 'q' to quit): ").strip()
            
            if user_input.lower() in ['q', 'quit', 'exit']:
                print("👋 Goodbye!")
                break
            
            conversation_count += 1
            
            try:
                # Record audio
                audio_data = await recorder.record_audio(duration=5)
                
                # Create audio input for the agent
                audio_input = AudioInput(buffer=audio_data)
                
                # Start audio player
                player.start()
                
                print("🤖 Chess Trainer is thinking and responding...")
                
                # Process voice input and get streaming response
                response_text = ""
                async for event in agent.chat_voice(audio_input):
                    event_type = event.get("type")
                    event_data = event.get("data")
                    
                    if event_type == "audio":
                        # Play audio chunk
                        player.play_chunk(event_data)
                    
                    elif event_type == "text":
                        # Display text as it streams
                        print(event_data, end="", flush=True)
                        response_text += event_data
                    
                    elif event_type == "lifecycle":
                        # Handle lifecycle events
                        if event_data == "turn_started":
                            print("\n🎯 Processing your question...")
                        elif event_data == "turn_ended":
                            print("\n✅ Response complete")
                    
                    elif event_type == "error":
                        print(f"\n❌ Error: {event_data}")
                
                # Stop audio player
                player.stop()
                
                print(f"\n📝 Full response: {response_text}")
                print("-" * 60)
                
            except Exception as e:
                print(f"❌ Error during voice interaction: {e}")
                player.stop()
                continue
    
    except KeyboardInterrupt:
        print("\n🔴 Interrupted by user")
    
    finally:
        # Cleanup
        player.stop()
        # Don't close agent here - will be handled later
    
    # Final summary
    final_summary = agent.get_conversation_summary()
    print(f"\n📊 Test Summary:")
    print(f"   Conversations: {conversation_count}")
    print(f"   Total messages: {final_summary['message_count']}")
    print(f"   Session ID: {final_summary['session_id']}")
    
    return True

async def test_text_conversation():
    """Test regular text conversation (fallback)"""
    
    print("=" * 60)
    print(" Chess Trainer AI - Text Test (Fallback)")
    print("=" * 60)
    print(f"Test started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Initialize agent
    print("\n🚀 Initializing Chess Trainer Agent...")
    agent = ChessTrainerAgent()
    print("✅ Agent initialized successfully")
    
    # Display current state
    print(f"\n📋 Current FEN: {agent.current_fen}")
    print(f"🔍 Stockfish Analysis: {agent.stockfish_input}")
    
    # Test questions
    test_questions = [
        "What's the best move in this position? White to play.",
        "Analyze the tactical opportunities for both sides.",
        "Should I be worried about my king safety?",
        "What's the strategic plan for White here?"
    ]
    
    print("\n💬 Starting text conversation test...")
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
            print(f"❌ Error: {e}")
            # Continue with other questions instead of failing completely
            continue
    
    # Final summary
    summary = agent.get_conversation_summary()
    print(f"\n📊 Test Summary:")
    print(f"   Total messages: {summary['message_count']}")
    print(f"   Session ID: {summary['session_id']}")
    
    return True

def print_audio_devices():
    """Print available audio devices for debugging"""
    if not AUDIO_AVAILABLE:
        print("❌ Audio functionality not available")
        return
    
    print("\n🎵 Available Audio Devices:")
    print("-" * 40)
    
    try:
        devices = sd.query_devices()
        for i, device in enumerate(devices):
            device_type = []
            if device['max_input_channels'] > 0:
                device_type.append("INPUT")
            if device['max_output_channels'] > 0:
                device_type.append("OUTPUT")
            
            print(f"{i:2d}: {device['name']}")
            print(f"     Type: {' | '.join(device_type)}")
            print(f"     Sample Rate: {device['default_samplerate']}")
            print()
        
        # Show default devices
        default_input = sd.query_devices(kind='input')
        default_output = sd.query_devices(kind='output')
        
        print(f"Default Input:  {default_input['name']}")
        print(f"Default Output: {default_output['name']}")
        
    except Exception as e:
        print(f"❌ Error querying audio devices: {e}")

async def main():
    """Main test function"""
    print("🎵 Chess Trainer AI - Voice Test Suite")
    
    # Print system info
    print(f"\n🐍 Python version: {sys.version}")
    print(f"📦 Audio available: {AUDIO_AVAILABLE}")
    
    if AUDIO_AVAILABLE:
        print_audio_devices()
        
        # Test voice conversation
        print("\n" + "=" * 60)
        print("Testing Voice Conversation")
        print("=" * 60)
        
        try:
            voice_success = await test_voice_conversation()
            print(f"\n🎤 Voice Test: {'✅ PASSED' if voice_success else '❌ FAILED'}")
        except Exception as e:
            print(f"\n🎤 Voice Test: ❌ FAILED - {e}")
            voice_success = False
    else:
        voice_success = False
        print("\n⚠️ Skipping voice test - audio functionality not available")
    
    # Test text conversation as fallback
    print("\n" + "=" * 60)
    print("Testing Text Conversation")
    print("=" * 60)
    
    try:
        text_success = await test_text_conversation()
        print(f"\n💬 Text Test: {'✅ PASSED' if text_success else '❌ FAILED'}")
    except Exception as e:
        print(f"\n💬 Text Test: ❌ FAILED - {e}")
        text_success = False
    
    # Cleanup connections properly
    print("\n🧹 Cleaning up...")
    try:
        from src.chess_rag import close_connection
        close_connection()
        print("✅ Connections closed properly")
    except Exception as e:
        print(f"⚠️ Cleanup warning: {e}")
    
    # Final results
    print("\n" + "=" * 60)
    print("Final Test Results")
    print("=" * 60)
    
    if voice_success and text_success:
        print("🎉 All tests PASSED! Chess Trainer AI with voice is working correctly.")
        return 0
    elif text_success:
        print("⚠️ Text functionality working, but voice unavailable.")
        print("   Install requirements: pip install sounddevice 'openai-agents[voice]'")
        return 0
    else:
        print("❌ Some tests FAILED. Please check the errors above.")
        return 1

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n🔴 Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
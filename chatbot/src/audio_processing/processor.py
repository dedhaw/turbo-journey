from fastapi import WebSocket, WebSocketDisconnect
import logging
import asyncio
from deepgram import DeepgramClient, LiveOptions
from dotenv import load_dotenv
import os
import json

from ..agent.response import ai_response
from .connection_manager import DeepgramConnectionManager
from .conversation_state import ConversationState
from .message_handler import WebSocketMessageHandler
from .audio import AudioProcessor

load_dotenv()

DEEPGRAM_API_KEY = os.getenv('DEEPGRAM_API_KEY')
deepgram = DeepgramClient(DEEPGRAM_API_KEY)


async def live_text_transcription(websocket: WebSocket):
    """Main orchestrator for real-time audio transcription and response."""
    
    connection_manager = DeepgramConnectionManager(deepgram)
    conversation_state = ConversationState()
    message_handler = WebSocketMessageHandler(connection_manager, conversation_state)
    audio_processor = AudioProcessor(deepgram)
    
    async def process_transcript():
        """Process transcript queue and generate AI responses."""
        while True:
            transcript_data = conversation_state.get_next_transcript()
            if transcript_data:
                transcript = transcript_data["transcript"]
                transcript_time = transcript_data["timestamp"]
                
                if conversation_state.should_ignore_user_input(transcript_time):
                    print(f"Ignoring user input during AI speech (within 2 seconds): {transcript}")
                    continue
                elif conversation_state.is_user_interrupting(transcript_time):
                    print(f"User interruption detected: {transcript}")
                    conversation_state.reset_ai_speaking()
                    await websocket.send_text(json.dumps({"interrupt": True}))
                
                if not conversation_state.ai_currently_speaking:
                    transcript = conversation_state.handle_partial_transcript(transcript)
                    
                    if not conversation_state.is_complete_sentence(transcript):
                        conversation_state.set_partial_transcript(transcript)
                        print(f"Incomplete sentence, keeping in buffer: {transcript}")
                        continue
                    
                    print(f"User Input: {transcript}")
                    conversation_state.start_ai_speaking()
                    
                    response_text = ai_response(transcript)
                    print(f"AI Response: {response_text}")
                    
                    await audio_processor.process_response_audio(
                        websocket, response_text, conversation_state
                    )
                
            await asyncio.sleep(0.1)
    
    def on_message(sender, result, **kwargs):
        try:
            transcript = result.channel.alternatives[0].transcript
            is_final = getattr(result, 'is_final', None)
            if is_final is None:
                is_final = getattr(result.channel.alternatives[0], 'is_final', False)
            
            if is_final and len(transcript) > 0:
                print(f"Final transcript: {transcript}")
                conversation_state.add_transcript(transcript)
            else:
                print("Interim transcript ignored")
        except Exception as e:
            logging.error(f"Error processing transcript: {e}")
    
    options = LiveOptions(
        model="nova-3", 
        interim_results=True, 
        language="en-US",
        punctuate=True,
        diarize=True,
        endpointing=300,
        vad_events=True,
        smart_format=True,
        utterance_end_ms="1000"
    )
    
    try:
        await websocket.send_text(json.dumps({
            "status": "ready",
            "message": "Server ready to accept commands"
        }))
        
        queue_task = asyncio.create_task(process_transcript())
        
        while True:
            try:
                message_data = await websocket.receive()
                
                if "text" in message_data:
                    await message_handler.handle_text_message(
                        websocket, message_data["text"], on_message, options
                    )
                
                elif "bytes" in message_data:
                    await message_handler.handle_bytes_message(
                        websocket, message_data["bytes"], on_message, options
                    )
                
            except WebSocketDisconnect:
                logging.info("WebSocket disconnected")
                break
            
            except Exception as e:
                logging.error(f"Error processing data: {e}")
                await websocket.send_text(json.dumps({"error": str(e)}))
                
    except WebSocketDisconnect:
        logging.info("Disconnected")
    except Exception as e:
        logging.error(f"Error in WebSocket handler: {e}")
    
    finally:
        try:
            await message_handler.cleanup()
            await connection_manager.close_connection()
            conversation_state.clear_state()
            if queue_task in locals():
                queue_task.cancel()
        except Exception as e:
            logging.error(f"Error in cleaning connection or finalizing events: {e}")
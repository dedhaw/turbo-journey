from fastapi import WebSocket, WebSocketDisconnect
import logging
import asyncio
from deepgram import DeepgramClient, LiveOptions
from dotenv import load_dotenv
import os
import json

from .connection_manager import DeepgramConnectionManager
from .conversation_state import ConversationState
from .message_handler import WebSocketMessageHandler
from .audio import AudioProcessor
from .transcript_processor import TranscriptProcessor

load_dotenv()

DEEPGRAM_API_KEY = os.getenv('DEEPGRAM_API_KEY')
deepgram = DeepgramClient(DEEPGRAM_API_KEY)


async def live_text_transcription(websocket: WebSocket):
    """Main loop for real-time audio transcription and response."""
    
    connection_manager = DeepgramConnectionManager(deepgram)
    conversation_state = ConversationState()
    message_handler = WebSocketMessageHandler(connection_manager, conversation_state)
    audio_processor = AudioProcessor(deepgram)
    transcript_processor = TranscriptProcessor(conversation_state, audio_processor)
    
    on_message = transcript_processor.setup_deepgram_callback()
    
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
    
    # Main WebSocket loop
    try:
        await websocket.send_text(json.dumps({
            "status": "ready",
            "message": "Server ready to accept commands"
        }))
        
        queue_task = asyncio.create_task(transcript_processor.start_processing(websocket))
        
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
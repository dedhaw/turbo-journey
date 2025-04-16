from fastapi import WebSocket, WebSocketDisconnect
import logging
import asyncio
from deepgram import DeepgramClient, LiveOptions, LiveTranscriptionEvents
from dotenv import load_dotenv
import os
import json
import queue

from ..agent.core import ai_response

load_dotenv()

DEEPGRAM_API_KEY = os.getenv('DEEPGRAM_API_KEY')

async def live_audio_transcription(websocket: WebSocket, output_message):
    pass

async def live_text_transcription(websocket: WebSocket):
    transcript_queue = queue.Queue()
    
    # Task to process the queue and send messages
    async def process_queue():
        while True:
            # Check if there are items in the queue to process
            if not transcript_queue.empty():
                transcript = transcript_queue.get()
                
                # Send back output to frontend using websocket
                print(transcript)
                await websocket.send_text(json.dumps({"transcript": await ai_response(transcript)}))
            # Small sleep to avoid CPU spinning
            await asyncio.sleep(0.1)
    
    # Start the queue processing task
    queue_task = asyncio.create_task(process_queue())
    
    try:
        # Initialize Deepgram client for live transcription
        deepgram = DeepgramClient(DEEPGRAM_API_KEY)
        conn = deepgram.listen.websocket.v("1")
        
        # Handle incoming transcription results with a thread-safe queue
        def on_message(sender, result, **kwargs):
            try:
                transcript = result.channel.alternatives[0].transcript
                if len(transcript) > 0:
                    logging.info(f"Transcript: {transcript}")
                    # Put the transcript in the queue - no asyncio needed
                    transcript_queue.put(transcript)
            except Exception as e:
                logging.error(f"Error processing transcript: {e}")
        
        # Set up Deepgram event handler
        conn.on(LiveTranscriptionEvents.Transcript, on_message)
        
        # Configure Deepgram options
        options = LiveOptions(
            model="nova-3", 
            interim_results=False, 
            language="en-US",
            punctuate=True,
            diarize=True
        )
        
        # Start Deepgram connection
        conn.start(options)
        
        # Process audio from client
        while True:
            try:
                # Add a heartbeat to Deepgram to prevent timeout
                heartbeat_task = asyncio.create_task(send_heartbeat(conn))
                
                # Receive audio data from WebSocket
                audio_data = await websocket.receive_bytes()
                
                # Cancel heartbeat task since we got real data
                heartbeat_task.cancel()
                
                # Send audio data to Deepgram for transcription
                conn.send(audio_data)
            except WebSocketDisconnect:
                logging.info("WebSocket disconnected")
                break
            except Exception as e:
                logging.error(f"Error processing audio data: {e}")
                await websocket.send_text(json.dumps({"error": str(e)}))
                break
                
    except WebSocketDisconnect:
        logging.info("Client disconnected")
    except Exception as e:
        logging.error(f"Error in WebSocket handler: {e}")
    finally:
        # Clean up resources
        try:
            if 'conn' in locals():
                conn.finish()
            if 'queue_task' in locals():
                queue_task.cancel()
        except Exception as e:
            logging.error(f"Error finalizing connection: {e}")

async def send_heartbeat(conn, interval=5):
    """Send empty packets to keep the Deepgram connection alive"""
    try:
        while True:
            await asyncio.sleep(interval)
            conn.send(b"")
    except asyncio.CancelledError:
        pass
    except Exception as e:
        logging.error(f"Heartbeat error: {e}")
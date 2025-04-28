from deepgram import LiveTranscriptionEvents
from fastapi import WebSocket
import asyncio
import logging
import re
import json
        
async def split_into_sentences(text):
    """Split text into sentences for progressive audio generation."""
    sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', text)
    return [s.strip() for s in sentences if s.strip()]


async def check_and_reconnect(conn, is_connected, reconnect_attempts, on_message, options, websocket: WebSocket, deepgram_client):
    """Monitor the Deepgram connection and reconnect if necessary."""
    max_reconnect_attempts = 3
    while is_connected and reconnect_attempts < max_reconnect_attempts:
        await asyncio.sleep(5)
        
        try:
            if not conn or not conn.is_connected():
                logging.warning("Deepgram connection lost, attempting to reconnect...")
                
                if conn:
                    try:
                        conn.finish()
                    except:
                        pass
                
                conn = deepgram_client.listen.websocket.v("1")
                conn.on(LiveTranscriptionEvents.Transcript, on_message)
                conn.start(options)
                
                reconnect_attempts += 1
                logging.info(f"Reconnected to Deepgram (attempt {reconnect_attempts})")
                
                await websocket.send_text(json.dumps({
                    "status": "reconnected",
                    "message": "Connection restored"
                }))
            else:
                reconnect_attempts = 0
                
        except Exception as e:
            logging.error(f"Error during reconnection: {e}")
            await asyncio.sleep(2)
    
    return conn, reconnect_attempts

async def create_deepgram_connection(on_message, deepgram_client, options):
    """Helper function to create a new Deepgram connection."""
    try:
        conn = deepgram_client.listen.websocket.v("1")
        
        conn.on(LiveTranscriptionEvents.Transcript, on_message)
        conn.start(options)
        
        logging.info("Created new Deepgram connection")
        return conn, options
    except Exception as e:
        logging.error(f"Error creating Deepgram connection: {e}")
        return None, None

async def close_connection(conn):
    """Helper function to safely close a Deepgram connection."""
    if conn:
        try:
            conn.finish()
            logging.info("Closed Deepgram connection")
            return True
        except Exception as e:
            logging.error(f"Error closing Deepgram connection: {e}")
    return False

async def handle_command(websocket, conn, message, on_message, deepgram_client, options):
    """Process commands received from frontend."""
    if message.get("action") == "start_listening":
        await close_connection(conn)
        
        conn, _ = await create_deepgram_connection(on_message, deepgram_client, options)
        
        await websocket.send_text(json.dumps({
            "status": "listening",
            "message": "Ready for audio"
        }))
        
    elif message.get("action") == "stop_listening":
        await close_connection(conn)
        conn = None
        
        await websocket.send_text(json.dumps({
            "status": "stopped",
            "message": "Listening stopped"
        }))
        
    return conn


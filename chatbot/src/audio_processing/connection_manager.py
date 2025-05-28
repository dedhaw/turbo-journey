from deepgram import LiveTranscriptionEvents
import logging
import json


class DeepgramConnectionManager:
    """Manages Deepgram WebSocket connections including creation, health monitoring, and cleanup."""
    
    def __init__(self, deepgram_client):
        self.deepgram_client = deepgram_client
        self.connection = None
        self.is_connected = False
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 3
        
    async def create_connection(self, on_message, options):
        """Create a new Deepgram connection."""
        try:
            await self.close_connection()
            
            conn = self.deepgram_client.listen.websocket.v("1")
            conn.on(LiveTranscriptionEvents.Transcript, on_message)
            conn.start(options)
            
            self.connection = conn
            self.is_connected = True
            self.reconnect_attempts = 0
            
            logging.info("Created new Deepgram connection")
            return conn
            
        except Exception as e:
            logging.error(f"Error creating Deepgram connection: {e}")
            self.is_connected = False
            return None
    
    async def close_connection(self):
        """Safely close the current Deepgram connection."""
        if self.connection:
            try:
                self.connection.finish()
                logging.info("Closed Deepgram connection")
            except Exception as e:
                logging.error(f"Error closing Deepgram connection: {e}")
            finally:
                self.connection = None
                self.is_connected = False
                return True
        return False
    
    def send_audio(self, audio_data):
        """Send audio data to Deepgram if connection is active."""
        if self.connection and self.is_connected and hasattr(self.connection, 'is_connected') and self.connection.is_connected():
            try:
                self.connection.send(audio_data)
                return True
            except Exception as e:
                logging.error(f"Error sending audio data: {e}")
                self.is_connected = False
                return False
        return False
    
    def is_connection_healthy(self):
        """Check if the connection is healthy."""
        return (self.connection is not None and 
                self.is_connected and 
                hasattr(self.connection, 'is_connected') and 
                self.connection.is_connected())
    
    async def handle_start_listening(self, websocket, on_message, options):
        """Handle start listening command."""
        conn = await self.create_connection(on_message, options)
        if conn:
            await websocket.send_text(json.dumps({
                "status": "listening",
                "message": "Ready for audio"
            }))
        else:
            await websocket.send_text(json.dumps({
                "status": "error",
                "message": "Failed to start listening"
            }))
        return conn
    
    async def handle_stop_listening(self, websocket):
        """Handle stop listening command."""
        await self.close_connection()
        await websocket.send_text(json.dumps({
            "status": "stopped", 
            "message": "Connection closed"
        }))
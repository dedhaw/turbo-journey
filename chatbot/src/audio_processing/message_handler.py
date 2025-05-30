import json
import base64
import logging
import asyncio

class WebSocketMessageHandler:
    """Handles WebSocket message processing including commands and audio data routing."""
    
    def __init__(self, connection_manager, conversation_state):
        self.connection_manager = connection_manager
        self.conversation_state = conversation_state
        self.keepalive_task = None
        
    async def handle_text_message(self, websocket, message_text, on_message, options):
        """Handle text-based WebSocket messages (commands and JSON data)."""
        try:
            message = json.loads(message_text)
            
            if message.get("action") == "start_listening":
                await self._handle_start_listening(websocket, on_message, options)
                
            elif message.get("action") == "stop_listening":
                await self._handle_stop_listening(websocket)
                
            elif message.get("type") == "audio" and message.get("data"):
                await self._handle_audio_data(message)
                
        except json.JSONDecodeError:
            logging.error("Received invalid JSON message")
            
    async def handle_bytes_message(self, websocket, audio_bytes, on_message, options):
        """Handle binary audio data messages."""
        if not self.conversation_state.ai_currently_speaking:
            self.conversation_state.update_audio_time()
            
            if self.connection_manager.is_connection_healthy():
                self.connection_manager.send_audio(audio_bytes)
            else:
                await self._handle_start_listening(websocket, on_message, options)
                
                if self.connection_manager.is_connection_healthy():
                    self.connection_manager.send_audio(audio_bytes)
                    
                    await websocket.send_text(json.dumps({
                        "status": "listening",
                        "message": "Auto-started listening"
                    }))
        else:
            print("AI is speaking, ignoring audio bytes")
            
    async def _handle_start_listening(self, websocket, on_message, options):
        """Handle start listening command."""
        await self.connection_manager.handle_start_listening(websocket, on_message, options)
        
        if self.connection_manager.is_connection_healthy() and not self.keepalive_task:
            self.keepalive_task = asyncio.create_task(self._send_keepalive())
            
    async def _handle_stop_listening(self, websocket):
        """Handle stop listening command."""
        print("Stop listening command received")
        
        if self.conversation_state.ai_currently_speaking:
            print("Stopping AI speech due to stop command")
            self.conversation_state.reset_ai_speaking()
        
        if self.keepalive_task:
            self.keepalive_task.cancel()
            self.keepalive_task = None
            print("Cancelled keepalive task")
        
        await self.connection_manager.handle_stop_listening(websocket)
        print("Stop listening completed")
        
    async def _handle_audio_data(self, message):
        """Handle JSON-encoded audio data."""
        if not self.conversation_state.ai_currently_speaking:
            audio_data = base64.b64decode(message["data"])
            self.connection_manager.send_audio(audio_data)
            self.conversation_state.update_audio_time()
            
    async def _send_keepalive(self):
        """Send periodic keepalive to prevent Deepgram timeout during AI speech"""
        while True:
            await asyncio.sleep(8)
            
            if (self.conversation_state.needs_keepalive() and 
                self.connection_manager.is_connection_healthy()):
                try:
                    silent_audio = b'\x00' * 320
                    self.connection_manager.send_audio(silent_audio)
                    print("Sent keepalive to Deepgram during AI speech")
                except Exception as e:
                    print(f"Keepalive failed: {e}")
                    break
                    
    async def cleanup(self):
        """Clean up message handler resources."""
        if self.keepalive_task:
            self.keepalive_task.cancel()
            self.keepalive_task = None
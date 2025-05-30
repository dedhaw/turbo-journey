import json
import asyncio
import logging
from agent.response import ai_response

class TranscriptProcessor:
    """Handles transcript processing, AI response generation, and conversation flow."""
    
    def __init__(self, conversation_state, audio_processor):
        self.conversation_state = conversation_state
        self.audio_processor = audio_processor
        
    async def start_processing(self, websocket):
        """Start the transcript processing loop."""
        while True:
            await self._process_next_transcript(websocket)
            await asyncio.sleep(0.1)
    
    async def _process_next_transcript(self, websocket):
        """Process the next transcript from the queue."""
        transcript_data = self.conversation_state.get_next_transcript()
        if not transcript_data:
            return
            
        transcript = transcript_data["transcript"]
        transcript_time = transcript_data["timestamp"]
        
        # Handle interruption logic
        if self.conversation_state.should_ignore_user_input(transcript_time):
            print(f"Ignoring user input during AI speech (within 2 seconds): {transcript}")
            return
            
        elif self.conversation_state.is_user_interrupting(transcript_time):
            print(f"User interruption detected: {transcript}")
            self.conversation_state.reset_ai_speaking()
            await websocket.send_text(json.dumps({"interrupt": True}))
            return
        
        if not self.conversation_state.ai_currently_speaking:
            await self._handle_user_input(websocket, transcript)
    
    async def _handle_user_input(self, websocket, transcript):
        """Handle user input and generate AI response."""
        transcript = self.conversation_state.handle_partial_transcript(transcript)
        
        if not self.conversation_state.is_complete_sentence(transcript):
            self.conversation_state.set_partial_transcript(transcript)
            print(f"Incomplete sentence, keeping in buffer: {transcript}")
            return
        
        print(f"User Input: {transcript}")
        self.conversation_state.start_ai_speaking()
        
        try:
            response_text = ai_response(transcript)
            print(f"AI Response: {response_text}")
            
            await self.audio_processor.process_response_audio(
                websocket, response_text, self.conversation_state
            )
            
        except Exception as e:
            logging.error(f"Error generating AI response: {e}")
            self.conversation_state.reset_ai_speaking()
            await websocket.send_text(json.dumps({
                "error": "Failed to generate AI response"
            }))
    
    def setup_deepgram_callback(self):
        """Create and return the Deepgram message callback function."""
        def on_message(sender, result, **kwargs):
            try:
                transcript = result.channel.alternatives[0].transcript
                is_final = getattr(result, 'is_final', None)
                if is_final is None:
                    is_final = getattr(result.channel.alternatives[0], 'is_final', False)
                
                if is_final and len(transcript) > 0:
                    print(f"Final transcript: {transcript}")
                    self.conversation_state.add_transcript(transcript)
                else:
                    logging.info("Interim transcript ignored")
            except Exception as e:
                logging.error(f"Error processing transcript: {e}")
        
        return on_message
import tempfile
import base64
import logging
import asyncio
import os
import json
import re
from deepgram import SpeakOptions


async def split_into_sentences(text):
    """Split text into sentences for progressive audio generation."""
    sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', text)
    return [s.strip() for s in sentences if s.strip()]


class AudioProcessor:
    """Handles text-to-speech conversion and audio generation."""
    
    def __init__(self, deepgram_client):
        self.deepgram_client = deepgram_client
        
    async def generate_speech_audio(self, sentence):
        """Convert a single sentence to speech audio bytes."""
        try:
            with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_file:
                temp_filename = temp_file.name
                
            speak_options = {"text": sentence}
            options = SpeakOptions(
                model="aura-2-thalia-en",
            )
            
            _ = self.deepgram_client.speak.rest.v("1").save(temp_filename, speak_options, options)
            
            with open(temp_filename, 'rb') as f:
                audio_bytes = f.read()
                
            try:
                os.unlink(temp_filename)
            except:
                pass
                
            return audio_bytes
        
        except Exception as e:
            logging.error(f"Error generating speech for sentence: {e}")
            return None
    
    async def process_response_audio(self, websocket, response_text, conversation_state):
        """Process AI response text and generate streaming audio."""
        sentences = await split_into_sentences(response_text)
        
        # Send transcript to frontend first
        await websocket.send_text(json.dumps({"transcript": response_text}))
        
        for i, sentence in enumerate(sentences):
            if not conversation_state.ai_currently_speaking:
                print(f"AI speech interrupted, stopping at sentence {i}")
                break
                
            print(f"Generating audio for sentence {i+1}/{len(sentences)}: {sentence}")
            audio_bytes = await self.generate_speech_audio(sentence)
            
            if not conversation_state.ai_currently_speaking:
                print(f"AI speech interrupted during audio generation for sentence {i}")
                break
            
            if audio_bytes:
                await self._send_audio_to_frontend(websocket, audio_bytes, sentence)
                await asyncio.sleep(0.1)
        
        # Signal completion if not interrupted
        if conversation_state.ai_currently_speaking:
            print("AI finished speaking")
            conversation_state.reset_ai_speaking()
            await websocket.send_text(json.dumps({"ai_finished_speaking": True}))
    
    async def _send_audio_to_frontend(self, websocket, audio_bytes, sentence):
        """Send audio data to frontend via WebSocket."""
        audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')
        await websocket.send_text(json.dumps({
            "audio": audio_base64,
            "content_type": "audio/mp3",
            "sentence": sentence
        }))
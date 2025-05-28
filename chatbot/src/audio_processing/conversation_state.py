import queue
import time


class ConversationState:
    """Manages the state of the conversation including AI speaking status, transcripts, and timing."""
    
    def __init__(self):
        self.transcript_queue = queue.Queue()
        self.ai_currently_speaking = False
        self.ai_speaking_start_time = None
        self.last_audio_time = time.time()
        self.partial_transcript = ""
        
    def reset_ai_speaking(self):
        """Reset AI speaking state."""
        self.ai_currently_speaking = False
        self.ai_speaking_start_time = None
        
    def start_ai_speaking(self):
        """Start AI speaking state."""
        self.ai_currently_speaking = True
        self.ai_speaking_start_time = time.time()
        
    def update_audio_time(self):
        """Update the last audio received time."""
        self.last_audio_time = time.time()
        
    def add_transcript(self, transcript, timestamp=None):
        """Add a transcript to the processing queue."""
        if timestamp is None:
            timestamp = time.time()
        
        self.transcript_queue.put({
            "transcript": transcript,
            "timestamp": timestamp
        })
        
    def get_next_transcript(self):
        """Get the next transcript from the queue, or None if empty."""
        if not self.transcript_queue.empty():
            return self.transcript_queue.get()
        return None
        
    def should_ignore_user_input(self, transcript_time):
        """Check if user input should be ignored (within 2 seconds of AI starting to speak)."""
        if self.ai_currently_speaking and self.ai_speaking_start_time:
            time_since_ai_started = transcript_time - self.ai_speaking_start_time
            return time_since_ai_started <= 2.0
        return False
        
    def is_user_interrupting(self, transcript_time):
        """Check if user is interrupting AI speech (after 2 seconds)."""
        if self.ai_currently_speaking and self.ai_speaking_start_time:
            time_since_ai_started = transcript_time - self.ai_speaking_start_time
            return time_since_ai_started > 2.0
        return False
        
    def needs_keepalive(self):
        """Check if a keepalive signal should be sent to Deepgram."""
        current_time = time.time()
        return (self.ai_currently_speaking and 
                current_time - self.last_audio_time > 8)
                
    def handle_partial_transcript(self, transcript):
        """Handle partial transcript accumulation."""
        if self.partial_transcript:
            combined = self.partial_transcript + " " + transcript
            self.partial_transcript = ""
            return combined
        return transcript
        
    def set_partial_transcript(self, transcript):
        """Set a partial transcript to be combined with the next complete one."""
        self.partial_transcript = transcript
        
    def is_complete_sentence(self, transcript):
        """Check if transcript forms a complete sentence."""
        sentence_endings = ['.', '!', '?', '…']
        has_ending = any(transcript.rstrip().endswith(ending) for ending in sentence_endings)
        return has_ending or transcript.endswith('...')
        
    def clear_state(self):
        """Clear all conversation state (useful for cleanup)."""
        while not self.transcript_queue.empty():
            try:
                self.transcript_queue.get_nowait()
            except queue.Empty:
                break
                
        self.reset_ai_speaking()
        self.partial_transcript = ""
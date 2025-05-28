from deepgram import DeepgramClient, SpeakOptions, LiveOptions, LiveTranscriptionEvents
from dotenv import load_dotenv
import os
import threading
import httpx

load_dotenv()
DEEPGRAM_API_KEY = os.getenv('DEEPGRAM_API_KEY')

async def test_live_transcription():
    AUDIO_URL = {
        "url": "https://static.deepgram.com/examples/Bueller-Life-moves-pretty-fast.wav"
    }

    try:
        deepgram = DeepgramClient(DEEPGRAM_API_KEY)
        
        conn = deepgram.listen.websocket.v("1")
        
        def on_message(self, result, **kwargs):
            sentence = result.channel.alternatives[0].transcript
            if len(sentence) > 0:
                print(f"Speaker: {sentence}")
                
        conn.on(LiveTranscriptionEvents.Transcript, on_message)

        options = LiveOptions(model="nova-3", interim_results=False, language="en-US")
        conn.start(options)

        lock_exit = threading.Lock()
        exit = False

        def myThread():
            with httpx.stream("GET", AUDIO_URL["url"]) as r:
                for data in r.iter_bytes():
                    lock_exit.acquire()
                    if exit:
                        break
                    lock_exit.release()

                    conn.send(data)

        myHttp = threading.Thread(target=myThread)
        myHttp.start()

        input("Press Enter to stop recording...\n\n")

        lock_exit.acquire()
        exit = True
        lock_exit.release()
        myHttp.join()
        conn.finish()

    except Exception as e:
        print(f"Could not open socket: {e}")
        return
    
    
async def test_audio_transcription():
    SPEAK_OPTIONS = {"text": "Hello, how can I help you today?"}
    filename = "output.mp3"
    try:
        # STEP 1: Create a Deepgram client.
        # By default, the DEEPGRAM_API_KEY environment variable will be used for the API Key
        deepgram = DeepgramClient(DEEPGRAM_API_KEY)
        # STEP 2: Configure the options (such as model choice, audio configuration, etc.)
        options = SpeakOptions(
            model="aura-2-thalia-en",
        )
        # STEP 3: Call the save method on the speak property
        response = deepgram.speak.rest.v("1").save(filename, SPEAK_OPTIONS, options)
        print(response.to_json(indent=4))
    except Exception as e:
        print(f"Exception: {e}")
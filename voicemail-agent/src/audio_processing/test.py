from deepgram import DeepgramClient, LiveOptions, LiveTranscriptionEvents
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
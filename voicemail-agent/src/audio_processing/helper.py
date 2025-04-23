import asyncio
import logging

async def send_heartbeat(conn, interval=5):
    """Send empty packets to keep the Deepgram connection alive. This is incase the
    user takes breaths or more time between words/sentences.
    """
    try:
        while True:
            await asyncio.sleep(interval)
            conn.send(b"")
    except asyncio.CancelledError:
        pass
    except Exception as e:
        logging.error(f"Heartbeat error: {e}")
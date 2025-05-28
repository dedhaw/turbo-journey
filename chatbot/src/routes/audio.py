from fastapi import APIRouter, WebSocket
from ..audio_processing.processor import live_text_transcription
from ..audio_processing.test import test_live_transcription
import logging

router = APIRouter()

@router.websocket("/listen")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    logging.info("WebSocket connected")
    await live_text_transcription(websocket)

@router.get("/test-api")
async def test_deepgram_api_key():
    await test_live_transcription()
    return {"status": "Deepgram API test completed"}
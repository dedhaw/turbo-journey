from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes.test import router as test_router
from routes.audio import router as audio_router
import logging

# logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

import os
import certifi

os.environ['SSL_CERT_FILE'] = certifi.where()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173/"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(test_router)
app.include_router(audio_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
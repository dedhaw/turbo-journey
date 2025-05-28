import re

async def split_into_sentences(text):
    """Split text into sentences for progressive audio generation."""
    sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', text)
    return [s.strip() for s in sentences if s.strip()]
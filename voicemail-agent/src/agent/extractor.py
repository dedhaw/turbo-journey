from openai import OpenAI
from dotenv import load_dotenv
import os
import json
import logging
from .prompts import json_extraction_query
from ..db.entity_operations import get_context

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def extract_context(prompt):
    context = get_context()
    
    completion = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {
                "role": "user",
                "content": f"{json_extraction_query} {prompt}"
            }
        ]
    )

    response_text = completion.choices[0].message.content
    
    try:
        extracted_data = json.loads(response_text)
        return extracted_data
    
    except json.JSONDecodeError:
        logging.error("error Failed to parse JSON")
from openai import OpenAI
import os
from dotenv import load_dotenv
from .prompts import bot_background_information, basic_response
# from ..db.entity_operations import get_context

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def ai_response(user_message):
    return response_generator(f"{bot_background_information} {basic_response} {user_message}")

def response_generator(prompt):
    # context = get_context(prompt)
    
    completion = client.chat.completions.create(
        model="gpt-4",
        max_tokens= 250,
        messages=[
            {
                "role": "user",
                "content": f"{prompt}"
            }
        ]
    )

    return completion.choices[0].message.content
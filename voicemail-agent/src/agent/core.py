from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

async def ai_response(user_message):
    completion = client.chat.completions.create(
        model="gpt-4.1",
        messages=[
            {
                "role": "user",
                "content": f"""Respond to the users promp as if you were having a conversation
                here is the users message: {user_message}"""
            }
        ]
    )

    return completion.choices[0].message.content
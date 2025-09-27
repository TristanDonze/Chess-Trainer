# chat.py
from openai import OpenAI
import asyncio
from fastmcp import Client

import os
import dotenv

dotenv.load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai_client = OpenAI(api_key=OPENAI_API_KEY)

url = " http://127.0.0.1:8000/mcp"

user_query = (
    "Je joue les blancs dans une Sicilienne. "
    "Donne moi deux plans thématiques et cite des éléments de ta base s’ils existent."
)

result = openai_client.responses.create(
    model="gpt-5",
    input=user_query,
    reasoning={"effort": "medium"},
    text={"verbosity": "high"},
    tools=[
        {
            "type": "mcp",
            "server_label": "chesskb",
            "server_url": url,
            "require_approval": "never",
        }
    ],
)
print(result)
print("=== Final response ===")
print(result.output_text)

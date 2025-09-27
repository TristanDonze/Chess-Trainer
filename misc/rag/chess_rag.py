# chess_rag.py

import os, json, weaviate
from weaviate.classes.init import Auth
from dotenv import load_dotenv

load_dotenv()
openai_api_key = os.environ["OPENAI_API_KEY"]
weaviate_url = os.environ["WEAVIATE_REST_ENDPOINT"]
weaviate_api_key = os.environ["WEAVIATE_API_KEY"]

headers = {
    "X-OpenAI-Api-Key": openai_api_key
}

client = weaviate.connect_to_weaviate_cloud(
    cluster_url=weaviate_url,
    auth_credentials=Auth.api_key(weaviate_api_key),
    skip_init_checks=True,
    headers=headers
)
print("Weaviate ready:", client.is_ready())

CHESS_RAG = client.collections.use("ChessKnowledgeBase")
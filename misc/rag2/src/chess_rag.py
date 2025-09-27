# chess_rag.py
"""
Simplified Chess Knowledge RAG Module
"""

import os
import weaviate
from weaviate.classes.init import Auth
from dotenv import load_dotenv

load_dotenv()

# Configuration
openai_api_key = os.environ["OPENAI_API_KEY"]
weaviate_url = os.environ["WEAVIATE_REST_ENDPOINT"]
weaviate_api_key = os.environ["WEAVIATE_API_KEY"]

headers = {
    "X-OpenAI-Api-Key": openai_api_key
}

# Global client and collection
client = weaviate.connect_to_weaviate_cloud(
    cluster_url=weaviate_url,
    auth_credentials=Auth.api_key(weaviate_api_key),
    skip_init_checks=True,
    headers=headers
)

CHESS_RAG = client.collections.use("ChessKnowledgeBase")

def retrieve_chess_knowledge(query: str, limit: int = 2) -> dict:
    """
    Retrieve relevant chess knowledge from the knowledge base.
    
    Args:
        query (str): The query string to search for relevant information.
        limit (int): Number of results to return
        
    Returns:
        dict: The retrieved information from the knowledge base.
    """
    response = CHESS_RAG.query.near_text(
        query=query,
        limit=limit
    )
    response_json = [obj.properties for obj in response.objects]
    return response_json

def close_connection():
    """Close the Weaviate connection"""
    client.close()
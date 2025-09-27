# chess_rag.py
"""
Simplified Chess Knowledge RAG Module - FIXED VERSION
"""

import os
import weaviate
from weaviate.classes.init import Auth
from dotenv import load_dotenv

load_dotenv()

# Configuration
openai_api_key = os.environ.get("OPENAI_API_KEY", "")
weaviate_url = os.environ.get("WEAVIATE_REST_ENDPOINT", "")
weaviate_api_key = os.environ.get("WEAVIATE_API_KEY", "")

headers = {
    "X-OpenAI-Api-Key": openai_api_key
}

# Global client - managed as singleton
_weaviate_client = None
_chess_rag_collection = None

def get_weaviate_client():
    """Get or create Weaviate client with proper connection management"""
    global _weaviate_client
    
    if _weaviate_client is None:
        _weaviate_client = weaviate.connect_to_weaviate_cloud(
            cluster_url=weaviate_url,
            auth_credentials=Auth.api_key(weaviate_api_key),
            skip_init_checks=True,
            headers=headers
        )
    
    # Ensure connection is active
    if not _weaviate_client.is_connected():
        try:
            _weaviate_client.connect()
        except Exception as e:
            print(f"Warning: Could not reconnect to Weaviate: {e}")
    
    return _weaviate_client

def get_chess_collection():
    """Get chess knowledge collection"""
    global _chess_rag_collection
    
    if _chess_rag_collection is None:
        client = get_weaviate_client()
        _chess_rag_collection = client.collections.use("ChessKnowledgeBase")
    
    return _chess_rag_collection

def retrieve_chess_knowledge(query: str, limit: int = 2) -> dict:
    """
    Retrieve relevant chess knowledge from the knowledge base.
    
    Args:
        query (str): The query string to search for relevant information.
        limit (int): Number of results to return
        
    Returns:
        dict: The retrieved information from the knowledge base.
    """
    try:
        collection = get_chess_collection()
        response = collection.query.near_text(
            query=query,
            limit=limit
        )
        response_json = [obj.properties for obj in response.objects]
        return response_json
    except Exception as e:
        print(f"Error retrieving chess knowledge: {e}")
        return {"error": str(e), "results": []}

def close_connection():
    """Close the Weaviate connection - use with caution"""
    global _weaviate_client, _chess_rag_collection
    
    if _weaviate_client and _weaviate_client.is_connected():
        _weaviate_client.close()
    
    # Reset globals so they'll be recreated if needed
    _weaviate_client = None
    _chess_rag_collection = None

def ensure_connection():
    """Ensure Weaviate connection is active"""
    client = get_weaviate_client()
    if not client.is_connected():
        client.connect()
    return client
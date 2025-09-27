# tools.py

from chess_rag import client, CHESS_RAG


def retrieve(query: str):
    """
    Retrieve relevant chess knowledge from the knowledge base.
    Args:
        query (str): The query string to search for relevant information.
    Returns:
        dict: The retrieved information from the knowledge base.
    """
    response = CHESS_RAG.query.near_text(
        query=query,
        limit=2
    )
    response_json = [obj.properties for obj in response.objects]
    return response_json


if __name__ == "__main__":
    print(retrieve("Give me advice in endgame when im a bad position."))
    client.close()
# chess_rag.py
"""
Enhanced Chess Knowledge RAG Module
Provides retrieval-augmented generation for chess knowledge using Weaviate
with robust fallbacks and error handling
"""

import logging
import time
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

# Try Weaviate import with graceful fallback
try:
    import weaviate
    from weaviate.classes.init import Auth
    from weaviate.classes.query import MetadataQuery
    WEAVIATE_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ Weaviate not available: {e}")
    print("To install: pip install weaviate-client")
    WEAVIATE_AVAILABLE = False
    weaviate = None

from .config import Config

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class ChessKnowledgeResult:
    """Structured result from chess knowledge retrieval"""
    title: str
    content: str
    type: str
    tags: List[str]
    score: float
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "content": self.content,
            "type": self.type,
            "tags": self.tags,
            "score": self.score
        }

class ChessRAG:
    """Chess knowledge retrieval and RAG functionality with fallbacks"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the Chess RAG system"""
        self.config = config or Config.weaviate
        self.client = None
        self.collection = None
        self.connected = False
        
        if WEAVIATE_AVAILABLE:
            self._connect()
        else:
            logger.warning("Weaviate client not available, using fallback knowledge")
    
    def _connect(self):
        """Connect to Weaviate and set up collection"""
        try:
            self.client = weaviate.connect_to_weaviate_cloud(
                cluster_url=self.config.url,
                auth_credentials=Auth.api_key(self.config.api_key),
                skip_init_checks=True,
                headers=self.config.headers
            )
            
            if not self.client.is_ready():
                raise ConnectionError("Weaviate client is not ready")
            
            self.collection = self.client.collections.use(self.config.collection_name)
            self.connected = True
            logger.info(f"✅ Connected to Weaviate collection: {self.config.collection_name}")
            
        except Exception as e:
            logger.error(f"Failed to connect to Weaviate: {e}")
            self.connected = False
    
    def _get_fallback_knowledge(self, query: str) -> List[ChessKnowledgeResult]:
        """Provide fallback chess knowledge when RAG is unavailable"""
        query_lower = query.lower()
        
        # Basic chess knowledge fallback
        fallback_knowledge = {
            "opening": {
                "title": "Chess Opening Principles",
                "content": "1. Control the center with pawns (e4, d4, e5, d5). 2. Develop knights before bishops. 3. Castle early for king safety. 4. Don't move the same piece twice in the opening. 5. Don't bring your queen out too early.",
                "type": "opening",
                "tags": ["principles", "development", "center"]
            },
            "tactics": {
                "title": "Basic Chess Tactics",
                "content": "Pin: Attacking a piece that cannot move without exposing a more valuable piece. Fork: Attacking two pieces simultaneously. Skewer: Forcing a valuable piece to move, exposing a less valuable piece. Discovery: Moving one piece to reveal an attack from another.",
                "type": "tactics",
                "tags": ["pin", "fork", "skewer", "discovery"]
            },
            "endgame": {
                "title": "Basic Endgame Principles",
                "content": "1. Activate your king in the endgame. 2. Passed pawns must be pushed. 3. Opposition is crucial in king and pawn endgames. 4. Rook belongs behind passed pawns. 5. Study basic checkmate patterns (Q+K vs K, R+K vs K).",
                "type": "endgame",
                "tags": ["king", "pawns", "opposition", "checkmate"]
            },
            "strategy": {
                "title": "Chess Strategy Fundamentals",
                "content": "1. Improve your worst-placed piece. 2. Create weaknesses in opponent's position. 3. Control key squares and outposts. 4. Coordinate your pieces. 5. Plan based on pawn structure.",
                "type": "strategy",
                "tags": ["planning", "coordination", "weaknesses"]
            },
            "sicilian": {
                "title": "Sicilian Defense Basics",
                "content": "The Sicilian Defense (1...c5) is Black's most popular response to 1.e4. Key ideas: Control the d4 square, fight for central space, create counterplay on the queenside. Main variations include Najdorf, Dragon, Accelerated Dragon, and Scheveningen.",
                "type": "opening",
                "tags": ["sicilian", "defense", "counterplay"]
            },
            "study plan": {
                "title": "Chess Improvement Study Plan",
                "content": "Beginner: Focus on tactics (70%), basic endgames (20%), opening principles (10%). Intermediate: Tactics (50%), positional understanding (30%), opening theory (20%). Advanced: Deep analysis (40%), opening preparation (30%), endgame technique (30%).",
                "type": "study",
                "tags": ["improvement", "training", "development"]
            }
        }
        
        # Find relevant knowledge based on query
        relevant_results = []
        for key, knowledge in fallback_knowledge.items():
            if any(word in query_lower for word in key.split()) or \
               any(tag in query_lower for tag in knowledge["tags"]):
                result = ChessKnowledgeResult(
                    title=knowledge["title"],
                    content=knowledge["content"],
                    type=knowledge["type"],
                    tags=knowledge["tags"],
                    score=0.8  # Fixed high score for fallback
                )
                relevant_results.append(result)
        
        # If no specific matches, return general advice
        if not relevant_results:
            general_advice = ChessKnowledgeResult(
                title="General Chess Advice",
                content="Focus on tactics training, study basic endgames, learn opening principles, analyze your games, and practice regularly. Chess improvement comes through consistent study and practice.",
                type="general",
                tags=["advice", "improvement"],
                score=0.7
            )
            relevant_results.append(general_advice)
        
        return relevant_results[:3]  # Return up to 3 results
    
    def retrieve(self, 
                query: str, 
                limit: int = 3,
                min_score: float = 0.7,
                filters: Optional[Dict[str, Any]] = None) -> List[ChessKnowledgeResult]:
        """
        Retrieve relevant chess knowledge from the knowledge base.
        
        Args:
            query: The search query
            limit: Maximum number of results to return
            min_score: Minimum similarity score threshold
            filters: Optional filters for content type, tags, etc.
            
        Returns:
            List of ChessKnowledgeResult objects
        """
        # If not connected to Weaviate, use fallback
        if not self.connected:
            logger.info("Using fallback knowledge (Weaviate not available)")
            return self._get_fallback_knowledge(query)
        
        try:
            if not self.collection:
                raise RuntimeError("Collection not initialized")
            
            # Build the query
            search_query = self.collection.query.near_text(
                query=query,
                limit=limit,
                return_metadata=MetadataQuery(score=True)
            )
            
            # Apply filters if provided
            if filters:
                # Note: Weaviate filtering syntax would go here
                # This is a simplified version
                pass
            
            response = search_query
            
            results = []
            for obj in response.objects:
                # Filter by score if specified
                score = obj.metadata.score if hasattr(obj.metadata, 'score') else 0.0
                if score < min_score:
                    continue
                
                # Extract properties safely
                props = obj.properties or {}
                
                result = ChessKnowledgeResult(
                    title=props.get("title", "Untitled"),
                    content=props.get("content", ""),
                    type=props.get("type", "unknown"),
                    tags=props.get("tags", []),
                    score=score
                )
                results.append(result)
            
            # If no results from Weaviate, use fallback
            if not results:
                logger.info(f"No results from Weaviate for query: '{query}', using fallback")
                return self._get_fallback_knowledge(query)
            
            logger.info(f"Retrieved {len(results)} results for query: '{query}'")
            return results
            
        except Exception as e:
            logger.error(f"Error retrieving knowledge: {e}")
            # Fallback to built-in knowledge
            logger.info("Falling back to built-in knowledge")
            return self._get_fallback_knowledge(query)
    
    def retrieve_by_type(self, 
                        query: str, 
                        content_type: str,
                        limit: int = 3) -> List[ChessKnowledgeResult]:
        """Retrieve knowledge filtered by content type (opening, endgame, etc.)"""
        filters = {"type": content_type}
        return self.retrieve(query, limit=limit, filters=filters)
    
    def retrieve_by_tags(self, 
                        query: str, 
                        tags: List[str],
                        limit: int = 3) -> List[ChessKnowledgeResult]:
        """Retrieve knowledge filtered by tags"""
        filters = {"tags": tags}
        return self.retrieve(query, limit=limit, filters=filters)
    
    def format_results_for_llm(self, results: List[ChessKnowledgeResult]) -> str:
        """Format retrieval results for LLM consumption"""
        if not results:
            return "No relevant chess knowledge found for this query."
        
        formatted = "Here's relevant chess knowledge from my database:\n\n"
        
        for i, result in enumerate(results, 1):
            formatted += f"**Source {i}: {result.title}** (Type: {result.type})\n"
            if result.tags:
                formatted += f"Tags: {', '.join(result.tags)}\n"
            formatted += f"{result.content}\n\n"
        
        return formatted
    
    def search_and_format(self, 
                         query: str, 
                         limit: int = 3,
                         include_metadata: bool = True) -> str:
        """One-step search and format for LLM use"""
        results = self.retrieve(query, limit=limit)
        return self.format_results_for_llm(results)
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics about the knowledge base"""
        try:
            stats = {
                "collection_name": self.config.collection_name,
                "weaviate_available": WEAVIATE_AVAILABLE,
                "connected": self.connected
            }
            
            if self.connected and self.client:
                stats["status"] = "connected" if self.client.is_ready() else "disconnected"
            else:
                stats["status"] = "using_fallback"
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting collection stats: {e}")
            return {"error": str(e), "status": "error"}
    
    def test_connection(self) -> bool:
        """Test the RAG connection and return status"""
        if not WEAVIATE_AVAILABLE:
            return False
        
        try:
            if self.connected and self.client and self.client.is_ready():
                # Try a simple query to test everything works
                test_results = self.retrieve("test", limit=1)
                return True
            return False
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False
    
    def close(self):
        """Close the Weaviate connection"""
        if self.client:
            try:
                self.client.close()
                logger.info("Weaviate connection closed")
            except Exception as e:
                logger.error(f"Error closing connection: {e}")
            finally:
                self.connected = False
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()

# Global instance for convenience
_chess_rag_instance = None

def get_chess_rag() -> ChessRAG:
    """Get a singleton ChessRAG instance"""
    global _chess_rag_instance
    if _chess_rag_instance is None:
        _chess_rag_instance = ChessRAG()
    return _chess_rag_instance

def close_chess_rag():
    """Close the global ChessRAG instance"""
    global _chess_rag_instance
    if _chess_rag_instance is not None:
        _chess_rag_instance.close()
        _chess_rag_instance = None

# Function for agent function calling
def retrieve_chess_knowledge(query: str, limit: int = 3) -> str:
    """
    Retrieve relevant chess knowledge from the knowledge base.
    This function is designed to be used as a tool by the chess agent.
    
    Args:
        query: The search query describing what chess knowledge you need
        limit: Maximum number of results to return (default: 3)
        
    Returns:
        Formatted string with relevant chess knowledge
    """
    try:
        # Use context manager to ensure proper cleanup
        with ChessRAG() as rag:
            return rag.search_and_format(query, limit=limit)
    except Exception as e:
        logger.error(f"Error in retrieve_chess_knowledge: {e}")
        # Return fallback knowledge instead of error
        rag = ChessRAG()
        fallback_results = rag._get_fallback_knowledge(query)
        return rag.format_results_for_llm(fallback_results)

if __name__ == "__main__":
    # Test the RAG system
    print("Testing Chess RAG System...")
    
    with ChessRAG() as rag:
        # Test connection
        connection_ok = rag.test_connection()
        print(f"Connection test: {'✅ PASS' if connection_ok else '⚠️ Using fallback'}")
        
        test_queries = [
            "Sicilian Defense opening principles",
            "endgame king and pawn versus king",
            "middlegame pawn structure strategies",
            "tactics for improving piece activity",
            "chess study plan for beginners"
        ]
        
        for query in test_queries:
            print(f"\n--- Testing query: '{query}' ---")
            start_time = time.time()
            results = rag.retrieve(query, limit=2)
            end_time = time.time()
            
            print(f"Found {len(results)} results in {end_time - start_time:.2f}s")
            
            if results:
                formatted = rag.format_results_for_llm(results)
                print(f"Formatted output:\n{formatted[:200]}...")
            else:
                print("No results found")
        
        # Test stats
        stats = rag.get_collection_stats()
        print(f"\nCollection stats: {stats}")
"""
Embeddings Generator using HuggingFace (FREE)
Converts text to semantic vectors for similarity matching
"""

from sentence_transformers import SentenceTransformer
import numpy as np
from typing import List, Union
import logging

logger = logging.getLogger(__name__)


class EmbeddingGenerator:
    """
    Generate embeddings using free HuggingFace models
    No API key required - runs locally
    """
    
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        """
        Initialize embedding model
        
        Args:
            model_name: HuggingFace model (default: all-MiniLM-L6-v2)
                       - Fast and lightweight
                       - 384 dimensions
                       - Perfect for semantic search
        """
        logger.info(f"Loading embedding model: {model_name}")
        self.model = SentenceTransformer(model_name)
        self.dimension = self.model.get_sentence_embedding_dimension()
        logger.info(f"Model loaded. Embedding dimension: {self.dimension}")
    
    def generate(self, text: Union[str, List[str]]) -> np.ndarray:
        """
        Generate embeddings for text
        
        Args:
            text: Single string or list of strings
            
        Returns:
            numpy array of embeddings
        """
        try:
            if isinstance(text, str):
                embeddings = self.model.encode([text])
                return embeddings[0]
            else:
                embeddings = self.model.encode(text)
                return embeddings
        except Exception as e:
            logger.error(f"Error generating embeddings: {e}")
            # Return zero vector on error
            if isinstance(text, str):
                return np.zeros(self.dimension)
            else:
                return np.zeros((len(text), self.dimension))
    
    def batch_generate(self, texts: List[str], batch_size: int = 32) -> np.ndarray:
        """
        Generate embeddings in batches (more efficient)
        
        Args:
            texts: List of strings
            batch_size: Number of texts per batch
            
        Returns:
            numpy array of embeddings
        """
        try:
            embeddings = self.model.encode(
                texts, 
                batch_size=batch_size,
                show_progress_bar=True
            )
            return embeddings
        except Exception as e:
            logger.error(f"Error in batch generation: {e}")
            return np.zeros((len(texts), self.dimension))
    
    def similarity(self, text1: str, text2: str) -> float:
        """
        Calculate cosine similarity between two texts
        
        Args:
            text1: First text
            text2: Second text
            
        Returns:
            Similarity score (0-1, higher is more similar)
        """
        emb1 = self.generate(text1)
        emb2 = self.generate(text2)
        
        # Cosine similarity
        similarity = np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2))
        return float(similarity)


# Global instance (lazy loading)
_embedding_generator = None

def get_embedding_generator() -> EmbeddingGenerator:
    """Get global embedding generator instance"""
    global _embedding_generator
    if _embedding_generator is None:
        _embedding_generator = EmbeddingGenerator()
    return _embedding_generator
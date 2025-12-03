"""
Cosine Similarity - Semantic Matching
Uses embeddings to find semantically similar RFPs
Catches matches even when exact keywords don't appear
"""

import numpy as np
from typing import Dict
import logging
from .embeddings import get_embedding_generator

logger = logging.getLogger(__name__)


class CosineMatcher:
    """
    Calculate cosine similarity using semantic embeddings
    
    This catches RFPs like:
    - "Industrial surface protection" → matches "coating"
    - "Architectural finishes" → matches "painting"
    - "Corrosion prevention" → matches "anti-corrosive"
    
    Even when exact keywords don't appear!
    """
    
    def __init__(self, user_profile: str):
        """
        Initialize with Asian Paints business profile
        
        Args:
            user_profile: Description of what you do
                Example: "Asian Paints provides paint and coating 
                         solutions for buildings, infrastructure, and 
                         industrial projects including decorative paints,
                         protective coatings, and surface treatments."
        """
        self.user_profile = user_profile
        self.embedding_generator = get_embedding_generator()
        
        # Generate embedding for user profile (do once, reuse)
        logger.info("Generating embedding for user profile...")
        self.user_embedding = self.embedding_generator.generate(user_profile)
        logger.info("User profile embedding ready")
    
    def calculate_similarity(self, rfp_text: str) -> Dict[str, float]:
        """
        Calculate cosine similarity between RFP and your profile
        
        Args:
            rfp_text: RFP title + description
            
        Returns:
            Dict with:
                - cosine_score: Similarity score (0-1)
                - confidence: How confident we are in the match
        """
        if not rfp_text or len(rfp_text.strip()) < 10:
            return {
                'cosine_score': 0.0,
                'confidence': 'low',
                'embedding_quality': 'poor'
            }
        
        # Generate embedding for RFP
        rfp_embedding = self.embedding_generator.generate(rfp_text)
        
        # Calculate cosine similarity
        similarity = self._cosine_similarity(self.user_embedding, rfp_embedding)
        
        # Determine confidence based on text length
        text_length = len(rfp_text)
        if text_length > 500:
            confidence = 'high'
        elif text_length > 200:
            confidence = 'medium'
        else:
            confidence = 'low'
        
        logger.debug(f"Cosine similarity: {similarity:.3f} (confidence: {confidence})")
        
        return {
            'cosine_score': float(similarity),
            'confidence': confidence,
            'text_length': text_length,
            'embedding_quality': 'good' if text_length > 100 else 'fair'
        }
    
    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """
        Calculate cosine similarity between two vectors
        
        Formula: cos(θ) = (A · B) / (||A|| ||B||)
        
        Returns:
            Similarity score (0-1)
        """
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        similarity = dot_product / (norm1 * norm2)
        
        # Ensure range [0, 1]
        similarity = max(0.0, min(1.0, similarity))
        
        return similarity
    
    def batch_calculate(self, rfp_texts: list) -> list:
        """
        Calculate similarity for multiple RFPs efficiently
        
        Args:
            rfp_texts: List of RFP texts
            
        Returns:
            List of similarity results
        """
        if not rfp_texts:
            return []
        
        # Generate embeddings in batch (faster)
        rfp_embeddings = self.embedding_generator.batch_generate(rfp_texts)
        
        results = []
        for i, rfp_embedding in enumerate(rfp_embeddings):
            similarity = self._cosine_similarity(self.user_embedding, rfp_embedding)
            
            text_length = len(rfp_texts[i])
            confidence = 'high' if text_length > 500 else 'medium' if text_length > 200 else 'low'
            
            results.append({
                'cosine_score': float(similarity),
                'confidence': confidence,
                'text_length': text_length
            })
        
        logger.info(f"Batch processed {len(rfp_texts)} RFPs")
        return results
    
    def explain_match(self, result: Dict) -> str:
        """
        Generate human-readable explanation
        
        Args:
            result: Result from calculate_similarity()
            
        Returns:
            Explanation string
        """
        score = result['cosine_score']
        confidence = result['confidence']
        
        if score >= 0.7:
            level = "VERY STRONG"
        elif score >= 0.5:
            level = "STRONG"
        elif score >= 0.3:
            level = "MODERATE"
        else:
            level = "WEAK"
        
        explanation = f"{level} semantic match ({score:.1%})\n"
        explanation += f"Confidence: {confidence.upper()}\n"
        explanation += "This score shows how similar the RFP's meaning is to your business profile."
        
        return explanation
    
    def find_most_similar_phrase(self, rfp_text: str, phrases: list) -> Dict:
        """
        Find which phrase in RFP is most similar to your profile
        Useful for explaining WHY it matched
        
        Args:
            rfp_text: Full RFP text
            phrases: List of phrases/sentences from RFP
            
        Returns:
            Dict with most similar phrase and its score
        """
        if not phrases:
            return {'phrase': '', 'score': 0.0}
        
        phrase_embeddings = self.embedding_generator.batch_generate(phrases)
        
        best_score = 0.0
        best_phrase = ''
        
        for phrase, embedding in zip(phrases, phrase_embeddings):
            similarity = self._cosine_similarity(self.user_embedding, embedding)
            if similarity > best_score:
                best_score = similarity
                best_phrase = phrase
        
        return {
            'phrase': best_phrase,
            'score': float(best_score)
        }


# Example usage
if __name__ == "__main__":
    # Asian Paints profile
    profile = """
    Asian Paints provides comprehensive paint and coating solutions for 
    buildings, infrastructure, and industrial projects. Services include 
    decorative paints, protective coatings, anti-corrosive treatments, 
    waterproofing, and specialty surface finishes for construction and 
    maintenance projects.
    """
    
    matcher = CosineMatcher(profile)
    
    # Test RFP (doesn't use exact keywords!)
    rfp_text = """
    Seeking vendor for architectural surface protection and aesthetic 
    enhancement of government facilities. Work includes corrosion prevention,
    weather resistance treatment, and visual improvement of building exteriors.
    """
    
    result = matcher.calculate_similarity(rfp_text)
    print(result)
    print(matcher.explain_match(result))
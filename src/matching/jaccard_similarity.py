
"""
Jaccard Similarity - Keyword Overlap Matching
Measures how many keywords overlap between RFP and your standards
"""

from typing import List, Set, Dict
import re
import logging

logger = logging.getLogger(__name__)


class JaccardMatcher:
    """
    Calculate Jaccard similarity for keyword matching
    
    Formula: |A ∩ B| / |A ∪ B|
    - Intersection / Union
    - Range: 0 to 1 (0% to 100% match)
    """
    
    def __init__(self, user_keywords: Dict[str, List[str]]):
        """
        Initialize with Asian Paints keywords
        
        Args:
            user_keywords: Dict with keys:
                - 'primary': Main keywords (paint, coating, etc.)
                - 'secondary': Related keywords (construction, etc.)
                - 'technical': Technical terms (epoxy, etc.)
        """
        self.primary_keywords = set(k.lower() for k in user_keywords.get('primary', []))
        self.secondary_keywords = set(k.lower() for k in user_keywords.get('secondary', []))
        self.technical_keywords = set(k.lower() for k in user_keywords.get('technical', []))
        
        # All keywords combined
        self.all_keywords = self.primary_keywords | self.secondary_keywords | self.technical_keywords
        
        logger.info(f"Jaccard matcher initialized with {len(self.all_keywords)} keywords")
    
    def extract_keywords(self, text: str) -> Set[str]:
        """
        Extract keywords from text
        
        Args:
            text: RFP text (title + description)
            
        Returns:
            Set of keywords found
        """
        if not text:
            return set()
        
        # Lowercase and clean
        text = text.lower()
        
        # Remove special characters, keep alphanumeric and spaces
        text = re.sub(r'[^a-z0-9\s-]', ' ', text)
        
        # Split into words
        words = text.split()
        
        # Also check for multi-word phrases
        phrases = []
        for i in range(len(words) - 1):
            phrases.append(f"{words[i]} {words[i+1]}")
        
        # Check for three-word phrases
        for i in range(len(words) - 2):
            phrases.append(f"{words[i]} {words[i+1]} {words[i+2]}")
        
        # Combine words and phrases
        all_terms = set(words) | set(phrases)
        
        # Find matches with our keywords
        matched_keywords = all_terms & self.all_keywords
        
        return matched_keywords
    
    def calculate_similarity(self, rfp_text: str) -> Dict[str, float]:
        """
        Calculate Jaccard similarity
        
        Args:
            rfp_text: RFP title + description
            
        Returns:
            Dict with:
                - jaccard_score: Overall score (0-1)
                - matched_keywords: Keywords that matched
                - primary_match: Match with primary keywords
                - secondary_match: Match with secondary keywords
                - technical_match: Match with technical keywords
        """
        # Extract keywords from RFP
        rfp_keywords = self.extract_keywords(rfp_text)
        
        if not rfp_keywords:
            return {
                'jaccard_score': 0.0,
                'matched_keywords': [],
                'primary_match': 0.0,
                'secondary_match': 0.0,
                'technical_match': 0.0
            }
        
        # Overall Jaccard similarity
        intersection = rfp_keywords & self.all_keywords
        union = rfp_keywords | self.all_keywords
        jaccard_score = len(intersection) / len(union) if union else 0.0
        
        # Primary keywords match
        primary_matched = rfp_keywords & self.primary_keywords
        primary_score = len(primary_matched) / len(self.primary_keywords) if self.primary_keywords else 0.0
        
        # Secondary keywords match
        secondary_matched = rfp_keywords & self.secondary_keywords
        secondary_score = len(secondary_matched) / len(self.secondary_keywords) if self.secondary_keywords else 0.0
        
        # Technical keywords match
        technical_matched = rfp_keywords & self.technical_keywords
        technical_score = len(technical_matched) / len(self.technical_keywords) if self.technical_keywords else 0.0
        
        # Weighted score (primary keywords are more important)
        weighted_score = (
            primary_score * 0.5 +      # 50% weight
            secondary_score * 0.3 +    # 30% weight
            technical_score * 0.2      # 20% weight
        )
        
        logger.debug(f"Jaccard similarity: {jaccard_score:.2f}, Weighted: {weighted_score:.2f}")
        logger.debug(f"Matched keywords: {intersection}")
        
        return {
            'jaccard_score': weighted_score,  # Use weighted score as main score
            'raw_jaccard': jaccard_score,
            'matched_keywords': list(intersection),
            'primary_match': primary_score,
            'secondary_match': secondary_score,
            'technical_match': technical_score,
            'match_count': len(intersection),
            'total_rfp_keywords': len(rfp_keywords)
        }
    
    def explain_match(self, result: Dict) -> str:
        """
        Generate human-readable explanation
        
        Args:
            result: Result from calculate_similarity()
            
        Returns:
            Explanation string
        """
        score = result['jaccard_score']
        matched = result['matched_keywords']
        
        if score >= 0.6:
            level = "EXCELLENT"
        elif score >= 0.4:
            level = "GOOD"
        elif score >= 0.25:
            level = "MODERATE"
        else:
            level = "WEAK"
        
        explanation = f"{level} keyword match ({score:.1%})\n"
        explanation += f"Matched keywords: {', '.join(matched[:10])}"  # Show first 10
        
        if len(matched) > 10:
            explanation += f" and {len(matched) - 10} more"
        
        return explanation


# Example usage
if __name__ == "__main__":
    # Asian Paints keywords
    keywords = {
        'primary': ['paint', 'coating', 'painting', 'surface treatment', 'finishing'],
        'secondary': ['construction', 'building', 'infrastructure', 'renovation'],
        'technical': ['epoxy', 'polyurethane', 'anti-corrosive', 'primer', 'enamel']
    }
    
    matcher = JaccardMatcher(keywords)
    
    # Test RFP
    rfp_text = """
    Request for Proposal: Building Exterior Painting and Coating Services
    The Department of Transportation requires exterior painting and protective 
    coating services for bridge infrastructure. Must use anti-corrosive primer 
    and weather-resistant epoxy coating. Project includes surface preparation, 
    painting, and finishing work.
    """
    
    result = matcher.calculate_similarity(rfp_text)
    print(result)
    print(matcher.explain_match(result))
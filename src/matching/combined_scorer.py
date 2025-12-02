import logging
from typing import Dict, Any
import json
from .jaccard_similarity import JaccardMatcher
from .cosine_similarity import CosineMatcher

logger = logging.getLogger(__name__)


class RFPCombinedScorer:
    """
    Master scoring engine that combines all algorithms + AI judgment
    """
    
    def __init__(self, config: Dict[str, Any], ollama_client):
        """
        Initialize all matchers
        
        Args:
            config: Configuration with:
                - keywords: Asian Paints keywords
                - profile: Business profile description
                - thresholds: Score thresholds
            ollama_client: Ollama client for LLM judgment
        """
        self.config = config
        self.ollama_client = ollama_client
        
        # Initialize matchers
        logger.info("Initializing matching algorithms...")
        
        self.jaccard_matcher = JaccardMatcher(config['keywords'])
        self.cosine_matcher = CosineMatcher(config['profile'])
        
        # Thresholds
        self.jaccard_threshold = config.get('jaccard_threshold', 0.25)
        self.cosine_threshold = config.get('cosine_threshold', 0.50)
        self.overall_threshold = config.get('overall_threshold', 0.45)
        
        # Weights for combined score
        self.weights = {
            'jaccard': 0.25,   # 25% - Keyword match
            'cosine': 0.25,    # 25% - Semantic match
            'tfidf': 0.15,     # 15% - Weighted terms
            'ner': 0.10,       # 10% - Entity match
            'llm': 0.25        # 25% - AI judgment (most important!)
        }
        
        logger.info("✅ All matchers initialized")
    
    async def score_rfp(self, rfp_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Score an RFP using ALL algorithms + LLM
        
        Args:
            rfp_data: Dict with:
                - title: RFP title
                - description: RFP description
                - budget: Budget info
                - location: Location info
                - deadline: Deadline date
                
        Returns:
            Dict with all scores and final verdict
        """
        logger.info(f"Scoring RFP: {rfp_data.get('title', 'Unknown')[:50]}...")
        
        # Combine title + description for analysis
        full_text = f"{rfp_data.get('title', '')} {rfp_data.get('description', '')}"
        
        scores = {}
        
        # 1. Jaccard Similarity (keyword overlap)
        try:
            jaccard_result = self.jaccard_matcher.calculate_similarity(full_text)
            scores['jaccard'] = jaccard_result['jaccard_score']
            scores['jaccard_details'] = jaccard_result
            logger.debug(f"Jaccard: {scores['jaccard']:.2f}")
        except Exception as e:
            logger.error(f"Jaccard error: {e}")
            scores['jaccard'] = 0.0
            scores['jaccard_details'] = {}
        
        # 2. Cosine Similarity (semantic)
        try:
            cosine_result = self.cosine_matcher.calculate_similarity(full_text)
            scores['cosine'] = cosine_result['cosine_score']
            scores['cosine_details'] = cosine_result
            logger.debug(f"Cosine: {scores['cosine']:.2f}")
        except Exception as e:
            logger.error(f"Cosine error: {e}")
            scores['cosine'] = 0.0
            scores['cosine_details'] = {}
        
        # 3. TF-IDF Scoring (weighted keywords)
        # TODO: Implement in tfidf_scorer.py
        scores['tfidf'] = 0.0  # Placeholder
        
        # 4. NER Scoring (entity matching)
        # TODO: Implement in ner_extractor.py
        scores['ner'] = 0.0  # Placeholder
        
        # 5. LLM Judgment (Ollama - The Smart Layer!)
        try:
            llm_result = await self._llm_judgment(rfp_data, scores)
            scores['llm'] = llm_result['score']
            scores['llm_reasoning'] = llm_result['reasoning']
            logger.debug(f"LLM: {scores['llm']:.2f}")
        except Exception as e:
            logger.error(f"LLM error: {e}")
            scores['llm'] = 0.0
            scores['llm_reasoning'] = "LLM evaluation failed"
        
        # 6. Calculate weighted combined score
        overall_score = self._calculate_overall_score(scores)
        
        # 7. Generate verdict
        verdict = self._generate_verdict(overall_score, scores)
        
        result = {
            'overall_score': overall_score,
            'scores': scores,
            'verdict': verdict,
            'passes_threshold': overall_score >= self.overall_threshold,
            'recommendation': self._generate_recommendation(overall_score, scores)
        }
        
        logger.info(f"✅ Final score: {overall_score:.2%} - {verdict}")
        
        return result
    
    async def _llm_judgment(self, rfp_data: Dict, scores: Dict) -> Dict:
        """
        Let Ollama make the final intelligent judgment
        This is where AI sees patterns algorithms might miss!
        """
        prompt = f"""You are an expert at evaluating RFPs for Asian Paints, a leading paint and coating company.

RFP DETAILS:
Title: {rfp_data.get('title', 'N/A')}
Description: {rfp_data.get('description', 'N/A')[:500]}
Budget: {rfp_data.get('budget', 'Not specified')}
Location: {rfp_data.get('location', 'Not specified')}
Deadline: {rfp_data.get('deadline', 'Not specified')}

ALGORITHM SCORES:
- Keyword Match (Jaccard): {scores.get('jaccard', 0):.1%}
- Semantic Match (Cosine): {scores.get('cosine', 0):.1%}

ASIAN PAINTS FOCUS:
- Paint and coating projects
- Building/infrastructure work
- Industrial coatings
- Protective/decorative finishes
- Budget range: $10K - $10M

EVALUATE:
Does this RFP match Asian Paints' business? Consider:
1. Is it paint/coating related?
2. Is the scope appropriate?
3. Are there any red flags?
4. Would Asian Paints have competitive advantage?

Respond ONLY in JSON format:
{{
  "score": 0.75,
  "reasoning": "Brief explanation",
  "confidence": "high/medium/low",
  "key_factors": ["factor1", "factor2"]
}}"""

        try:
            response = await self.ollama_client.generate(prompt)
            
            # Parse JSON response
            # Ollama might wrap in markdown, so extract JSON
            response_text = response.strip()
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0]
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0]
            
            result = json.loads(response_text)
            
            return {
                'score': float(result.get('score', 0.5)),
                'reasoning': result.get('reasoning', ''),
                'confidence': result.get('confidence', 'medium'),
                'key_factors': result.get('key_factors', [])
            }
            
        except Exception as e:
            logger.error(f"LLM judgment parsing error: {e}")
            # Fallback: use average of other scores
            avg_score = (scores.get('jaccard', 0) + scores.get('cosine', 0)) / 2
            return {
                'score': avg_score,
                'reasoning': 'Based on algorithm scores (LLM unavailable)',
                'confidence': 'medium',
                'key_factors': []
            }
    
    def _calculate_overall_score(self, scores: Dict) -> float:
        """
        Calculate weighted combined score
        """
        overall = (
            scores.get('jaccard', 0) * self.weights['jaccard'] +
            scores.get('cosine', 0) * self.weights['cosine'] +
            scores.get('tfidf', 0) * self.weights['tfidf'] +
            scores.get('ner', 0) * self.weights['ner'] +
            scores.get('llm', 0) * self.weights['llm']
        )
        
        return round(overall, 3)
    
    def _generate_verdict(self, overall_score: float, scores: Dict) -> str:
        """
        Generate verdict based on score
        """
        if overall_score >= 0.70:
            return "EXCELLENT MATCH"
        elif overall_score >= 0.55:
            return "GOOD MATCH"
        elif overall_score >= self.overall_threshold:
            return "MODERATE MATCH"
        elif overall_score >= 0.30:
            return "WEAK MATCH"
        else:
            return "NOT A MATCH"
    
    def _generate_recommendation(self, overall_score: float, scores: Dict) -> str:
        """
        Generate actionable recommendation
        """
        if overall_score >= 0.70:
            return "🎯 HIGH PRIORITY - Review immediately"
        elif overall_score >= 0.55:
            return "✅ GOOD OPPORTUNITY - Worth reviewing"
        elif overall_score >= self.overall_threshold:
            return "⚠️ POTENTIAL FIT - Review if capacity allows"
        elif overall_score >= 0.30:
            return "🔍 MARGINAL FIT - Low priority"
        else:
            return "❌ SKIP - Not aligned with business"
    
    def explain_scoring(self, result: Dict) -> str:
        """
        Generate detailed human-readable explanation
        """
        explanation = f"""
RFP MATCHING ANALYSIS
{'='*50}

OVERALL SCORE: {result['overall_score']:.1%}
VERDICT: {result['verdict']}
RECOMMENDATION: {result['recommendation']}

DETAILED SCORES:
- Keyword Match (Jaccard): {result['scores'].get('jaccard', 0):.1%}
- Semantic Match (Cosine): {result['scores'].get('cosine', 0):.1%}
- TF-IDF Score: {result['scores'].get('tfidf', 0):.1%}
- Entity Match (NER): {result['scores'].get('ner', 0):.1%}
- AI Judgment (LLM): {result['scores'].get('llm', 0):.1%}

AI REASONING:
{result['scores'].get('llm_reasoning', 'N/A')}

MATCHED KEYWORDS:
{', '.join(result['scores'].get('jaccard_details', {}).get('matched_keywords', [])[:10])}

STATUS: {'✅ PASSES THRESHOLD' if result['passes_threshold'] else '❌ BELOW THRESHOLD'}
"""
        return explanation


# Example usage
if __name__ == "__main__":
    import asyncio
    
    # Mock Ollama client for testing
    class MockOllamaClient:
        async def generate(self, prompt):
            return '{"score": 0.82, "reasoning": "Strong match for paint work", "confidence": "high", "key_factors": ["paint", "coating"]}'
    
    config = {
        'keywords': {
            'primary': ['paint', 'coating'],
            'secondary': ['construction', 'building'],
            'technical': ['epoxy', 'primer']
        },
        'profile': "Asian Paints provides paint and coating solutions",
        'overall_threshold': 0.45
    }
    
    scorer = RFPCombinedScorer(config, MockOllamaClient())
    
    rfp = {
        'title': 'Building Exterior Painting Services',
        'description': 'Need paint and coating for government building exterior',
        'budget': '$50,000',
        'location': 'Delhi, India'
    }
    
    async def test():
        result = await scorer.score_rfp(rfp)
        print(scorer.explain_scoring(result))
    
    asyncio.run(test())
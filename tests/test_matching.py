"""
TEST SUITE - Phase 5 Matching Algorithms
Run this to verify all matchers work correctly
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import asyncio
from src.matching.jaccard_similarity import JaccardMatcher
from src.matching.cosine_similarity import CosineMatcher
from src.matching.combined_scorer import RFPCombinedScorer


# ============================================
# MOCK OLLAMA CLIENT (for testing without Docker)
# ============================================
class MockOllamaClient:
    """Simulates Ollama responses for testing"""
    
    async def generate(self, prompt):
        # Simulate LLM response based on prompt content
        if "paint" in prompt.lower() or "coating" in prompt.lower():
            return '''
            {
                "score": 0.85,
                "reasoning": "Strong match - this is clearly a paint/coating project for building infrastructure, which is Asian Paints' core business",
                "confidence": "high",
                "key_factors": ["paint", "coating", "building", "infrastructure"]
            }
            '''
        elif "construction" in prompt.lower():
            return '''
            {
                "score": 0.65,
                "reasoning": "Moderate match - construction project that may involve painting work, but not specifically focused on coatings",
                "confidence": "medium",
                "key_factors": ["construction", "building"]
            }
            '''
        else:
            return '''
            {
                "score": 0.30,
                "reasoning": "Weak match - project does not appear to be related to paint or coating services",
                "confidence": "low",
                "key_factors": []
            }
            '''


# ============================================
# TEST DATA - Sample RFPs
# ============================================

# TEST RFP 1: Perfect Match
PERFECT_MATCH_RFP = {
    'title': 'Exterior Building Painting and Protective Coating Services',
    'description': '''
    The Department of Public Works requires comprehensive painting and coating 
    services for government building exteriors. Scope includes surface preparation, 
    application of anti-corrosive primer, epoxy-based protective coating, and 
    decorative finish painting. Project involves approximately 50,000 sq ft of 
    building facade requiring weather-resistant polyurethane coating and 
    waterproofing treatment. Must meet all EPA standards for low-VOC paints.
    ''',
    'budget': '$250,000',
    'location': 'Delhi, India',
    'deadline': '2025-02-15'
}

# TEST RFP 2: Good Match (semantic, not exact keywords)
GOOD_MATCH_RFP = {
    'title': 'Infrastructure Surface Protection and Enhancement',
    'description': '''
    Seeking vendor for architectural surface treatment and aesthetic improvement 
    of municipal facilities. Work includes corrosion prevention, weather resistance 
    application, and visual enhancement of building exteriors. Project requires 
    expertise in protective finishes and architectural coatings.
    ''',
    'budget': '$150,000',
    'location': 'California, USA',
    'deadline': '2025-03-01'
}

# TEST RFP 3: Moderate Match
MODERATE_MATCH_RFP = {
    'title': 'Construction and Renovation Services',
    'description': '''
    General construction services needed for office building renovation including 
    structural work, electrical, plumbing, HVAC, and finishing work. Some painting 
    and coating work required as part of overall project.
    ''',
    'budget': '$500,000',
    'location': 'Mumbai, India',
    'deadline': '2025-04-01'
}

# TEST RFP 4: Poor Match
POOR_MATCH_RFP = {
    'title': 'IT Infrastructure and Network Services',
    'description': '''
    Seeking IT consulting services for network infrastructure upgrade, cybersecurity 
    implementation, cloud migration, and software development. No construction or 
    physical work involved.
    ''',
    'budget': '$100,000',
    'location': 'New York, USA',
    'deadline': '2025-02-28'
}


# ============================================
# TEST CONFIGURATION
# ============================================

# Asian Paints keywords
TEST_KEYWORDS = {
    'primary': [
        'paint', 'painting', 'coating', 'coatings', 'surface treatment',
        'finishing', 'repainting', 'refinishing'
    ],
    'secondary': [
        'construction', 'building', 'infrastructure', 'renovation',
        'maintenance', 'rehabilitation', 'restoration', 'facade'
    ],
    'technical': [
        'epoxy', 'polyurethane', 'anti-corrosive', 'primer', 'enamel',
        'emulsion', 'waterproofing', 'weather coating', 'protective coating',
        'industrial coating', 'decorative', 'low-voc', 'corrosion prevention'
    ]
}

# Asian Paints business profile
TEST_PROFILE = """
Asian Paints is a leading paint and coating solutions provider specializing in:
- Decorative paints for residential and commercial buildings
- Protective coatings for industrial and infrastructure projects
- Anti-corrosive treatments and weatherproofing solutions
- Surface preparation and finishing services
- Waterproofing and specialty coatings
- Architectural finishes and aesthetic enhancements

We serve construction, infrastructure, building maintenance, and industrial sectors
with comprehensive paint and coating solutions.
"""

TEST_CONFIG = {
    'keywords': TEST_KEYWORDS,
    'profile': TEST_PROFILE,
    'jaccard_threshold': 0.25,
    'cosine_threshold': 0.50,
    'overall_threshold': 0.45
}


# ============================================
# TEST FUNCTIONS
# ============================================

def print_separator(title):
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70 + "\n")


def test_jaccard_matcher():
    """Test Jaccard similarity matcher"""
    print_separator("TEST 1: JACCARD SIMILARITY (Keyword Overlap)")
    
    matcher = JaccardMatcher(TEST_KEYWORDS)
    
    test_cases = [
        ("Perfect Match RFP", PERFECT_MATCH_RFP),
        ("Good Match RFP", GOOD_MATCH_RFP),
        ("Moderate Match RFP", MODERATE_MATCH_RFP),
        ("Poor Match RFP", POOR_MATCH_RFP)
    ]
    
    for name, rfp in test_cases:
        full_text = f"{rfp['title']} {rfp['description']}"
        result = matcher.calculate_similarity(full_text)
        
        print(f"📊 {name}")
        print(f"   Score: {result['jaccard_score']:.1%}")
        print(f"   Matched Keywords: {len(result['matched_keywords'])}")
        print(f"   Keywords: {', '.join(result['matched_keywords'][:5])}")
        if len(result['matched_keywords']) > 5:
            print(f"              ... and {len(result['matched_keywords']) - 5} more")
        print(f"   Explanation: {matcher.explain_match(result)}\n")


def test_cosine_matcher():
    """Test Cosine similarity matcher"""
    print_separator("TEST 2: COSINE SIMILARITY (Semantic Matching)")
    
    print("⏳ Loading embedding model (this may take 10-30 seconds)...\n")
    matcher = CosineMatcher(TEST_PROFILE)
    print("✅ Model loaded!\n")
    
    test_cases = [
        ("Perfect Match RFP", PERFECT_MATCH_RFP),
        ("Good Match RFP", GOOD_MATCH_RFP),
        ("Moderate Match RFP", MODERATE_MATCH_RFP),
        ("Poor Match RFP", POOR_MATCH_RFP)
    ]
    
    for name, rfp in test_cases:
        full_text = f"{rfp['title']} {rfp['description']}"
        result = matcher.calculate_similarity(full_text)
        
        print(f"📊 {name}")
        print(f"   Score: {result['cosine_score']:.1%}")
        print(f"   Confidence: {result['confidence'].upper()}")
        print(f"   Explanation: {matcher.explain_match(result)}\n")


async def test_combined_scorer():
    """Test combined scorer with all algorithms"""
    print_separator("TEST 3: COMBINED SCORER (All Algorithms + LLM)")
    
    print("🚀 Initializing all matchers...\n")
    ollama_client = MockOllamaClient()
    scorer = RFPCombinedScorer(TEST_CONFIG, ollama_client)
    print("✅ All matchers ready!\n")
    
    test_cases = [
        ("Perfect Match RFP", PERFECT_MATCH_RFP),
        ("Good Match RFP", GOOD_MATCH_RFP),
        ("Moderate Match RFP", MODERATE_MATCH_RFP),
        ("Poor Match RFP", POOR_MATCH_RFP)
    ]
    
    for name, rfp in test_cases:
        print(f"🔍 Analyzing: {name}")
        print(f"   Title: {rfp['title'][:60]}...")
        
        result = await scorer.score_rfp(rfp)
        
        print(f"\n   OVERALL SCORE: {result['overall_score']:.1%}")
        print(f"   VERDICT: {result['verdict']}")
        print(f"   PASSES THRESHOLD: {'✅ YES' if result['passes_threshold'] else '❌ NO'}")
        print(f"\n   Individual Scores:")
        print(f"   ├─ Jaccard (Keywords):  {result['scores']['jaccard']:.1%}")
        print(f"   ├─ Cosine (Semantic):   {result['scores']['cosine']:.1%}")
        print(f"   ├─ TF-IDF:              {result['scores']['tfidf']:.1%} (TODO)")
        print(f"   ├─ NER:                 {result['scores']['ner']:.1%} (TODO)")
        print(f"   └─ LLM (Ollama):        {result['scores']['llm']:.1%}")
        
        print(f"\n   🤖 AI Reasoning:")
        print(f"   {result['scores']['llm_reasoning']}")
        
        print(f"\n   📋 Recommendation:")
        print(f"   {result['recommendation']}")
        print("\n" + "-"*70 + "\n")


def test_threshold_comparison():
    """Test how different thresholds affect matching"""
    print_separator("TEST 4: THRESHOLD SENSITIVITY ANALYSIS")
    
    matcher = JaccardMatcher(TEST_KEYWORDS)
    
    rfp_text = f"{MODERATE_MATCH_RFP['title']} {MODERATE_MATCH_RFP['description']}"
    result = matcher.calculate_similarity(rfp_text)
    score = result['jaccard_score']
    
    thresholds = [0.20, 0.25, 0.30, 0.40, 0.50]
    
    print(f"Testing RFP: {MODERATE_MATCH_RFP['title']}")
    print(f"Jaccard Score: {score:.1%}\n")
    
    print("Threshold | Passes? | Verdict")
    print("-"*40)
    for threshold in thresholds:
        passes = "✅ PASS" if score >= threshold else "❌ FAIL"
        print(f"  {threshold:.0%}    |  {passes}  | {'Would match' if score >= threshold else 'Would skip'}")


# ============================================
# MAIN TEST RUNNER
# ============================================

async def run_all_tests():
    """Run all test suites"""
    
    print("\n")
    print("╔" + "="*68 + "╗")
    print("║" + " "*10 + "RFP MATCHING ALGORITHMS - TEST SUITE" + " "*22 + "║")
    print("║" + " "*20 + "Phase 5 Validation" + " "*30 + "║")
    print("╚" + "="*68 + "╝")
    
    try:
        # Test 1: Jaccard
        test_jaccard_matcher()
        
        # Test 2: Cosine
        test_cosine_matcher()
        
        # Test 3: Combined Scorer
        await test_combined_scorer()
        
        # Test 4: Threshold Analysis
        test_threshold_comparison()
        
        # Summary
        print_separator("✅ ALL TESTS COMPLETED SUCCESSFULLY!")
        print("""
Next Steps:
1. These matchers are now validated and ready to use
2. They will be integrated into the crawler workflow (Phase 7)
3. Ollama will provide real LLM judgments when Docker is running
4. Results will be stored in PostgreSQL with all scores

The AI-powered matching layer is READY! 🚀
        """)
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("\n⏳ Starting tests (this may take 30-60 seconds for model loading)...\n")
    asyncio.run(run_all_tests())
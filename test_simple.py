#!/usr/bin/env python3
"""
Simple test script for CI Orchestrator functionality.
"""
import sys
import os
import asyncio
import json

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.models import CIOrchestratorInput, Brand, Competitor
from src.validators.json_validator import JSONValidator

async def test_json_validator():
    """Test JSON validator functionality."""
    print("Testing JSON Validator...")
    
    validator = JSONValidator()
    
    # Test with minimal valid output
    minimal_output = validator.create_minimal_valid_output("all")
    validation = validator.validate_output(minimal_output)
    
    print(f"Minimal output validation: {validation['valid']}")
    if validation['errors']:
        print(f"Errors: {validation['errors']}")
    if validation['warnings']:
        print(f"Warnings: {validation['warnings']}")
    
    print("JSON Validator test completed.\n")
    return validation['valid']

def test_models():
    """Test Pydantic models."""
    print("Testing Pydantic Models...")
    
    try:
        # Create test input
        test_input = CIOrchestratorInput(
            brand=Brand(name="Crooks & Castles", url="https://crooksncastles.com"),
            competitors=[
                Competitor(name="Paper Planes", url="https://paperplane.shop"),
                Competitor(name="Stüssy", url="https://stussy.com")
            ],
            mode="all",
            window_days=7
        )
        
        print(f"Created input model for brand: {test_input.brand.name}")
        print(f"Mode: {test_input.mode}")
        print(f"Competitors: {[c.name for c in test_input.competitors]}")
        print("Pydantic models test completed.\n")
        return True
        
    except Exception as e:
        print(f"Error testing models: {str(e)}")
        return False

def test_analyzers():
    """Test analyzer components."""
    print("Testing Analyzer Components...")
    
    try:
        from src.analyzers.influence_scorer import InfluenceScorer
        from src.analyzers.sentiment_analyzer import SentimentAnalyzer
        from src.analyzers.trend_analyzer import TrendAnalyzer
        from src.analyzers.peer_scorer import PeerScorer
        
        # Test influence scorer
        scorer = InfluenceScorer()
        test_creator = {
            'creator': 'test_creator',
            'engagement_rate': 0.05,
            'recent_content': 'streetwear fashion style',
            'hashtags': ['#streetwear', '#fashion'],
            'last_post_timestamp': '2024-09-16T12:00:00Z'
        }
        
        influence_score = scorer.calculate_influence_score(test_creator)
        print(f"Influence score calculated: {influence_score}")
        
        # Test sentiment analyzer
        sentiment_analyzer = SentimentAnalyzer()
        test_data = [
            {'text': 'This brand is amazing and the quality is fire!', 'platform': 'instagram'},
            {'text': 'Not worth the price, quality is poor', 'platform': 'twitter'}
        ]
        
        sentiment_result = sentiment_analyzer.analyze_sentiment(test_data)
        print(f"Sentiment analysis completed: {len(sentiment_result)} insights")
        
        print("Analyzer components test completed.\n")
        return True
        
    except Exception as e:
        print(f"Error testing analyzers: {str(e)}")
        return False

async def run_all_tests():
    """Run all tests."""
    print("=== CI Orchestrator Test Suite ===\n")
    
    results = []
    
    # Test models
    results.append(test_models())
    
    # Test JSON validator
    results.append(await test_json_validator())
    
    # Test analyzers
    results.append(test_analyzers())
    
    # Summary
    passed = sum(results)
    total = len(results)
    
    print(f"=== Test Summary ===")
    print(f"Passed: {passed}/{total}")
    print(f"Success rate: {passed/total*100:.1f}%")
    
    if passed == total:
        print("✅ All tests passed!")
    else:
        print("❌ Some tests failed.")
    
    return passed == total

if __name__ == "__main__":
    success = asyncio.run(run_all_tests())


#!/usr/bin/env python3
"""
Test script for brand-neutral CI Orchestrator functionality.
"""
import sys
import os
import asyncio
import json

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.models import CIOrchestratorInput, Brand, Competitor
from src.orchestrator import CIOrchestrator
from src.validators.json_validator import JSONValidator

async def test_brand_neutral_functionality():
    """Test CI Orchestrator with different brands to ensure brand neutrality."""
    print("=== Brand-Neutral CI Orchestrator Test ===\n")
    
    orchestrator = CIOrchestrator()
    validator = JSONValidator()
    
    # Test with different brands
    test_brands = [
        {
            "brand": Brand(
                name="Supreme",
                url="https://supremenewyork.com",
                meta={
                    "aliases": ["Supreme NY", "Supreme NYC"],
                    "hashtags": ["#supreme", "#supremeny"],
                    "priority_platforms": ["instagram.com", "tiktok.com"]
                }
            ),
            "competitors": [
                Competitor(name="BAPE", url="https://bape.com"),
                Competitor(name="Off-White", url="https://off---white.com")
            ]
        },
        {
            "brand": Brand(
                name="Nike",
                url="https://nike.com",
                meta={
                    "aliases": ["Nike Inc", "Just Do It"],
                    "hashtags": ["#nike", "#justdoit"],
                    "blocked_domains": ["fake-nike.com"]
                }
            ),
            "competitors": [
                Competitor(name="Adidas", url="https://adidas.com"),
                Competitor(name="Puma", url="https://puma.com")
            ]
        },
        {
            "brand": Brand(
                name="Stüssy",
                url="https://stussy.com"
                # No metadata - test default behavior
            ),
            "competitors": [
                Competitor(name="Carhartt WIP", url="https://carhartt-wip.com"),
                Competitor(name="Palace", url="https://palaceskateboards.com")
            ]
        }
    ]
    
    results = []
    
    for i, test_case in enumerate(test_brands, 1):
        print(f"Test {i}: Testing with brand '{test_case['brand'].name}'")
        
        try:
            # Create input
            test_input = CIOrchestratorInput(
                brand=test_case['brand'],
                competitors=test_case['competitors'],
                mode="all",
                window_days=7,
                max_results_per_section=5
            )
            
            # Run analysis
            result = await orchestrator.run_analysis(test_input)
            result_dict = result.dict()
            
            # Validate output
            validation = validator.validate_output(result_dict)
            
            print(f"  ✅ Analysis completed for {test_case['brand'].name}")
            print(f"  📊 Validation: {'PASS' if validation['valid'] else 'FAIL'}")
            
            if validation['errors']:
                print(f"  ❌ Errors: {validation['errors']}")
            
            if validation['warnings']:
                print(f"  ⚠️  Warnings: {len(validation['warnings'])} warnings")
            
            # Check for brand-specific content
            brand_specific_check = check_for_hardcoded_brands(result_dict, test_case['brand'].name)
            print(f"  🔍 Brand neutrality: {'PASS' if brand_specific_check else 'FAIL'}")
            
            results.append({
                'brand': test_case['brand'].name,
                'validation_passed': validation['valid'],
                'brand_neutral': brand_specific_check,
                'errors': validation['errors'],
                'warnings_count': len(validation['warnings'])
            })
            
        except Exception as e:
            print(f"  ❌ Error testing {test_case['brand'].name}: {str(e)}")
            results.append({
                'brand': test_case['brand'].name,
                'validation_passed': False,
                'brand_neutral': False,
                'errors': [str(e)],
                'warnings_count': 0
            })
        
        print()
    
    # Summary
    print("=== Test Summary ===")
    passed_validation = sum(1 for r in results if r['validation_passed'])
    passed_neutrality = sum(1 for r in results if r['brand_neutral'])
    total_tests = len(results)
    
    print(f"Validation Tests: {passed_validation}/{total_tests} passed")
    print(f"Brand Neutrality: {passed_neutrality}/{total_tests} passed")
    print(f"Overall Success: {min(passed_validation, passed_neutrality)}/{total_tests}")
    
    # Detailed results
    print("\n=== Detailed Results ===")
    for result in results:
        status = "✅" if result['validation_passed'] and result['brand_neutral'] else "❌"
        print(f"{status} {result['brand']}: Validation={result['validation_passed']}, Neutral={result['brand_neutral']}")
        if result['errors']:
            print(f"    Errors: {result['errors']}")
    
    return min(passed_validation, passed_neutrality) == total_tests

def check_for_hardcoded_brands(result_dict, current_brand):
    """Check if the result contains hardcoded brand names (other than the current brand)."""
    try:
        # Convert result to string for searching
        result_str = json.dumps(result_dict).lower()
        
        # List of brands that should NOT appear in results for other brands
        hardcoded_brands = [
            'crooks & castles', 'crooks', 'castles', 'crooksncastles',
            'paper planes', 'stüssy', 'huf', 'pleasures', 'carrots',
            'the hundreds', 'supreme', 'bape', 'ksubi'
        ]
        
        # Remove current brand from check list
        current_brand_lower = current_brand.lower()
        hardcoded_brands = [brand for brand in hardcoded_brands if brand != current_brand_lower]
        
        # Check for hardcoded brands
        for brand in hardcoded_brands:
            if brand in result_str:
                print(f"    ⚠️  Found hardcoded brand '{brand}' in results for {current_brand}")
                return False
        
        return True
        
    except Exception as e:
        print(f"    ❌ Error checking brand neutrality: {str(e)}")
        return False

def test_query_generation():
    """Test brand query generation."""
    print("=== Testing Query Generation ===\n")
    
    orchestrator = CIOrchestrator()
    
    test_cases = [
        {
            "brand": Brand(name="Test Brand"),
            "expected_contains": ['"Test Brand"']
        },
        {
            "brand": Brand(
                name="Supreme",
                meta={
                    "aliases": ["Supreme NY"],
                    "hashtags": ["#supreme", "#supremeny"]
                }
            ),
            "expected_contains": ['"Supreme"', '"Supreme NY"', '#supreme', '#supremeny']
        },
        {
            "brand": Brand(
                name="Nike",
                meta={
                    "priority_platforms": ["instagram.com", "tiktok.com"]
                }
            ),
            "expected_contains": ['"Nike"', 'site:instagram.com', 'site:tiktok.com']
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"Query Test {i}: {test_case['brand'].name}")
        
        try:
            query = orchestrator._build_brand_query(test_case['brand'])
            print(f"  Generated query: {query}")
            
            # Check if expected elements are present
            all_present = True
            for expected in test_case['expected_contains']:
                if expected not in query:
                    print(f"  ❌ Missing expected element: {expected}")
                    all_present = False
                else:
                    print(f"  ✅ Found: {expected}")
            
            if all_present:
                print(f"  ✅ Query generation PASSED")
            else:
                print(f"  ❌ Query generation FAILED")
                
        except Exception as e:
            print(f"  ❌ Error generating query: {str(e)}")
        
        print()

async def run_all_tests():
    """Run all brand neutrality tests."""
    print("Starting comprehensive brand-neutral tests...\n")
    
    # Test query generation
    test_query_generation()
    
    # Test brand-neutral functionality
    success = await test_brand_neutral_functionality()
    
    print(f"\n{'='*50}")
    if success:
        print("🎉 ALL TESTS PASSED - CI Orchestrator is brand-neutral!")
    else:
        print("❌ SOME TESTS FAILED - Review issues above")
    print(f"{'='*50}")
    
    return success

if __name__ == "__main__":
    success = asyncio.run(run_all_tests())


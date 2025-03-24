#!/usr/bin/env python
"""
Test script to verify the fix for the article distribution logic
"""
import json
import requests
import sys
from pprint import pprint

# Test queries known to have had issues
TEST_QUERIES = [
    "wheat prices food",
    "Ukraine",
    "artificial intelligence",
    "climate change"
]

def test_query(query):
    """Test a specific query and analyze the results"""
    print(f"\n{'='*80}")
    print(f"TESTING QUERY: '{query}'")
    print(f"{'='*80}")
    
    try:
        # Make request to local server
        response = requests.post(
            "http://localhost:5000/data", 
            data={"event": query},
            timeout=30
        )
        
        # Check if request was successful
        response.raise_for_status()
        data = response.json()
        
        if 'error' in data:
            print(f"Error: {data['error']}")
            return
        
        if 'warning' in data:
            print(f"Warning: {data['warning']}")
        
        # Print summary info
        print(f"Summary: {data.get('summary', 'No summary')[:100]}...")
        
        # Analyze article count and distribution
        articles = data.get('articles', [])
        print(f"\nReceived {len(articles)} articles")
        
        # Count by source
        source_counts = {}
        for article in articles:
            source = article.get('source', 'Unknown')
            source_counts[source] = source_counts.get(source, 0) + 1
        
        print("\nSource distribution:")
        for source, count in source_counts.items():
            print(f"- {source}: {count} articles")
        
        # Print sample article titles
        print("\nSample article titles:")
        for i, article in enumerate(articles[:5]):
            print(f"{i+1}. {article.get('title', 'No title')[:60]}...")
        
        # Check against expected minimum count (baseline before fix was 5)
        if len(articles) <= 5:
            print("\n⚠️ WARNING: Article count is still 5 or less. Fix may not be working as expected.")
        else:
            print(f"\n✅ SUCCESS: Received {len(articles)} articles - more than the previous limit of 5.")
            
        return len(articles), source_counts
        
    except requests.RequestException as e:
        print(f"Request failed: {e}")
        return 0, {}

def run_all_tests():
    """Run tests for all defined queries"""
    results = {}
    success_count = 0
    
    for query in TEST_QUERIES:
        article_count, source_counts = test_query(query)
        results[query] = {
            "article_count": article_count,
            "source_counts": source_counts
        }
        
        if article_count > 5:
            success_count += 1
    
    # Print summary
    print(f"\n{'='*80}")
    print(f"TEST SUMMARY: {success_count}/{len(TEST_QUERIES)} queries returned more than 5 articles")
    print(f"{'='*80}")
    
    for query, result in results.items():
        status = "✅" if result["article_count"] > 5 else "❌"
        print(f"{status} {query}: {result['article_count']} articles")
    
    return success_count == len(TEST_QUERIES)

if __name__ == "__main__":
    print("Testing article distribution fix...")
    success = run_all_tests()
    
    if success:
        print("\nAll tests passed! The fix appears to be working correctly.")
        sys.exit(0)
    else:
        print("\nSome tests failed. The fix may not be fully effective.")
        sys.exit(1) 
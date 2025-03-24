#!/usr/bin/env python
"""
Test script to try different dynamic cap formulas
"""
import sys
from pprint import pprint

# Configuration values
MAX_ARTICLES_PER_SOURCE = 4
DEFAULT_TOP_N = 15

# Test data for "wheat prices food"
source_groups = {
    "BusinessLine": 1,
    "Guardian": 4,
    "Devdiscourse": 1,
    "SooToday": 1
}

def test_formula(name, formula_func):
    """Test a specific dynamic cap formula and show results"""
    print(f"\n{'='*50}")
    print(f"TESTING FORMULA: {name}")
    print(f"{'='*50}")
    
    num_sources = len(source_groups)
    dynamic_cap = formula_func(num_sources)
    
    print(f"Number of sources: {num_sources}")
    print(f"Dynamic cap: {dynamic_cap} articles per source")
    
    # Simulate the distribution logic
    final_articles = []
    remaining_slots = DEFAULT_TOP_N
    
    # First round - one from each source
    first_round_sources = []
    for source, count in source_groups.items():
        if count > 0 and remaining_slots > 0:
            final_articles.append(f"{source} article 1")
            remaining_slots -= 1
            first_round_sources.append(source)
    
    print(f"First round: Added {len(first_round_sources)} articles (one from each source)")
    print(f"Remaining slots: {remaining_slots}")
    
    # Second round - up to dynamic cap
    second_round_additions = {}
    for source, count in source_groups.items():
        articles_to_add = min(count - 1, dynamic_cap - 1)  # -1 because we already added one
        articles_to_add = max(0, articles_to_add)  # Ensure non-negative
        articles_to_add = min(articles_to_add, remaining_slots)  # Don't exceed remaining slots
        
        if articles_to_add > 0:
            for i in range(articles_to_add):
                final_articles.append(f"{source} article {i+2}")
                remaining_slots -= 1
            second_round_additions[source] = articles_to_add
    
    print("Second round additions:")
    for source, count in second_round_additions.items():
        print(f"- {source}: +{count} articles")
    print(f"Remaining slots: {remaining_slots}")
    
    # Final distribution
    final_counts = {}
    for article in final_articles:
        source = article.split()[0]
        final_counts[source] = final_counts.get(source, 0) + 1
    
    print("\nFinal distribution:")
    for source, count in final_counts.items():
        print(f"- {source}: {count} articles (out of {source_groups[source]} available)")
    
    print(f"\nTotal articles: {len(final_articles)}")
    print(f"{'='*50}")
    
    return len(final_articles)

# Define different formulas to test
formulas = {
    "Original": lambda n: min(MAX_ARTICLES_PER_SOURCE, max(2, DEFAULT_TOP_N // n)),
    "Modified (n-1)": lambda n: min(MAX_ARTICLES_PER_SOURCE, max(3, DEFAULT_TOP_N // max(1, n - 1))),
    "Fixed cap=3": lambda n: 3,
    "More aggressive": lambda n: min(MAX_ARTICLES_PER_SOURCE, max(3, DEFAULT_TOP_N // max(1, n - 2))),
    "Scaling": lambda n: min(MAX_ARTICLES_PER_SOURCE, max(3, int(DEFAULT_TOP_N * 0.8 / n))),
    "Guardian special": lambda n: {'BusinessLine': 1, 'Guardian': 3, 'Devdiscourse': 1, 'SooToday': 1}
}

if __name__ == "__main__":
    print("Testing different dynamic cap formulas for 'wheat prices food' query...")
    
    results = {}
    for name, formula in formulas.items():
        results[name] = test_formula(name, formula)
    
    print("\nSUMMARY OF RESULTS:")
    print("=" * 50)
    for name, count in results.items():
        status = "✅" if count > 5 else "❌"
        print(f"{status} {name}: {count} articles") 
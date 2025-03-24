#!/usr/bin/env python
"""
Test script to understand article distribution logic in the news app
"""
import sys
import json
from pprint import pprint

# Import config values
try:
    from config_prod import MAX_ARTICLES_PER_SOURCE, DEFAULT_TOP_N
    print(f"Imported config values successfully:")
    print(f"MAX_ARTICLES_PER_SOURCE = {MAX_ARTICLES_PER_SOURCE}")
    print(f"DEFAULT_TOP_N = {DEFAULT_TOP_N}")
except ImportError as e:
    print(f"Error importing config: {e}")
    MAX_ARTICLES_PER_SOURCE = 4
    DEFAULT_TOP_N = 10
    print(f"Using fallback values: MAX_ARTICLES_PER_SOURCE={MAX_ARTICLES_PER_SOURCE}, DEFAULT_TOP_N={DEFAULT_TOP_N}")

def simulate_grouping_and_capping(sources_with_articles):
    """
    Simulate the grouping and capping logic from routes.py
    
    Args:
        sources_with_articles: Dict of source name -> list of articles
    """
    print("\n--- Simulation of grouping and capping logic ---")
    print(f"Input: {len(sources_with_articles)} sources with a total of {sum(len(articles) for articles in sources_with_articles.values())} articles")
    
    # Print source distribution
    for source, articles in sources_with_articles.items():
        print(f"- {source}: {len(articles)} articles")
    
    # Calculate dynamic cap
    num_sources = len(sources_with_articles)
    dynamic_cap = min(MAX_ARTICLES_PER_SOURCE, max(2, DEFAULT_TOP_N // num_sources))
    print(f"\nUsing dynamic cap of {dynamic_cap} articles per source for {num_sources} sources")
    print(f"Total slots available: {DEFAULT_TOP_N}")
    print(f"Calculation: min({MAX_ARTICLES_PER_SOURCE}, max(2, {DEFAULT_TOP_N} // {num_sources})) = {dynamic_cap}")
    
    # First round - take one from each source
    final_articles = []
    remaining_slots = DEFAULT_TOP_N
    
    first_round_sources = []
    for source, articles_list in sources_with_articles.items():
        source_articles = articles_list.copy()  # Make a copy to avoid modifying the original
        if source_articles and remaining_slots > 0:
            final_articles.append(source_articles[0])
            source_articles.pop(0)
            remaining_slots -= 1
            first_round_sources.append(source)
    
    print(f"\nFirst round distribution - Added one article from each of these sources: {first_round_sources}")
    print(f"Remaining slots after first round: {remaining_slots}")
    
    # Track what's added in second round
    second_round_additions = {}
    for source, articles_list in sources_with_articles.items():
        source_articles = articles_list.copy()  # Create a new copy
        # Skip the first article that was already added
        if source_articles:
            source_articles.pop(0)
        
        # Add more articles until we reach the dynamic cap
        while source_articles and len([a for a in final_articles if a.get('source') == source]) < dynamic_cap and remaining_slots > 0:
            final_articles.append(source_articles[0])
            source_articles.pop(0)
            remaining_slots -= 1
            second_round_additions[source] = second_round_additions.get(source, 0) + 1
    
    print(f"Second round distribution - Additional articles per source: {second_round_additions}")
    print(f"Remaining slots after second round: {remaining_slots}")
    
    # Print final distribution
    final_source_counts = {}
    for article in final_articles:
        source = article.get('source', 'Unknown')
        final_source_counts[source] = final_source_counts.get(source, 0) + 1
    
    print(f"\nFinal distribution:")
    for source, count in final_source_counts.items():
        print(f"- {source}: {count} articles")
    
    print(f"\nTotal articles in final result: {len(final_articles)}")
    print("------------------------------------------------")
    
    return final_articles

# Example data representing the "wheat prices food" query
sources_with_articles = {
    "BusinessLine": [{"title": "Growing green: How sustainable farming can feed th...", "source": "BusinessLine"}],
    "Guardian": [
        {"title": "Asda cuts prices on 1,500 products in effort to ha...", "source": "Guardian"},
        {"title": "Trump administration 'villainizes' immigrant famil...", "source": "Guardian"},
        {"title": "Pioneering Devon food forest garden at risk after ...", "source": "Guardian"},
        {"title": "Egg prices have quadrupled, chicken has doubled: t...", "source": "Guardian"}
    ],
    "Devdiscourse": [{"title": "India's Futures Trading Suspension Extended - Impa...", "source": "Devdiscourse"}],
    "SooToday": [{"title": "How the grocery supply chain works, from wheat fie...", "source": "SooToday"}]
}

# Run the simulation
final_articles = simulate_grouping_and_capping(sources_with_articles)

# Another test with fewer sources
print("\nTest 2: Fewer sources (2 sources)")
sources_with_articles_2 = {
    "Guardian": [
        {"title": "Article 1", "source": "Guardian"},
        {"title": "Article 2", "source": "Guardian"},
        {"title": "Article 3", "source": "Guardian"},
        {"title": "Article 4", "source": "Guardian"},
        {"title": "Article 5", "source": "Guardian"}
    ],
    "CNN": [
        {"title": "CNN Article 1", "source": "CNN"},
        {"title": "CNN Article 2", "source": "CNN"},
        {"title": "CNN Article 3", "source": "CNN"}
    ]
}
simulate_grouping_and_capping(sources_with_articles_2)

# Test with more sources
print("\nTest 3: More sources (6 sources)")
sources_with_articles_3 = {
    "Guardian": [{"title": "Guardian Article 1", "source": "Guardian"}, {"title": "Guardian Article 2", "source": "Guardian"}],
    "CNN": [{"title": "CNN Article 1", "source": "CNN"}, {"title": "CNN Article 2", "source": "CNN"}],
    "Fox News": [{"title": "Fox News Article 1", "source": "Fox News"}],
    "NBC": [{"title": "NBC Article 1", "source": "NBC"}],
    "BBC": [{"title": "BBC Article 1", "source": "BBC"}, {"title": "BBC Article 2", "source": "BBC"}],
    "Al Jazeera": [{"title": "Al Jazeera Article 1", "source": "Al Jazeera"}]
}
simulate_grouping_and_capping(sources_with_articles_3)

if __name__ == "__main__":
    print("\nTest complete!") 
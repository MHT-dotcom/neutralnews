from fetchers import fetch_articles, fetch_newsdata_io_articles
from processors import process_articles, filter_relevant_articles

def test_newsdata():
    # First, get articles directly from NewsData.io
    direct_articles = fetch_newsdata_io_articles("climate change")
    print(f"\nDirect NewsData.io API call:")
    print(f"Found {len(direct_articles)} articles directly from NewsData.io")
    
    # Show source names from direct call
    if direct_articles:
        print("\nSources from direct NewsData.io call:")
        for i, article in enumerate(direct_articles[:5]):
            source_name = article.get("source", {}).get("name", "Unknown")
            print(f"  {i+1}. {source_name}: {article.get('title', 'No title')}")
    
    # Then test the combined fetch_articles function
    articles = fetch_articles("climate change")
    newsdata_articles = []
    sources = {}
    providers = {}
    
    for article in articles:
        try:
            if isinstance(article, dict):
                # Track sources
                source = article.get("source", {})
                if isinstance(source, dict):
                    source_name = source.get("name", "")
                    sources[source_name] = sources.get(source_name, 0) + 1
                
                # Track providers
                provider = article.get("provider", "Unknown")
                providers[provider] = providers.get(provider, 0) + 1
                
                # Identify NewsData.io articles using provider field
                if provider == "NewsData.io":
                    newsdata_articles.append(article)
        except Exception as e:
            print(f"Error with article: {e}")
    
    print(f"\nCombined articles test:")
    print(f"Total articles: {len(articles)}")
    print(f"NewsData.io articles found by provider field: {len(newsdata_articles)}")
    
    print("\nProviders found:")
    for name, count in sorted(providers.items(), key=lambda x: x[1], reverse=True):
        print(f"  - {name}: {count}")
    
    print("\nTop 10 sources found in combined results:")
    for i, (source, count) in enumerate(sorted(sources.items(), key=lambda x: x[1], reverse=True)[:10]):
        print(f"  - {source}: {count}")
    
    # Test the standardization function
    print("\nStandardized NewsData.io articles test:")
    std_newsdata = process_articles(newsdata_articles, "NewsData.io")
    print(f"Original count: {len(newsdata_articles)}")
    print(f"After standardization: {len(std_newsdata)}")
    print("\nSample standardized articles:")
    for i, article in enumerate(std_newsdata[:3], 1):
        print(f"  {i}. Source: {article.get('source', 'Unknown')}, Provider: {article.get('provider', 'Unknown')}, Title: {article.get('title', 'No title')}")
    
    # Test relevance filtering
    print("\nRelevance filtering test:")
    relevant_articles = filter_relevant_articles(std_newsdata, "climate change")
    print(f"Before filtering: {len(std_newsdata)}")
    print(f"After relevance filtering: {len(relevant_articles)}")
    if relevant_articles:
        print("\nSample articles that passed relevance filtering:")
        for i, article in enumerate(relevant_articles[:3], 1):
            print(f"  {i}. Source: {article.get('source', 'Unknown')}, Title: {article.get('title', 'No title')}")
    else:
        print("No articles passed relevance filtering!")
    
    # Simulate the complete article processing pipeline
    print("\nSimulating complete processing pipeline:")
    # For testing, we'll use only the NewsData.io articles
    # Process Guardian articles for comparison
    guardian_articles = [article for article in articles if article.get('provider') != 'NewsData.io'][:5]
    std_guardian = process_articles(guardian_articles, "Guardian")
    print(f"Guardian articles: {len(std_guardian)}")

    # Combine articles
    all_test_articles = std_newsdata + std_guardian
    print(f"Combined articles: {len(all_test_articles)}")

    # Group articles by source
    print("\nGrouping by source:")
    source_groups = {}
    for article in all_test_articles:
        # For NewsData.io articles, use provider as the source group key
        # For others, use the regular source field
        source_key = article.get('provider', article.get('source', 'Unknown'))
        if source_key not in source_groups:
            source_groups[source_key] = []
        source_groups[source_key].append(article)

    for source, articles_list in source_groups.items():
        print(f"  - {source}: {len(articles_list)} articles")

    # Simulate capping
    print("\nSimulating capping algorithm:")
    final_articles = []
    num_sources = len(source_groups)
    top_n_value = 10  # Similar to DEFAULT_TOP_N in the code
    dynamic_cap = min(5, max(3, top_n_value // max(1, num_sources - 1)))
    print(f"Using dynamic cap of {dynamic_cap} articles per source for {num_sources} sources")

    remaining_slots = top_n_value
    # First round - add one article from each source
    first_round_sources = []
    for source, articles_list in source_groups.items():
        if articles_list and remaining_slots > 0:
            final_articles.append(articles_list[0])
            articles_list.pop(0)
            remaining_slots -= 1
            first_round_sources.append(source)
    print(f"First round - added one article from each source: {first_round_sources}")
    print(f"Remaining slots: {remaining_slots}")

    # Second round - add additional articles up to the cap
    second_round_additions = {}
    while remaining_slots > 0:
        added_article = False
        for source, articles_list in sorted(source_groups.items()):
            current_source_count = len([a for a in final_articles if a.get('source') == source])
            if articles_list and current_source_count < dynamic_cap:
                final_articles.append(articles_list[0])
                articles_list.pop(0)
                remaining_slots -= 1
                second_round_additions[source] = second_round_additions.get(source, 0) + 1
                added_article = True
                if remaining_slots <= 0:
                    break
        if not added_article:
            break
    print(f"Second round - additional articles per source: {second_round_additions}")

    # Final distribution
    final_source_counts = {}
    for article in final_articles:
        source = article.get('source', 'Unknown')
        final_source_counts[source] = final_source_counts.get(source, 0) + 1

    print("\nFinal distribution:")
    for source, count in final_source_counts.items():
        print(f"  - {source}: {count} articles")

    print("\nSample articles from final list:")
    for i, article in enumerate(final_articles[:5], 1):
        print(f"  {i}. Source: {article.get('source', 'Unknown')}, Title: {article.get('title', 'No title')}")

    if newsdata_articles:
        print("\nSample articles from NewsData.io provider:")
        for i, article in enumerate(newsdata_articles[:3]):
            source = article.get("source", {}).get("name", "Unknown")
            title = article.get("title", "No title")
            print(f"  {i+1}. {source}: {title}")

if __name__ == "__main__":
    test_newsdata() 
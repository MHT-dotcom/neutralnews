# This file contains functions to process and standardize articles from various news APIs (e.g., NewsAPI.org, Guardian, NYT) into a uniform format, remove duplicates, filter relevant articles by TF-IDF, and summarize them using OpenAI's GPT-3.5-turbo.

import openai
import logging
import requests
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from config_prod import DEFAULT_TOP_N, RELEVANCE_THRESHOLD, OPENAI_API_KEY, SUMMARIZER_BY_GPT, WEIGHT_RELEVANCE, WEIGHT_POPULARITY
import re
import time
import os
from deep_translator import GoogleTranslator  # Using deep_translator instead of googletrans

# Set up logging
logger = logging.getLogger('neutralnews')
translator = GoogleTranslator(source='auto', target='en')

def translate_to_english(text):
    """Translate text to English if TRANSLATION=TRUE."""
    if os.getenv("TRANSLATION", "FALSE").upper() != "TRUE":
        return text
    try:
        translated = translator.translate(text)
        logger.debug(f"Translated text to English: {translated[:50]}...")
        return translated
    except Exception as e:
        logger.error(f"Translation failed: {str(e)}")
        return text

def get_share_count(url, sharecount_api_key):
    url = f"https://api.sharedcount.com/?url={url}&key={sharecount_api_key}"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            return data.get('total', 0)
        else:
            return 0
    except Exception as e:
        return 0
    
def standardize_aylien_articles(articles):
    """Standardize Aylien articles into a common format with source attribution."""
    standardized_articles = []
    
    for i, article in enumerate(articles):
        try:
            standardized_article = {
                'title': translate_to_english(article.title),
                'url': article.links.permalink,
                'content': translate_to_english(article.body),
                'source': 'Aylien'
            }
            standardized_articles.append(standardized_article)
        except Exception as e:
            logger.error(f"Error standardizing Aylien article {i+1}: {e}")
            
    return standardized_articles

def standardize_gnews_articles(articles):
    """Standardize GNews articles into a common format with true source attribution."""
    standardized_articles = []
    
    for i, article in enumerate(articles):
        try:
            standardized_article = {
                'title': translate_to_english(article.get('title', 'No title available')),
                'url': article.get('url', '#'),
                'content': translate_to_english(article.get('content', '')),
                'source': article.get('source', {}).get('name', 'GNews')
            }
            standardized_articles.append(standardized_article)
        except Exception as e:
            logger.error(f"Error standardizing GNews article {i+1}: {e}")
            
    return standardized_articles

def standardize_articles(articles, source):
    """Standardize articles from NewsAPI.org or The Guardian into a common format with true source attribution."""
    standardized_articles = []
    
    for article in articles:
        content = translate_to_english(article.get('content', '') or article.get('webTitle', ''))
        if not content.strip():
            continue
        
        # Handle article source properly
        article_source = article.get('source', {})
        if isinstance(article_source, dict):
            article_source = article_source.get('name', source) or source
        else:
            article_source = source if source != 'NewsAPI' else article_source
        
        standardized_article = {
            'title': translate_to_english(article.get('title') or article.get('webTitle', 'No title available')),
            'url': article.get('url') or article.get('webUrl', '#'),
            'content': content,
            'source': article_source
        }
        standardized_articles.append(standardized_article)
    return standardized_articles

def standardize_nyt_articles(articles):
    """Standardize articles from the New York Times API."""
    standardized_articles = []
    
    for i, article in enumerate(articles):
        try:
            headline = translate_to_english(article.get('headline', {}).get('main', ''))
            content = translate_to_english(article.get('abstract', '') or article.get('lead_paragraph', ''))
            if not content.strip():
                continue
            
            standardized_article = {
                'title': headline or 'No title available',
                'url': article.get('web_url', '#'),
                'content': content,
                'source': 'New York Times'
            }
            standardized_articles.append(standardized_article)
        except Exception as e:
            logger.error(f"NYT: Error standardizing article {i+1}: {e}")
    
    return standardized_articles

def standardize_mediastack_articles(articles):
    """Standardize articles from the Mediastack API."""
    standardized_articles = []
    
    for i, article in enumerate(articles):
        try:
            title = translate_to_english(article.get('title', ''))
            content = translate_to_english(article.get('description', ''))
            if not content.strip():
                continue
            
            standardized_article = {
                'title': title or 'No title available',
                'url': article.get('url', '#'),
                'content': content,
                'source': article.get('source', 'Mediastack')
            }
            standardized_articles.append(standardized_article)
        except Exception as e:
            logger.error(f"Mediastack: Error standardizing article {i+1}: {e}")
    
    return standardized_articles

def standardize_newsapi_ai_articles(articles):
    """Standardize articles from the NewsAPI.ai API."""
    standardized_articles = []
    
    for i, article in enumerate(articles):
        try:
            title = translate_to_english(article.get('title', ''))
            content = translate_to_english(article.get('body', '') or article.get('description', ''))
            if not content.strip():
                continue
            
            standardized_article = {
                'title': title or 'No title available',
                'url': article.get('url', '#'),
                'content': content,
                'source': article.get('source', {}).get('title', 'NewsAPI.ai')
            }
            standardized_articles.append(standardized_article)
        except Exception as e:
            logger.error(f"NewsAPI.ai: Error standardizing article {i+1}: {e}")
    
    return standardized_articles

def process_articles(articles, source):
    """
    Process articles based on their fetch source by applying the appropriate standardization.
    Adds robust error handling to prevent crashes regardless of input.
    """
    try:
        # Check for invalid input
        if not articles:
            logger.warning(f"Empty articles list received from {source}")
            return []
            
        if not isinstance(articles, list):
            logger.warning(f"Non-list articles received from {source}: {type(articles)}")
            # Try to convert to list if possible
            try:
                articles = list(articles) if hasattr(articles, '__iter__') else [articles]
            except:
                logger.error(f"Could not convert {source} results to list")
                return []
                
        # Apply appropriate standardization with error handling
        try:
            if source == 'Aylien':
                standardized = standardize_aylien_articles(articles)
            elif source == 'GNews':
                standardized = standardize_gnews_articles(articles)
            elif source == 'NYT':
                standardized = standardize_nyt_articles(articles)
            elif source == 'Mediastack':
                standardized = standardize_mediastack_articles(articles)
            elif source == 'NewsAPI.ai':
                standardized = standardize_newsapi_ai_articles(articles)
            else:  # NewsAPI.org or Guardian
                standardized = standardize_articles(articles, source)
        except Exception as e:
            logger.error(f"Error standardizing {source} articles: {e}")
            # Attempt fallback standardization for any articles that can be processed
            standardized = []
            for article in articles:
                try:
                    if not isinstance(article, dict):
                        continue
                        
                    # Create a basic standardized article with required fields
                    std_article = {
                        'title': str(article.get('title', '')),
                        'url': str(article.get('url', '')),
                        'source': source,
                        'description': str(article.get('description', '')),
                        'content': str(article.get('content', '')),
                        'published_at': str(article.get('published_at', '')),
                    }
                    
                    # Only add if it has at least a title and URL
                    if std_article['title'] and std_article['url']:
                        standardized.append(std_article)
                except Exception as article_err:
                    logger.error(f"Error processing individual {source} article: {article_err}")
                    continue
        
        # Final validation of standardized articles
        valid_standardized = []
        for article in standardized:
            if not isinstance(article, dict):
                logger.warning(f"Non-dict article after standardization from {source}")
                continue
                
            # Ensure all required fields exist with proper types
            try:
                validated_article = {
                    'title': str(article.get('title', '')),
                    'url': str(article.get('url', '')),
                    'source': str(article.get('source', source)),
                    'provider': source,
                    'description': str(article.get('description', '')),
                    'content': str(article.get('content', '')),
                    'published_at': str(article.get('published_at', '')),
                }
                
                # Only include articles with required fields
                if validated_article['title'] and validated_article['url']:
                    valid_standardized.append(validated_article)
            except Exception as validation_err:
                logger.error(f"Error validating standardized article from {source}: {validation_err}")
                continue
        
        logger.info(f"Successfully processed {len(valid_standardized)} articles from {source}")
        return valid_standardized
        
    except Exception as e:
        logger.error(f"Critical error in process_articles for {source}: {e}", exc_info=True)
        return []  # Return empty list as fallback

def remove_duplicates(articles):
    """
    Remove duplicate articles based on their titles using similarity matching.
    Handles None values and empty arrays gracefully.
    """
    logger.info(f"Removing duplicates from {len(articles) if articles else 0} articles")
    
    # Handle edge cases
    if not articles:
        logger.warning("Empty article list passed to remove_duplicates")
        return []
    
    # Filter out articles with no title
    valid_articles = [a for a in articles if a and isinstance(a, dict) and a.get('title')]
    if len(valid_articles) < len(articles):
        logger.warning(f"Filtered out {len(articles) - len(valid_articles)} articles with no title")
    
    if not valid_articles:
        logger.warning("No valid articles with titles found")
        return []
    
    # Use a more robust deduplication approach
    unique_articles = []
    seen_titles = set()
    
    for article in valid_articles:
        title = article.get('title', '').strip().lower()
        
        # Skip empty titles
        if not title:
            continue
            
        # Check if we've seen this exact title before
        if title in seen_titles:
            continue
            
        # Check for very similar titles (simple approach)
        duplicate = False
        for seen_title in seen_titles:
            # If >80% of words match, consider it a duplicate
            title_words = set(title.split())
            seen_words = set(seen_title.split())
            
            if title_words and seen_words:  # Avoid division by zero
                similarity = len(title_words.intersection(seen_words)) / len(title_words.union(seen_words))
                if similarity > 0.8:
                    duplicate = True
                    break
        
        if not duplicate:
            seen_titles.add(title)
            unique_articles.append(article)
    
    logger.info(f"Removed {len(valid_articles) - len(unique_articles)} duplicates, returning {len(unique_articles)} unique articles")
    return unique_articles

def filter_relevant_articles(articles, query, top_n=DEFAULT_TOP_N, relevance_threshold=RELEVANCE_THRESHOLD):
    """Filter and sort articles by combined relevance and popularity scores."""
    logger.info(f"Starting detailed filtering for '{query}' with {len(articles)} articles")
    
    relevance_threshold = 0.01
    logger.info(f"Using universal low threshold: {relevance_threshold}")
    
    logger.info(f"Articles before filtering for '{query}':")
    for i, article in enumerate(articles):
        title = article.get('title', 'No title')
        source = article.get('source', 'Unknown')
        logger.info(f"Article {i+1}: '{title[:50]}...' - Source: {source}")
    
    texts = [article.get('content', '') or article.get('title', '') for article in articles]
    if not any(texts):
        logger.warning(f"No text content found in articles for '{query}'")
        return articles[:top_n]
    
    try:
        vectorizer = TfidfVectorizer()
        tfidf_matrix = vectorizer.fit_transform(texts)
        query_vector = vectorizer.transform([query])
        similarities = cosine_similarity(query_vector, tfidf_matrix).flatten()
    except Exception as e:
        logger.error(f"Error during vectorization: {str(e)}")
        logger.info(f"Returning all articles due to vectorization error")
        return articles[:top_n]
    
    share_counts = [article.get('share_count', 0) for article in articles]
    max_share_count = max(share_counts) if share_counts else 0
    
    logger.info(f"Relevance threshold for '{query}': {relevance_threshold}")
    logger.info(f"Article filtering details for '{query}':")
    
    article_scores = []
    filtered_count = 0
    for i, (article, similarity, share_count) in enumerate(zip(articles, similarities, share_counts)):
        article_title = article.get('title', 'No title')
        article_source = article.get('source', 'Unknown')
        
        if similarity >= relevance_threshold:
            normalized_share_count = share_count / max_share_count if max_share_count > 0 else 0
            combined_score = similarity * WEIGHT_RELEVANCE + normalized_share_count * WEIGHT_POPULARITY
            article_scores.append((article, combined_score))
            logger.info(f"KEPT: Article {i+1} - Title: '{article_title[:30]}...' - Source: {article_source} - Similarity: {similarity:.4f}")
        else:
            filtered_count += 1
            logger.info(f"FILTERED OUT: Article {i+1} - Title: '{article_title[:30]}...' - Source: {article_source} - Similarity: {similarity:.4f} (below threshold {relevance_threshold})")
    
    logger.info(f"Articles filtered out for '{query}': {filtered_count}/{len(articles)}")
    
    if not article_scores:
        logger.warning(f"No articles passed relevance filter for '{query}'. Returning all articles instead.")
        return articles[:top_n]
    
    sorted_articles = sorted(article_scores, key=lambda x: x[1], reverse=True)
    relevant_articles = [article for article, _ in sorted_articles[:top_n]]
    
    logger.info(f"Final article count for '{query}' after filtering: {len(relevant_articles)}")
    return relevant_articles

def process_trending_articles(trending_data):
    """
    Process articles for trending topics: standardize and summarize.
    
    Args:
        trending_data (dict): Dictionary of topics mapped to article lists.
    
    Returns:
        dict: Processed trending data with summaries.
    """
    processed_data = {}

    for topic, articles in trending_data.items():
        logger.info(f"Processing articles for topic: {topic}")
        if not articles:
            processed_data[topic] = {"articles": [], "summary": "No articles found."}
            continue
        
        standardized_articles = standardize_articles(articles, 'Unknown')
        
        # Add sentiment score of 0 to each article
        for article in standardized_articles:
            article['sentiment_score'] = 0
            
        summary = summarize_articles(standardized_articles, topic)
        
        processed_data[topic] = {
            "articles": standardized_articles[:3],
            "summary": summary
        }
    
    return processed_data

# Use only GPT-based summarization since we've removed the model manager
def summarize_articles(articles, query):
    """Generate a concise summary of articles using GPT-3.5-turbo."""
    logger.info(f"Starting GPT-based summarization for {len(articles)} articles about '{query}'")
    
    articles_content = []
    for article in articles:
        title = article.get('title', '').strip()
        content = article.get('content', '').strip()[:100]
        if title or content:
            articles_content.append(f"Title: {title}\nExcerpt: {content}")
    
    if not articles_content:
        logger.warning("No content available for summarization")
        return f"Found {len(articles)} articles about '{query}', but no content was available for summarization."
    
    base_prompt = f"Summarize these news articles about '{query}' in 2-3 sentences. Be concise and factual:\n\n"
    articles_text = "\n\n".join(articles_content)
    prompt = base_prompt + articles_text
    
    logger.info(f"GPT prompt length: {len(prompt)} characters")
    logger.debug(f"GPT prompt content: {prompt}")
    
    try:
        client = openai.OpenAI(api_key=OPENAI_API_KEY)
        start_time = time.time()
        logger.info(f"Starting OpenAI API call for '{query}' at {start_time}")
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=100,
            temperature=0.3,
            presence_penalty=-0.1,
            frequency_penalty=0.3
        )
        
        end_time = time.time()
        summary = response.choices[0].message.content.strip()
        logger.info(f"OpenAI API call completed in {end_time - start_time:.2f}s")
        logger.info(f"Generated summary for '{query}': {summary}")
        
        return summary
        
    except Exception as e:
        logger.error(f"OpenAI API call failed for '{query}': {str(e)}", exc_info=True)
        return f"Found {len(articles)} articles about '{query}'. View them below for the latest news on this topic."
"""process and standardize articles from news APIs into a uniform format, 
analyze sentiment with preloaded DistilBERT model with batch processing, remove duplicates, 
filter relevant articles by TF-IDF, and summarize them with GPT-3.5-turbo. 
also does model loading and clearing via the ModelManager class.
"""

import openai
import logging
import requests
import inspect
import time
import os
from transformers import pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from flask import current_app
import torch
import re

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Log when this module is imported
logger.info(f"[IMPORT_SEQUENCE] {time.time()} - Processors module is being imported")

# Log the call stack to see who's importing this module
current_frame = inspect.currentframe()
try:
    call_stack = inspect.getouterframes(current_frame)
    caller_info = ", ".join([f"{frame.filename}:{frame.lineno}" for frame in call_stack[1:4]])
    logger.info(f"[IMPORT_SEQUENCE] {time.time()} - Processors module imported by: {caller_info}")
except Exception as e:
    logger.error(f"[IMPORT_SEQUENCE] Error getting call stack: {e}")
finally:
    del current_frame  # Prevent reference cycles

# Track configuration access attempts
config_access_attempts = {}

class ModelManager:
    _instance = None
    _summarizer = None
    _sentiment_analyzer = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
            logger.info("Preloading sentiment analysis model at startup...")
            cls._instance._sentiment_analyzer = pipeline("sentiment-analysis", model="distilbert-base-uncased-finetuned-sst-2-english", device=-1)  # CPU, preloaded
        return cls._instance

    def get_summarizer(self):
        if self._summarizer is None:
            logger.info("Loading summarization model...")
            self._summarizer = pipeline("summarization", model="facebook/bart-large-cnn")
        return self._summarizer

    def get_sentiment_analyzer(self):
        return self._sentiment_analyzer  # Return preloaded model

    def clear_models(self):
        logger.info("Clearing models from memory...")
        self._summarizer = None
        # Keep _sentiment_analyzer loaded to avoid reload overhead
        torch.cuda.empty_cache() if torch.cuda.is_available() else None

def get_config(key, default=None):
    """Helper function to safely get config values"""
    try:
        # Try to access the config within application context
        return current_app.config.get(key, default)
    except RuntimeError:
        # If we're outside of application context (e.g., during testing)
        logger.warning(f"Accessing {key} outside application context")
        
        # Check environment variables directly as a fallback
        env_key = key.upper()  # Convert to uppercase for environment variable convention
        if env_key in os.environ:
            env_value = os.environ.get(env_key)
            # Log the fact that we found the value in environment variables
            if any(x in key.upper() for x in ['KEY', 'SECRET', 'PASSWORD', 'TOKEN']):
                logger.info(f"Found {key} in environment variables (length: {len(env_value)})")
            else:
                logger.info(f"Found {key} in environment variables: {env_value}")
            return env_value
            
        return default

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
    logger.info(f"Standardizing {len(articles)} Aylien articles")
    standardized_articles = []
    
    for i, article in enumerate(articles):
        try:
            standardized_article = {
                'title': article['title'],
                'url': article['url'],
                'content': article['content'],
                'source': article['source']['name'] if isinstance(article['source'], dict) and 'name' in article['source'] else 'Aylien'
            }
            logger.debug(f"Standardized Aylien article {i+1}: {standardized_article['title']} (Source: {standardized_article['source']})")
            standardized_articles.append(standardized_article)
        except Exception as e:
            logger.error(f"Error standardizing Aylien article {i+1}: {e}")
            
    return standardized_articles

def standardize_gnews_articles(articles):
    """Standardize GNews articles into a common format with true source attribution."""
    logger.info(f"Standardizing {len(articles)} GNews articles")
    standardized_articles = []
    
    for i, article in enumerate(articles):
        try:
            standardized_article = {
                'title': article.get('title', 'No title available'),
                'url': article.get('url', '#'),
                'content': article.get('content', ''),
                'source': article.get('source', {}).get('name', 'GNews')
            }
            logger.debug(f"Standardized GNews article {i+1}: {standardized_article['title']} (Source: {standardized_article['source']})")
            standardized_articles.append(standardized_article)
        except Exception as e:
            logger.error(f"Error standardizing GNews article {i+1}: {e}")
            
    return standardized_articles

def standardize_articles(articles, source):
    """Standardize articles from NewsAPI.org or The Guardian into a common format with true source attribution."""
    logger.info(f"Standardizing {len(articles)} {source} articles")
    standardized_articles = []
    
    for article in articles:
        content = article.get('content', '') or article.get('webTitle', '')
        if not content.strip():
            continue
        article_source = article.get('source', {}).get('name', 'Unknown') if source == 'NewsAPI' else source
        standardized_article = {
            'title': article.get('title') or article.get('webTitle', 'No title available'),
            'url': article.get('url') or article.get('webUrl', '#'),
            'content': content,
            'source': article_source
        }
        standardized_articles.append(standardized_article)
    return standardized_articles

def standardize_nyt_articles(articles):
    """Standardize articles from the New York Times API."""
    logger.info(f"Standardizing {len(articles)} NYT articles")
    standardized_articles = []
    
    for i, article in enumerate(articles):
        try:
            headline = article.get('headline', {}).get('main', '')
            content = article.get('abstract', '') or article.get('lead_paragraph', '')
            if not content.strip():
                logger.warning(f"NYT: Skipping article {i+1} due to empty content")
                continue
            
            standardized_article = {
                'title': headline or 'No title available',
                'url': article.get('web_url', '#'),
                'content': content,
                'source': 'New York Times'
            }
            logger.debug(f"NYT: Successfully standardized article {i+1}: {standardized_article['title']}")
            standardized_articles.append(standardized_article)
        except Exception as e:
            logger.error(f"NYT: Error standardizing article {i+1}: {e}")
    
    logger.info(f"NYT: Successfully standardized {len(standardized_articles)} out of {len(articles)} articles")
    return standardized_articles

def standardize_mediastack_articles(articles):
    """Standardize articles from the Mediastack API."""
    logger.info(f"Standardizing {len(articles)} Mediastack articles")
    standardized_articles = []
    
    for i, article in enumerate(articles):
        try:
            title = article.get('title', '')
            content = article.get('description', '')
            if not content.strip():
                logger.warning(f"Mediastack: Skipping article {i+1} due to empty content")
                continue
            
            standardized_article = {
                'title': title or 'No title available',
                'url': article.get('url', '#'),
                'content': content,
                'source': article.get('source', 'Mediastack')
            }
            logger.debug(f"Mediastack: Successfully standardized article {i+1}: {standardized_article['title']}")
            standardized_articles.append(standardized_article)
        except Exception as e:
            logger.error(f"Mediastack: Error standardizing article {i+1}: {e}")
    
    logger.info(f"Mediastack: Successfully standardized {len(standardized_articles)} out of {len(articles)} articles")
    return standardized_articles

def standardize_newsapi_ai_articles(articles):
    """Standardize articles from the NewsAPI.ai API."""
    logger.info(f"Standardizing {len(articles)} NewsAPI.ai articles")
    standardized_articles = []
    
    for i, article in enumerate(articles):
        try:
            title = article.get('title', '')
            content = article.get('body', '') or article.get('description', '')
            if not content.strip():
                logger.warning(f"NewsAPI.ai: Skipping article {i+1} due to empty content")
                continue
            
            standardized_article = {
                'title': title or 'No title available',
                'url': article.get('url', '#'),
                'content': content,
                'source': article.get('source', {}).get('title', 'NewsAPI.ai')
            }
            logger.debug(f"NewsAPI.ai: Successfully standardized article {i+1}: {standardized_article['title']}")
            standardized_articles.append(standardized_article)
        except Exception as e:
            logger.error(f"NewsAPI.ai: Error standardizing article {i+1}: {e}")
    
    logger.info(f"NewsAPI.ai: Successfully standardized {len(standardized_articles)} out of {len(articles)} articles")
    return standardized_articles

def process_articles(articles, source):
    """Process articles based on their fetch source by applying the appropriate standardization."""
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
    
    return standardized

def analyze_sentiment(text):
    """Analyze the sentiment of a text and return a normalized score between -1 and 1."""
    try:
        model_manager = ModelManager.get_instance()
        sentiment_analyzer = model_manager.get_sentiment_analyzer()
        result = sentiment_analyzer(text[:512])  # Kept as fallback, though batching is primary
        score = result[0]['score']
        if result[0]['label'] == 'NEGATIVE':
            score = -score
        return score
    except Exception as e:
        logger.error(f"Error in sentiment analysis: {e}")
        return 0

def remove_duplicates(articles):
    """Remove duplicate articles based on their titles."""
    logger.info(f"Removing duplicates from {len(articles)} articles")
    seen_titles = set()
    unique_articles = []
    for article in articles:
        title = article.get('title', '')
        if title and title not in seen_titles:
            seen_titles.add(title)
            unique_articles.append(article)
    logger.info(f"Removed {len(articles) - len(unique_articles)} duplicates")
    return unique_articles

def filter_relevant_articles(articles, query, top_n=None, relevance_threshold=None):
    """Filter articles by relevance to query using TF-IDF and cosine similarity."""
    top_n = top_n or get_config('DEFAULT_TOP_N', 5)
    relevance_threshold = relevance_threshold or get_config('RELEVANCE_THRESHOLD', 0.1)
    weight_relevance = get_config('WEIGHT_RELEVANCE', 0.7)
    weight_popularity = get_config('WEIGHT_POPULARITY', 0.3)
    
    texts = [article.get('content', '') or article.get('title', '') for article in articles]
    if not any(texts):
        return articles[:top_n]
    
    vectorizer = TfidfVectorizer()
    tfidf_matrix = vectorizer.fit_transform(texts)
    query_vector = vectorizer.transform([query])
    similarities = cosine_similarity(query_vector, tfidf_matrix).flatten()
    
    share_counts = [article.get('share_count', 0) for article in articles]
    max_share_count = max(share_counts) if share_counts else 0
    
    article_scores = []
    for article, similarity, share_count in zip(articles, similarities, share_counts):
        if similarity >= relevance_threshold:
            normalized_share_count = share_count / max_share_count if max_share_count > 0 else 0
            combined_score = similarity * weight_relevance + normalized_share_count * weight_popularity
            article_scores.append((article, combined_score))
    
    sorted_articles = sorted(article_scores, key=lambda x: x[1], reverse=True)
    relevant_articles = [article for article, _ in sorted_articles[:top_n]]
    
    return relevant_articles

def summarize_articles(articles, query):
    """Summarize articles using either GPT-3.5-turbo or BART based on config, determined at runtime."""
    logger.info(f"Summarizing {len(articles)} articles for query '{query}'")
    total_chars = sum(len(article.get('content', '')) for article in articles)
    logger.info(f"Total input character length: {total_chars}")
    
    articles_content = [article.get('content', '')[:150] or article.get('title', '')[:150] for article in articles]
    
    # Check config at runtime within context
    use_gpt = get_config('SUMMARIZER_BY_GPT', True)
    
    if use_gpt:
        # GPT-3.5-turbo summarization
        prompt = "You are an expert in summarizing news articles neutrally. Your task is to generate a balanced summary from the following articles, ensuring that you present a fair and unbiased view.\n\n"
        for i, content in enumerate(articles_content):
            prompt += f"Article {i+1}:\n{content}\n\n"
        prompt += "Please generate a summary that is approximately 150 words long, focusing on the main points and maintaining neutrality. The summary needs to be straight to the point and easy to read. Use simple language (B1 English).\n"
        logger.info(f"Prompt length: {len(prompt)} characters")
        
        try:
            client = openai.OpenAI(api_key=get_config('OPENAI_API_KEY'))
            start_time = time.time()
            logger.info(f"Starting OpenAI API call at {start_time}")
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=150,
                temperature=0.2
            )
            end_time = time.time()
            logger.info(f"OpenAI API call completed in {end_time - start_time:.2f}s")
            summary = response.choices[0].message.content
        except Exception as e:
            logger.error(f"OpenAI API call failed: {str(e)}", exc_info=True)
            summary = f"Error generating summary: {str(e)}"
    else:
        # BART summarization
        combined_content = " ".join([article.get('content', '') or article.get('title', '') for article in articles])
        if combined_content.strip():
            try:
                model_manager = ModelManager.get_instance()
                summarizer = model_manager.get_summarizer()
                summary = summarizer(combined_content, max_length=300, min_length=100, do_sample=False)
                summary_text = summary[0]['summary_text']
                sentences = re.split(r'(?<=[.!?])\s+', summary_text.strip())
                formatted_summary = '<br>'.join(sentences)
                logger.info("Summary generated successfully with sentence splitting")
                model_manager.clear_models()
                summary = formatted_summary
            except Exception as e:
                logger.error(f"Error generating summary: {e}")
                summary = "Error generating summary."
        else:
            logger.warning("No content available for summarization")
            summary = "No content available for summarization."
    
    return summary

def process_trending_articles(trending_data):
    """
    Process articles for trending topics: standardize, analyze sentiment, and summarize.
    
    Args:
        trending_data (dict): Dictionary of topics mapped to article lists.
    
    Returns:
        dict: Processed trending data with summaries and sentiment.
    """
    model_manager = ModelManager.get_instance()
    processed_data = {}

    for topic, articles in trending_data.items():
        logger.info(f"Processing articles for topic: {topic}")
        if not articles:
            processed_data[topic] = {"articles": [], "summary": "No articles found."}
            continue
        
        standardized_articles = process_articles(articles, source='Unknown')  # Adjust source as needed
        
        # Note: process_trending_articles seems to reference undefined functions; fixing here
        for article in standardized_articles:
            article['sentiment_score'] = analyze_sentiment(article['content'])
        
        summary = summarize_articles(standardized_articles, topic)
        
        processed_data[topic] = {
            "articles": standardized_articles[:3],  # Limit to 3 articles
            "summary": summary
        }
    
    return processed_data
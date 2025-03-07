# This file contains functions to process and standardize articles from various news APIs (e.g., NewsAPI.org, Guardian, NYT) into a uniform format, analyze sentiment using a preloaded DistilBERT model with batch processing, remove duplicates, filter relevant articles by TF-IDF, and summarize them using OpenAI's GPT-3.5-turbo. It also manages model loading and clearing via the ModelManager class.
 
import openai
import logging
import requests
from transformers import pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from config_prod import DEFAULT_TOP_N, RELEVANCE_THRESHOLD, ELECTION_RELEVANCE_THRESHOLD, OPENAI_API_KEY, SUMMARIZER_BY_GPT, WEIGHT_RELEVANCE, WEIGHT_POPULARITY
import torch
import re
import time

# Set up logging
logger = logging.getLogger(__name__)

class ModelManager:
    _instance = None
    _summarizer = None
    _sentiment_analyzer = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
            try:
                logger.info("Preloading sentiment analysis model at startup...")
                # Use a smaller model to reduce memory issues
                cls._instance._sentiment_analyzer = pipeline("sentiment-analysis", model="distilbert-base-uncased-finetuned-sst-2-english", device=-1)  # CPU, preloaded
                logger.info("Sentiment analysis model loaded successfully")
            except Exception as e:
                logger.error(f"Error loading sentiment analysis model: {e}")
                # Create a fallback model that returns neutral sentiment
                cls._instance._sentiment_analyzer = lambda text: [{'label': 'POSITIVE', 'score': 0.5}]
                logger.warning("Using fallback sentiment analyzer")
        return cls._instance

    def get_summarizer(self):
        if self._summarizer is None:
            try:
                logger.info("Loading summarization model...")
                self._summarizer = pipeline("summarization", model="facebook/bart-large-cnn")
                logger.info("Summarization model loaded successfully")
            except Exception as e:
                logger.error(f"Error loading summarization model: {e}")
                # Define a simple fallback summarizer
                def fallback_summarizer(text, **kwargs):
                    return [{"summary_text": "Summary not available due to technical issues."}]
                self._summarizer = fallback_summarizer
                logger.warning("Using fallback summarizer")
        return self._summarizer

    def get_sentiment_analyzer(self):
        return self._sentiment_analyzer  # Return preloaded model

    def clear_models(self):
        logger.info("Clearing models from memory...")
        self._summarizer = None
        # Keep _sentiment_analyzer loaded to avoid reload overhead
        torch.cuda.empty_cache() if torch.cuda.is_available() else None

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
                'title': article.title,
                'url': article.links.permalink,
                'content': article.body,
                'source': 'Aylien'
            }
            logger.debug(f"Standardized Aylien article {i+1}: {standardized_article['title']} (Source: Aylien)")
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
    
    # if standardized:
    #     model_manager = ModelManager.get_instance()
    #     sentiment_analyzer = model_manager.get_sentiment_analyzer()
    #     titles = [article['title'][:200] for article in standardized]
    #     contents = [article['content'][:200] for article in standardized]
        
    #     # Batch process titles and contents
    #     title_results = sentiment_analyzer(titles)
    #     content_results = sentiment_analyzer(contents)
        
    #     for article, title_result, content_result in zip(standardized, title_results, content_results):
    #         title_score = title_result['score'] if title_result['label'] == 'POSITIVE' else -title_result['score']
    #         content_score = content_result['score'] if content_result['label'] == 'POSITIVE' else -content_result['score']
    #         article['sentiment_score'] = 0.3 * title_score + 0.7 * content_score
    
    return standardized

def analyze_sentiment(text):
    """Analyze the sentiment of a text and return a normalized score between -1 and 1."""
    try:
        # Ensure text is not too large to avoid memory issues
        if not text or not isinstance(text, str):
            logger.warning(f"Invalid text for sentiment analysis: {type(text)}")
            return 0
            
        # Truncate text to avoid memory issues (512 tokens is typically safe)
        safe_text = text[:1000] if len(text) > 1000 else text
        
        model_manager = ModelManager.get_instance()
        sentiment_analyzer = model_manager.get_sentiment_analyzer()
        
        # Handle potentially large batch inputs
        result = sentiment_analyzer(safe_text)
        
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

def filter_relevant_articles(articles, query, top_n=DEFAULT_TOP_N, relevance_threshold=RELEVANCE_THRESHOLD):
    """Filter and sort articles by combined relevance and popularity scores."""
    logger.info(f"Starting detailed filtering for '{query}' with {len(articles)} articles")
    
    # Use a lower global threshold - simpler approach to fix the issue
    relevance_threshold = 0.01  # Very low threshold to allow most articles through
    logger.info(f"Using universal low threshold: {relevance_threshold}")
    
    # For debugging, print out all articles before filtering
    logger.info(f"Articles before filtering for '{query}':")
    for i, article in enumerate(articles):
        title = article.get('title', 'No title')
        source = article.get('source', 'Unknown')
        logger.info(f"Article {i+1}: '{title[:50]}...' - Source: {source}")
    
    texts = [article.get('content', '') or article.get('title', '') for article in articles]
    if not any(texts):
        logger.warning(f"No text content found in articles for '{query}'")
        return articles[:top_n]
    
    # Catch any exceptions during vectorization
    try:
        vectorizer = TfidfVectorizer()
        tfidf_matrix = vectorizer.fit_transform(texts)
        query_vector = vectorizer.transform([query])
        similarities = cosine_similarity(query_vector, tfidf_matrix).flatten()
    except Exception as e:
        logger.error(f"Error during vectorization: {str(e)}")
        # If vectorization fails, return all articles
        logger.info(f"Returning all articles due to vectorization error")
        return articles[:top_n]
    
    share_counts = [article.get('share_count', 0) for article in articles]
    max_share_count = max(share_counts) if share_counts else 0
    
    # Debug: log details about each article
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
    
    # If no articles passed the filter, return all articles instead
    if not article_scores:
        logger.warning(f"No articles passed relevance filter for '{query}'. Returning all articles instead.")
        return articles[:top_n]
    
    sorted_articles = sorted(article_scores, key=lambda x: x[1], reverse=True)
    relevant_articles = [article for article, _ in sorted_articles[:top_n]]
    
    logger.info(f"Final article count for '{query}' after filtering: {len(relevant_articles)}")
    return relevant_articles

if SUMMARIZER_BY_GPT:
    def summarize_articles(articles, query):
        logger.info(f"Summarizing {len(articles)} articles for query '{query}'")
        total_chars = sum(len(article.get('content', '')) for article in articles)
        logger.info(f"Total input character length: {total_chars}")
        
        articles_content = [article.get('content', '')[:150] or article.get('title', '')[:150] for article in articles]
        
        prompt = "You are an expert in summarizing news articles neutrally. Your task is to generate a balanced summary from the following articles, ensuring that you present a fair and unbiased view.\n\n"
        for i, content in enumerate(articles_content):
            prompt += f"Article {i+1}:\n{content}\n\n"
        # TODO: update deze 150 naar de var uit de config 
        prompt += "Please generate a summary that is approximately 150 words long, focusing on the main points and maintaining neutrality. The summary needs to be straight to the point and easy to read. Use simple language (B1 english).\n"
        logger.info(f"Prompt length: {len(prompt)} characters")
        
        try:
            client = openai.OpenAI(api_key=OPENAI_API_KEY)
            start_time = time.time()
            logger.info(f"Starting OpenAI API call at {start_time}")
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",  # Faster model
                messages=[{"role": "user", "content": prompt}],
                max_tokens=200,
                temperature=0.2
            )
            end_time = time.time()
            logger.info(f"OpenAI API call completed in {end_time - start_time:.2f}s")
            summary = response.choices[0].message.content
        except Exception as e:
            logger.error(f"OpenAI API call failed: {str(e)}", exc_info=True)
            summary = f"Error generating summary: {str(e)}"
        
        return summary
else:
    def summarize_articles(articles, query):
        """Summarize the combined content of articles and split into sentences."""
        logger.info(f"Summarizing {len(articles)} articles for query '{query}'")
        combined_content = " ".join([article.get('content', '') or article.get('title', '') for article in articles])
        if combined_content.strip():
            try:
                model_manager = ModelManager.get_instance()
                summarizer = model_manager.get_summarizer()
                summary = summarizer(combined_content, max_length=300, min_length=100, do_sample=False)
                summary_text = summary[0]['summary_text']
                # Split into sentences and join with <br> tags
                sentences = re.split(r'(?<=[.!?])\s+', summary_text.strip())
                formatted_summary = '<br>'.join(sentences)
                logger.info("Summary generated successfully with sentence splitting")
                # Clear models after use
                model_manager.clear_models()
                return formatted_summary
            except Exception as e:
                logger.error(f"Error generating summary: {e}")
                return "Error generating summary."
        else:
            logger.warning("No content available for summarization")
            return "No content available for summarization."
        


def process_trending_articles(trending_data):
    """
    Process articles for trending topics: standardize, analyze sentiment, and summarize.
    
    Args:
        trending_data (dict): Dictionary of topics mapped to article lists.
    
    Returns:
        dict: Processed trending data with summaries and sentiment.
    """
    model_manager = ModelManager()
    processed_data = {}

    for topic, articles in trending_data.items():
        logger.info(f"Processing articles for topic: {topic}")
        if not articles:
            processed_data[topic] = {"articles": [], "summary": "No articles found."}
            continue
        
        # Standardize articles (assuming standardize_articles exists)
        standardized_articles = standardize_articles(articles)
        
        # Analyze sentiment (assuming analyze_sentiment exists)
        articles_with_sentiment = analyze_sentiment(standardized_articles, model_manager)
        
        # Generate a summary for the topic (assuming summarize_articles exists)
        summary = summarize_articles(articles_with_sentiment, model_manager, prompt=f"Summarize news about {topic}")
        
        processed_data[topic] = {
            "articles": articles_with_sentiment[:3],  # Limit to 3 articles
            "summary": summary
        }
    
    return processed_data
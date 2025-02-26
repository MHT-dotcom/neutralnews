import openai
import logging
import requests
from transformers import pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from config import DEFAULT_TOP_N, RELEVANCE_THRESHOLD, OPENAI_API_KEY, SUMMARIZER_BY_GPT, WEIGHT_RELEVANCE, WEIGHT_POPULARITY

# Set up logging
logger = logging.getLogger(__name__)

# Initialize summarization pipeline
summarizer = pipeline("summarization", model="facebook/bart-large-cnn")

# Initialize sentiment analysis pipeline
sentiment_analyzer = pipeline("sentiment-analysis", model="distilbert-base-uncased-finetuned-sst-2-english")

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
    
    # Add sentiment analysis to each article
    for article in standardized:
        # Analyze sentiment of both title and content
        title_sentiment = analyze_sentiment(article['title'])
        content_sentiment = analyze_sentiment(article['content'])
        # Weighted average: title (30%) and content (70%)
        article['sentiment_score'] = (0.3 * title_sentiment + 0.7 * content_sentiment)
    
    return standardized

def analyze_sentiment(text):
    """Analyze the sentiment of a text and return a normalized score between -1 and 1."""
    try:
        result = sentiment_analyzer(text[:512])  # Limit text length for efficiency
        # Convert POSITIVE/NEGATIVE to numerical score
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
            combined_score = similarity * WEIGHT_RELEVANCE + normalized_share_count * WEIGHT_POPULARITY
            article_scores.append((article, combined_score))
    
    sorted_articles = sorted(article_scores, key=lambda x: x[1], reverse=True)
    relevant_articles = [article for article, _ in sorted_articles[:top_n]]
    
    return relevant_articles

if SUMMARIZER_BY_GPT:
    def summarize_articles(articles, query):
        """Summarize the combined content of articles using the OpenAI API."""
        logger.info(f"Summarizing {len(articles)} articles for query '{query}'")
        articles_content = [article.get('content', '') or article.get('title', '') for article in articles]
        
        prompt = "You are an expert in summarizing news articles neutrally. Your task is to generate a balanced summary from the following articles, ensuring that you present a fair and unbiased view.\n\n"
        for i, content in enumerate(articles_content):
            prompt += f"Article {i+1}:\n{content}\n\n"
        prompt += "Please generate a summary that is approximately 150 words long, focusing on the main points and maintaining neutrality. The summary needs to be straight to the point and easy to read. Use simple language (B1 english).\n"
        
        try:
            client = openai.OpenAI(
                api_key=OPENAI_API_KEY
            )
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=300,
                temperature=0.2
            )
            summary = response.choices[0].message.content
        except Exception as e:
            summary = f"Error generating summary: {str(e)}"
        
        return summary
else:
    def summarize_articles(articles, query):
        """Summarize the combined content of articles and split into sentences."""
        logger.info(f"Summarizing {len(articles)} articles for query '{query}'")
        combined_content = " ".join([article.get('content', '') or article.get('title', '') for article in articles])
        if combined_content.strip():
            try:
                summary = summarizer(combined_content, max_length=300, min_length=100, do_sample=False)
                summary_text = summary[0]['summary_text']
                # Split into sentences and join with <br> tags
                sentences = re.split(r'(?<=[.!?])\s+', summary_text.strip())
                formatted_summary = '<br>'.join(sentences)
                logger.info("Summary generated successfully with sentence splitting")
                return formatted_summary
            except Exception as e:
                logger.error(f"Error generating summary: {e}")
                return "Error generating summary."
        else:
            logger.warning("No content available for summarization")
            return "No content available for summarization."
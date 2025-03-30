from datetime import datetime, timedelta
import requests
import os
import json

def test_newsapi_ai(query):
    print(f"\nTesting NewsAPI.ai with query: {query}")
    api_key = os.getenv('NEWSAPI_AI_KEY')
    if not api_key:
        print("NewsAPI.ai key not available")
        return
    
    url = "https://eventregistry.org/api/v1/article/getArticles"
    from_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    payload = {
        "action": "getArticles",
        "keyword": query,
        "dateStart": from_date,
        "dateEnd": datetime.now().strftime('%Y-%m-%d'),
        "articlesCount": 5,
        "resultType": "articles",
        "apiKey": api_key,
        "lang": "eng"
    }
    
    try:
        response = requests.post(url, json=payload, timeout=15)
        data = response.json()
        articles = data.get('articles', {}).get('results', [])
        print(f"NewsAPI.ai returned {len(articles)} articles")
    except Exception as e:
        print(f"Error: {e}")

def test_newsdata_io(query):
    print(f"\nTesting NewsData.io with query: {query}")
    api_key = os.getenv('NEWSDATAIO_API_KEY')
    if not api_key:
        print("NewsData.io key not available")
        return
    
    url = "https://newsdata.io/api/1/news"
    params = {
        "apikey": api_key,
        "q": query,
        "language": "en",
        "size": 5
    }
    
    try:
        response = requests.get(url, params=params, timeout=15)
        data = response.json()
        articles = data.get('results', [])
        print(f"NewsData.io returned {len(articles)} articles")
    except Exception as e:
        print(f"Error: {e}")

print("Running test searches to check active APIs...")
test_newsapi_ai("climate change")
test_newsapi_ai("artificial intelligence")
test_newsapi_ai("ukraine")

print("\nChecking NewsData.io API...")
test_newsdata_io("climate change")
test_newsdata_io("artificial intelligence")
test_newsdata_io("ukraine") 
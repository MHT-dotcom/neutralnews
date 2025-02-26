# Neutral News

An AI-powered news aggregator that provides balanced coverage from multiple perspectives.

## Features
- Fetches articles from multiple news sources
- AI-powered summarization
- Sentiment analysis
- Source diversity tracking
- Balance score calculation

## Setup

1. Clone the repository:
```bash
git clone https://github.com/MHT-dotcom/neutralnews.git
cd neutralnews
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up configuration:
```bash
cp config.template.py config.py
# Edit config.py with your API keys
```

5. Run the application:
```bash
# Development
python app.py

# Production
gunicorn app:app --workers 4 --bind 0.0.0.0:$PORT
```

## API Keys Required
- NewsAPI.org
- The Guardian
- GNews
- New York Times
- OpenAI
- Mediastack
- NewsAPI.ai
- Aylien News

## Contributing
Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

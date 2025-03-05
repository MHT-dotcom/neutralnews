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

4. Run the application:
```bash
# Local Development (uses config.py with your API keys)
python run_local.py

# Production (uses environment variables)
gunicorn app:app --bind 0.0.0.0:$PORT --workers 1 --timeout 120
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

## Local Development vs Production
- **Local Development**: Uses `config.py` which contains your API keys (this file is gitignored)
- **Production**: Uses environment variables for configuration

## Testing
To run tests:
```bash
# Run all tests
pytest

# Run a specific test file
pytest tests/test_comprehensive.py
```

## Contributing
Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

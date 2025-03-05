# Setting Up Neutral News on Render

This guide will help you set up the required environment variables in Render to ensure Neutral News works correctly.

## API Keys Configuration

1. Go to your Render dashboard
2. Select the Neutral News service
3. Navigate to the "Environment" tab
4. Add the following environment variables:

### Required API Keys:

- `NEWSAPI_ORG_KEY`: Your News API key from newsapi.org
- `GUARDIAN_API_KEY`: Your Guardian API key
- `OPENAI_API_KEY`: Your OpenAI API key for summarization

### Optional API Keys:

- `GNEWS_API_KEY`: Your GNews API key
- `NYT_API_KEY`: Your New York Times API key
- `AYLIEN_APP_ID`: Your Aylien App ID
- `AYLIEN_API_KEY`: Your Aylien API key
- `MEDIASTACK_API_KEY`: Your Mediastack API key
- `NEWSAPI_AI_KEY`: Your NewsAPI.ai key

### Additional Environment Variables:

- `PORT`: (Automatically set by Render, but can be overridden)
- `FLASK_ENV`: Set to `production` for Render deployments
- `FLASK_DEBUG`: Set to `0` for production, `1` for debugging
- `RENDER`: Set to `true` to indicate Render environment

## Monitoring Logs

After setting up the environment variables:

1. Redeploy your application
2. Go to the "Logs" tab in Render dashboard
3. Check for "API Key Status" log entries to confirm keys are detected
4. Verify trending topics are being fetched or fallbacks are being used

## Troubleshooting

- If Google Trends is returning 404 errors, don't worry - the application will use cached or fallback topics
- If news sources show "disabled or missing API key", double-check the API key spelling and validity
- If the application shows "No open ports detected", ensure the `PORT` environment variable is properly set 
# Neutral News Deployment Guide

This guide covers deploying the Neutral News application to Render.com.

## Pre-Deployment Checklist

1. Run the validation script to ensure all dependencies and configurations are correct:

```bash
python deploy_checks.py
```

2. Make sure all API keys are available and working.

3. Test the application locally with production settings:

```bash
FLASK_ENV=production python app.py
```

## Deployment Steps for Render.com

### 1. Set Up Your Render Account

1. Create an account at [Render.com](https://render.com/)
2. Connect your GitHub repository

### 2. Configure Environment Variables

Set the following environment variables in the Render.com dashboard:

- `APP_VERSION`: Version number (e.g., `1.0.0`)
- `FLASK_ENV`: `production`
- `DB_PATH`: `/data/search_db.sqlite`
- `NEWSAPI_ORG_KEY`: Your NewsAPI.org API key
- `GUARDIAN_API_KEY`: Your Guardian API key
- `GNEWS_API_KEY`: Your GNews API key
- `NYT_API_KEY`: Your New York Times API key
- `MEDIASTACK_API_KEY`: Your Mediastack API key
- `NEWSDATA_API_KEY`: Your NewsData API key
- `GROK_API_KEY`: Your Grok API key

### 3. Configure Persistent Disk

1. Create a 10GB persistent disk in Render.com
2. Mount it at `/data`

### 4. Deploy Using the Blueprint

1. Use the `render.yaml` file to deploy the service
2. Or create a new Web Service with these settings:
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn app:app --workers=3 --timeout=120`
   - Health Check Path: `/health`

### 5. Verify Deployment

1. Check the application logs for any errors
2. Visit the `/health` endpoint to verify the service is running correctly
3. Test the main functionality with a sample search

## Monitoring and Maintenance

### Monitoring

- Use the `/health` endpoint for regular health checks
- Set up alerts in Render.com for failed health checks

### Database Maintenance

- Run database backups periodically 
- Check disk usage with monitoring tools

### Troubleshooting

If the application fails to start:

1. Check the Render.com logs for error messages
2. Verify all environment variables are set correctly
3. Ensure the persistent disk is mounted and writable
4. Check the `/health` endpoint for specific component failures

## Production Best Practices

1. **Scaling**: Start with 1 instance and scale based on traffic
2. **Security**: Regularly rotate API keys
3. **Performance**: Monitor response times and optimize as needed
4. **Reliability**: Set up redundancy when possible
5. **Monitoring**: Set up logging and alerts for critical errors

## Rollback Procedure

If a deployment fails:

1. In the Render.com dashboard, select the previous working deployment
2. Click "Rollback to this deploy"
3. Verify the application is working correctly after rollback 
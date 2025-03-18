# Render.com Deployment Checklist

## Pre-Deployment Steps

1. **Update render.yaml** ✅
   - Health check path is now correctly set to `/health`
   - Resource allocation appears adequate (1x CPU, 1GB RAM)
   - Environment variables properly listed for sync

2. **Dependencies** ✅
   - Added missing `deep-translator==1.11.4` to requirements.txt
   - Gunicorn properly configured in render.yaml for production server

3. **Environment Variables** ⚠️
   - Ensure all API keys are set up in Render.com Dashboard:
     - NEWSAPI_ORG_KEY
     - GUARDIAN_API_KEY
     - AYLIEN_APP_ID
     - AYLIEN_API_KEY
     - GNEWS_API_KEY
     - NEWSAPI_AI_KEY
     - MEDIASTACK_API_KEY
     - OPENAI_API_KEY
     - SHARECOUNT_API_KEY
     - NYT_API_KEY
     - GROK_API_KEY (for trending topics)

4. **Directories** ✅
   - App creates required data directories on startup:
     ```python
     # From app.py
     os.makedirs(BASE_PATH, exist_ok=True)
     os.makedirs(IMAGE_DIR, exist_ok=True)
     ```

5. **Security Fixes** ✅
   - Image route protection implemented to prevent path traversal attacks
   - Only PNG files are served from the image directory

## Deployment Process

1. **Push code to GitHub repository** 
   - Ensure all changes are committed and pushed
   - Verify branch is correct (typically `main` or `master`)

2. **Connect to Render.com**
   - Create a new Web Service
   - Connect to your GitHub repository
   - Select "Use render.yaml" configuration

3. **Configure Environment Variables**
   - Add all required API keys through the Render.com dashboard
   - Double-check for typos or missing values

4. **Deploy and Monitor**
   - Monitor build logs for errors
   - Verify health check is passing
   - Check application logs for any issues

## Post-Deployment Verification

1. **API Functionality**
   - Test all news providers are working
   - Verify translation feature with `deep-translator`
   - Check sentiment analysis functionality

2. **Image Generation & Security**
   - Test image generation and storage
   - Verify secure image serving with PNG restriction
   - Test protection against path traversal attacks

3. **Performance Monitoring**
   - Watch resource usage (memory, CPU)
   - Check response times for end-user
   - Inspect error logs for any new issues

## Common Issues & Solutions

1. **Memory Issues**
   - If you encounter memory limit errors, consider:
     - Reducing batch sizes in news fetching
     - Lowering `MAX_ARTICLES_PER_API` in config_prod.py
     - Upgrading to higher memory tier on Render.com

2. **API Key Problems**
   - Verify keys are correctly set in Render.com (not saved with "quotes")
   - Check for whitespace in key values
   - Ensure API services are active and accounts in good standing

3. **Database Errors**
   - The app uses SQLite, which is stored in `/data` directory
   - Ensure proper permissions for file creation
   - For persistent database across deployments, consider using Render disk 
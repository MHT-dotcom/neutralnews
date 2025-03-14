import requests
import os
import json
import logging
import certifi

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def test_grok_api():
    """Test the Grok API with direct requests"""
    # Get API key from environment
    api_key = os.environ.get("GROK_API_KEY", "")
    if not api_key:
        logger.error("No GROK_API_KEY found in environment")
        return
    
    logger.info(f"API Key (truncated): {api_key[:8]}...{api_key[-8:]}")
    
    # API endpoint
    url = "https://api.x.ai/v1/chat/completions"
    
    # Headers
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    # Simple payload
    payload = {
        "model": "grok-1",
        "messages": [
            {"role": "user", "content": "What are the top 3 trending news topics today? Format as a JSON list."}
        ],
        "temperature": 0.3,
        "max_tokens": 500
    }
    
    try:
        # Make request using certifi's trusted certificates
        logger.info(f"Making request to {url}")
        response = requests.post(
            url, 
            json=payload, 
            headers=headers, 
            timeout=15,
            verify=certifi.where()  # Use certifi's certificates
        )
        
        # Log response
        logger.info(f"Response status: {response.status_code}")
        logger.info(f"Response headers: {dict(response.headers)}")
        
        # Check if response is successful
        if response.status_code == 200:
            data = response.json()
            logger.info("Success! Got valid response")
            logger.info(f"Response: {json.dumps(data, indent=2)}")
        else:
            try:
                error = response.json()
                logger.error(f"Error response: {json.dumps(error, indent=2)}")
            except:
                logger.error(f"Raw error response: {response.text[:500]}")
    
    except Exception as e:
        logger.error(f"Exception occurred: {e}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    test_grok_api() 
import stability_sdk.interfaces.gooseai.generation.generation_pb2 as generation_pb2
from stability_sdk import client
from PIL import Image
import io
import os
import logging
import requests
from flask import current_app
import image_cache
# Import the budget control module
import budget_control

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
if not logger.handlers:
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    logger.addHandler(ch)

def generate_with_stability(prompt, size=1024):
    """Generate image using Stability AI SDK v0.8.6 and return PIL Image"""
    logger.info("=== Starting Stability AI generation ===")
    logger.info(f"Prompt used for Stability AI: '{prompt}'")
    try:
        logger.info(f"Stability API key: {'Set' if os.getenv('STABILITY_API_KEY') else 'Not set'}")
        stability_api = client.StabilityInference(
            key=os.getenv('STABILITY_API_KEY', ""),
            verbose=True,
        )
        answers = stability_api.generate(
            prompt=prompt,
            width=size,
            height=size,
        )
        logger.info("Generation request sent")
        for resp in answers:
            for artifact in resp.artifacts:
                if artifact.type == generation_pb2.ArtifactType.ARTIFACT_IMAGE:
                    img = Image.open(io.BytesIO(artifact.binary))
                    logger.info("Image generated successfully with Stability AI")
                    return img
        logger.error("No image artifact found in response")
        return None
    except Exception as e:
        logger.error(f"Stability AI generation failed: {str(e)}", exc_info=True)
        return None

def generate_with_openai(prompt, size=1024):
    """Generate image using OpenAI v1.0.0+ and return PIL Image"""
    logger.info("=== Starting OpenAI generation ===")
    logger.info(f"Prompt used for OpenAI: '{prompt}'")
    try:
        from openai import OpenAI
        logger.info(f"OpenAI API key: {'Set' if os.getenv('OPENAI_API_KEY') else 'Not set'}")
        client = OpenAI(api_key=os.getenv('OPENAI_API_KEY', ""))
        response = client.images.generate(
            prompt=prompt,
            n=1,
            size=f"{size}x{size}"
        )
        
        image_url = response.data[0].url
        response = requests.get(image_url)
        logger.info(f"OpenAI image URL: {image_url[:50]}...")
        if response.status_code == 200:
            logger.info("Image generated successfully with OpenAI")
            return Image.open(io.BytesIO(response.content))
        logger.error(f"Failed to download image: HTTP {response.status_code}")
        return None
    except ImportError:
        logger.error("OpenAI library not installed; skipping OpenAI generation")
        return None
    except Exception as e:
        logger.error(f"OpenAI generation failed: {str(e)}", exc_info=True)
        return None

def generate_and_save_image(summary, query, include_images=True):
    """Generate and save an image for the given summary and query."""
    logger.info(f"generate_and_save_image called with include_images={include_images}")
    logger.info(f"Summary: '{summary[:50]}...' if len(summary) > 50 else summary)")
    logger.info(f"Query: '{query}'")
    
    try:
        if not include_images:
            logger.info("Image generation skipped due to include_images=False")
            return None, False
        
        # Default values for parameters not in the function signature
        force_regenerate = False
        quality = 85
        max_size = 1024
        
        # Get image directory from app config with fallback
        try:
            image_dir = current_app.config["IMAGE_DIRECTORY"]
        except (KeyError, RuntimeError):
            # Fallback to a default path
            image_dir = os.path.join(os.path.dirname(__file__), "data", "images")
            os.makedirs(image_dir, exist_ok=True)
            logger.warning(f"IMAGE_DIRECTORY not in app config, using fallback: {image_dir}")
        
        # Get cache instance
        try:
            # Try to get the DB path from app config
            db_path = current_app.config.get("DB_PATH")
            if not db_path:
                # Fallback to environment variable
                db_path = os.environ.get("DB_PATH")
                if not db_path:
                    # Last resort fallback
                    db_path = os.path.join(os.path.dirname(__file__), "data", "search_db.sqlite")
            
            cache = image_cache.get_instance(
                db_path=db_path,
                image_dir=image_dir
            )
        except Exception as e:
            logger.error(f"Error initializing image cache: {str(e)}")
            # If cache fails, continue without it
            cache = None
            
        # Function to get cached image
        def get_cached_image(query):
            if cache:
                cached_path = cache.get_image_path(query)
                if cached_path and os.path.exists(cached_path):
                    return cached_path
            return None
        
        # Check if we already have a cached image
        cached_image = get_cached_image(query)
        if cached_image:
            logger.info(f"Using cached image for query: {query}")
            return cached_image, True
        
        logger.info(f"Generating new image for query: {query}")
        
        # Clean the query for use as a filename
        clean_query = "".join(c if c.isalnum() else "-" for c in query.lower())
        
        # Check if the image is in our cache (unless force regenerate)
        if not force_regenerate:
            cached_path = cache.get_image_path(query) if cache else None
            if cached_path:
                logger.info(f"Image found in cache: {cached_path}")
                
                # Check if we need to optimize an existing image
                if cached_path.endswith('.png') and os.path.exists(cached_path):
                    # Get size in KB
                    file_size_kb = os.path.getsize(cached_path) / 1024
                    if file_size_kb > 500:  # If larger than 500KB, optimize it
                        try:
                            webp_path = cached_path.replace('.png', '.webp')
                            img = Image.open(cached_path)
                            
                            # Resize if needed
                            if img.width > max_size or img.height > max_size:
                                img.thumbnail((max_size, max_size), Image.LANCZOS)
                                
                            # Save as WebP for better compression
                            img.save(webp_path, 'WEBP', quality=quality)
                            
                            # If WebP file is smaller, update cache
                            if os.path.getsize(webp_path) < os.path.getsize(cached_path):
                                logger.info(f"Optimized image from {file_size_kb:.1f}KB to {os.path.getsize(webp_path) / 1024:.1f}KB")
                                if cache:
                                    cache.add_image(query, webp_path)
                                return webp_path, True
                            else:
                                # Remove WebP if it's not smaller
                                os.remove(webp_path)
                        except Exception as e:
                            logger.warning(f"Error optimizing cached image: {str(e)}")
                
                return cached_path, True
        
        # Standard path for the image, using WebP instead of PNG for better compression
        image_path = os.path.join(image_dir, f"{clean_query}.webp")
        
        # Check if image already exists on disk (unless force regenerate)
        if not force_regenerate and os.path.exists(image_path):
            logger.info(f"Image already exists at {image_path}")
            # Add to cache for future fast access
            if cache:
                cache.add_image(query, image_path)
            return image_path, True
        
        # Ensure the images directory exists
        os.makedirs(os.path.dirname(image_path), exist_ok=True)
        logger.info(f"Images directory ensured: {os.path.dirname(image_path)}")

        # === CHECK BUDGET BEFORE GENERATING ===
        # Check if we have budget available for this month
        if not budget_control.is_budget_available():
            logger.warning(f"Monthly budget limit reached for Stability AI. Disabling image generation completely.")
            # Return None to indicate no image, like when include_images=False
            return None, False

        # Generate prompt from summary
        prompt = f"A digital illustration of: {summary}"
        logger.info(f"Generating image with prompt: {prompt}")
        
        # Try Stability AI first
        image = generate_with_stability(prompt)
        if image:
            # Resize the image if needed
            if image.width > max_size or image.height > max_size:
                image.thumbnail((max_size, max_size), Image.LANCZOS)
                
            # Save the image as WebP for better compression
            image.save(image_path, 'WEBP', quality=quality)
            logger.info(f"Image saved to {image_path} via Stability AI")
            
            # Verify file exists and log size
            file_exists = os.path.exists(image_path)
            logger.info(f"File exists after save: {file_exists}")
            
            if file_exists:
                file_size_kb = os.path.getsize(image_path) / 1024
                logger.info(f"File size: {file_size_kb:.1f}KB")
                
                # Add to cache for future fast access
                if cache:
                    cache.add_image(query, image_path)
                
                # Log usage since we successfully generated an image
                budget_control.increment_usage(query)
                return image_path, True
            else:
                logger.error(f"File does not exist after save: {image_path}")
        
        # Fallback to OpenAI
        image = generate_with_openai(prompt)
        if image:
            # Resize the image if needed
            if image.width > max_size or image.height > max_size:
                image.thumbnail((max_size, max_size), Image.LANCZOS)
                
            # Save as WebP for better compression
            image.save(image_path, 'WEBP', quality=quality)
            logger.info(f"Image saved to {image_path} via OpenAI")
            logger.info(f"File exists after save: {os.path.exists(image_path)}")
            logger.info(f"File size: {os.path.getsize(image_path) / 1024:.1f}KB")
            
            # Add to cache
            cache.add_image(query, image_path)
            return image_path, True
        
        logger.error(f"Failed to generate image for query: {query}")
        return None, False
    except Exception as e:
        logger.error(f"Error in generate_and_save_image: {str(e)}", exc_info=True)
        return None, False

def pregenerate_trending_images(trending_topics):
    """
    Pre-generate images for trending topics in the background.
    
    Args:
        trending_topics (list): List of [headline, keywords] pairs
    """
    try:
        # Use imported Flask app when no current app context
        from flask import current_app
        
        # Get cache instance
        cache = image_cache.get_instance(
            db_path=current_app.config.get("DB_PATH"),
            image_dir=current_app.config.get("IMAGE_DIRECTORY")
        )
        
        # Start pre-generation
        cache.pregenerate_trending_images(trending_topics, generate_and_save_image)
        logger.info(f"Started background image pre-generation for {len(trending_topics)} trending topics")
    except Exception as e:
        logger.error(f"Error starting image pre-generation: {str(e)}")
        # Log full traceback for debugging
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")

def optimize_image_storage(max_age_days=30, target_size_mb=500):
    """
    Optimize storage by removing old/unused images and compressing large ones.
    
    Args:
        max_age_days (int): Maximum age for unused images
        target_size_mb (int): Target directory size in MB
    """
    try:
        if current_app:
            cache = image_cache.get_instance(
                db_path=current_app.config.get("DB_PATH"),
                image_dir=current_app.config.get("IMAGE_DIRECTORY")
            )
            
            # Run optimization
            cache.optimize_storage(max_age_days, target_size_mb)
            logger.info("Completed image storage optimization")
        else:
            logger.warning("Cannot optimize images: no Flask application context")
    except Exception as e:
        logger.error(f"Error during image optimization: {str(e)}")

def get_image_cache_stats():
    """Get statistics about the image cache performance."""
    try:
        if current_app:
            cache = image_cache.get_instance()
            return cache.get_stats()
        return {"error": "No Flask application context"}
    except Exception as e:
        logger.error(f"Error getting cache stats: {str(e)}")
        return {"error": str(e)}

if __name__ == "__main__":
    from flask import Flask
    app = Flask(__name__)
    app.config["IMAGE_DIRECTORY"] = os.path.join(os.path.dirname(__file__), "static", "images")
    app.config["DB_PATH"] = os.path.join(os.path.dirname(__file__), "data", "search_db.sqlite")
    with app.app_context():
        test_query = "Test-Query"
        test_summary = "A futuristic cityscape glowing with neon lights under a starry sky."
        image_path, status = generate_and_save_image(test_summary, test_query)
        print(f"Image Path: {image_path}, Status: {status}")
        
        # Test cache stats
        print(f"Cache Stats: {get_image_cache_stats()}")
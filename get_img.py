import stability_sdk.interfaces.gooseai.generation.generation_pb2 as generation_pb2
from stability_sdk import client
from PIL import Image
import io
import os
import logging
import requests
from flask import current_app
import image_cache

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

def generate_and_save_image(query, summary, force_regenerate=False, quality=85, max_size=1024):
    """
    Generate and save an image based on summary, using efficient caching strategy.
    
    Args:
        query (str): The search query
        summary (str): The article summary to base the image on
        force_regenerate (bool): Whether to regenerate the image even if it exists
        quality (int): JPEG quality for saved images (1-100)
        max_size (int): Maximum dimension (width or height) for the image
        
    Returns:
        tuple: (image_path, status) where image_path is the path to the image and status is True if successful
    """
    logger.info(f"=== Starting image generation for query: '{query}' ===")
    
    # Clean the query for use as a filename
    clean_query = "".join(c if c.isalnum() else "-" for c in query.lower())
    image_dir = current_app.config["IMAGE_DIRECTORY"]
    
    # Get cache instance
    cache = image_cache.get_instance(
        db_path=current_app.config.get("DB_PATH"),
        image_dir=image_dir
    )
    
    # Check if the image is in our cache (unless force regenerate)
    if not force_regenerate:
        cached_path = cache.get_image_path(query)
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
        cache.add_image(query, image_path)
        return image_path, True
    
    # Ensure the images directory exists
    os.makedirs(os.path.dirname(image_path), exist_ok=True)
    logger.info(f"Images directory ensured: {os.path.dirname(image_path)}")

    # Generate prompt from summary
    prompt = f"A digital illustration of: {summary}"
    logger.info(f"Generating image with prompt: {prompt}")
    
    # Try Stability AI first
    image = generate_with_stability(prompt)
    if image:
        # Resize the image if needed
        if image.width > max_size or image.height > max_size:
            image.thumbnail((max_size, max_size), Image.LANCZOS)
            
        # Save as WebP for better compression
        image.save(image_path, 'WEBP', quality=quality)
        logger.info(f"Image saved to {image_path} via Stability AI")
        logger.info(f"File exists after save: {os.path.exists(image_path)}")
        logger.info(f"File size: {os.path.getsize(image_path) / 1024:.1f}KB")
        
        # Add to cache
        cache.add_image(query, image_path)
        return image_path, True
    
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

def pregenerate_trending_images(trending_topics):
    """
    Pre-generate images for trending topics in the background.
    
    Args:
        trending_topics (list): List of [headline, keywords] pairs
    """
    try:
        # Get cache instance
        if current_app:
            cache = image_cache.get_instance(
                db_path=current_app.config.get("DB_PATH"),
                image_dir=current_app.config.get("IMAGE_DIRECTORY")
            )
            
            # Start pre-generation
            cache.pregenerate_trending_images(trending_topics, generate_and_save_image)
            logger.info(f"Started background image pre-generation for {len(trending_topics)} trending topics")
        else:
            logger.warning("Cannot pregenerate images: no Flask application context")
    except Exception as e:
        logger.error(f"Error starting image pre-generation: {str(e)}")

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
        image_path, status = generate_and_save_image(test_query, test_summary)
        print(f"Image Path: {image_path}, Status: {status}")
        
        # Test cache stats
        print(f"Cache Stats: {get_image_cache_stats()}")
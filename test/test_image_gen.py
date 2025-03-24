import os
import sys
import logging
from app import create_app
from get_img import generate_and_save_image
from image_cache import get_instance

# Set up logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    # Create and configure the app
    app = create_app()
    
    with app.app_context():
        # Print config keys for debugging
        logger.info("Available config keys:")
        for key in app.config:
            if isinstance(app.config[key], str) and not key.startswith('_'):
                logger.info(f"{key}: {app.config[key]}")
        
        # Manually set the image directory
        data_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
        image_dir = os.path.join(data_path, "images")
        if not os.path.exists(image_dir):
            os.makedirs(image_dir, exist_ok=True)
            
        app.config["IMAGE_DIRECTORY"] = image_dir
        logger.info(f"Manually set IMAGE_DIRECTORY to: {image_dir}")
        
        # Test parameters
        query = "climate"
        summary = "Climate change and global warming effects on the environment"
        
        # Test image generation with optimization
        logger.info(f"Testing image generation for '{query}'")
        try:
            result = generate_and_save_image(
                query=query, 
                summary=summary,
                force_regenerate=True,  # Force regeneration to test new code
                quality=85,             # Good quality but optimized
                max_size=800            # Reduced from default 1024
            )
            
            image_path, status = result
            logger.info(f"Generated image: {image_path}, Status: {status}")
            
            if status and image_path:
                # Get file size in KB
                file_size_kb = os.path.getsize(image_path) / 1024
                logger.info(f"Image size: {file_size_kb:.2f} KB")
                
                # Test cache optimization
                cache = get_instance(
                    db_path=app.config.get("DB_PATH"),
                    image_dir=app.config.get("IMAGE_DIRECTORY")
                )
                
                logger.info("Testing cache optimization...")
                cache.optimize_storage(max_age_days=30, target_size_mb=500)
                
                # Check if WebP version exists if it was a PNG
                if image_path.endswith('.png'):
                    webp_path = image_path.replace('.png', '.webp')
                    if os.path.exists(webp_path):
                        webp_size_kb = os.path.getsize(webp_path) / 1024
                        logger.info(f"WebP version created: {webp_path}")
                        logger.info(f"WebP size: {webp_size_kb:.2f} KB")
                        logger.info(f"Size reduction: {(1 - webp_size_kb/file_size_kb) * 100:.2f}%")
                    else:
                        logger.info("No WebP version created")
            else:
                logger.error("Image generation failed")
        except Exception as e:
            logger.error(f"Error generating image: {str(e)}", exc_info=True)
import os
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setLevel(logging.INFO)
logger.addHandler(handler)

# Only check the specific file we know exists
file_path = "/Users/maxteeuwen/neutralnews/get_img.py"

logger.info("=== Detailed File Content Check ===")
logger.info(f"Checking file: {file_path}")

try:
    with open(file_path, 'r') as f:
        content = f.read()
        logger.info("\nFirst 500 characters of file:")
        logger.info(content[:500])
        
        logger.info("\nChecking for stability_sdk references:")
        for i, line in enumerate(content.split('\n'), 1):
            if 'stability_sdk' in line:
                logger.info(f"Found stability_sdk reference on line {i}: {line.strip()}")
            
    # Check for __pycache__
    cache_dir = os.path.join(os.path.dirname(file_path), '__pycache__')
    if os.path.exists(cache_dir):
        logger.info(f"\nFound __pycache__ directory: {cache_dir}")
        cache_files = os.listdir(cache_dir)
        logger.info(f"Cache files: {cache_files}")
        
except Exception as e:
    logger.error(f"Error reading file: {e}")

logger.info("\n=== End Detailed Check ===")

logger.info("=== End Diagnostic ===") 
import os
import sys
import logging
import importlib

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def diagnose_app_structure():
    """Diagnose the application structure and import paths"""
    
    # Log environment information
    logger.info("=== Environment Information ===")
    logger.info(f"Python version: {sys.version}")
    logger.info(f"Current working directory: {os.getcwd()}")
    logger.info(f"PYTHONPATH: {os.environ.get('PYTHONPATH', 'Not set')}")
    logger.info(f"Sys path: {sys.path}")
    
    # Check app directory structure
    logger.info("\n=== Directory Structure ===")
    try:
        app_contents = os.listdir('app')
        logger.info(f"Contents of app directory: {app_contents}")
    except Exception as e:
        logger.error(f"Error listing app directory: {e}")
    
    # Attempt to import app module
    logger.info("\n=== Import Attempts ===")
    try:
        logger.info("Attempting to import 'app' module...")
        app_module = importlib.import_module('app')
        logger.info(f"Successfully imported app module: {app_module}")
        logger.info(f"App module contents: {dir(app_module)}")
    except Exception as e:
        logger.error(f"Error importing app module: {e}")
    
    # Try to find Flask app instance
    try:
        logger.info("\nLooking for Flask app instance...")
        from app import app
        logger.info(f"Found Flask app instance: {app}")
    except Exception as e:
        logger.error(f"Error finding Flask app instance: {e}")

if __name__ == "__main__":
    logger.info("Starting app structure diagnosis...")
    diagnose_app_structure()
    logger.info("Diagnosis complete") 
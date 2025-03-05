"""
Diagnostic script to validate module import and path assumptions for Render deployment
"""

import os
import sys
import logging
import importlib.util
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='[%(asctime)s] %(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)

def check_file_structure():
    """Check the file structure and module layout"""
    logger.info("=== Checking File Structure ===")
    
    # Log current working directory and Python path
    logger.info(f"Current working directory: {os.getcwd()}")
    logger.info(f"PYTHONPATH: {os.environ.get('PYTHONPATH', 'Not set')}")
    logger.info(f"sys.path: {sys.path}")
    
    # Check for app.py or similar files
    root_dir = Path('.')
    logger.info("\nSearching for potential app files:")
    for file in root_dir.rglob('*.py'):
        logger.info(f"Found Python file: {file}")

def check_module_imports():
    """Test importing the app module and object"""
    logger.info("\n=== Checking Module Imports ===")
    
    # Try different import paths
    import_attempts = [
        ('app', 'app'),
        ('app', 'application'),
        ('app.app', 'app'),
        ('run', 'app'),
    ]
    
    for module_name, object_name in import_attempts:
        try:
            logger.info(f"\nAttempting to import {object_name} from {module_name}")
            module = importlib.import_module(module_name)
            logger.info(f"Successfully imported module {module_name}")
            logger.info(f"Module location: {module.__file__}")
            logger.info(f"Module contents: {dir(module)}")
            
            if hasattr(module, object_name):
                obj = getattr(module, object_name)
                logger.info(f"Found {object_name} object: {type(obj)}")
                if hasattr(obj, 'config'):
                    logger.info(f"App config keys: {obj.config.keys()}")
            else:
                logger.warning(f"Module {module_name} does not contain {object_name}")
                
        except ImportError as e:
            logger.error(f"Import error for {module_name}: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error importing {module_name}: {str(e)}")

def check_wsgi_compatibility():
    """Check WSGI/ASGI compatibility of the app object"""
    logger.info("\n=== Checking WSGI/ASGI Compatibility ===")
    
    try:
        from app import app
        
        # Check for WSGI compatibility
        if hasattr(app, 'wsgi_app'):
            logger.info("App has wsgi_app attribute (Flask/WSGI compatible)")
        else:
            logger.warning("App missing wsgi_app attribute")
            
        # Check for ASGI compatibility
        if hasattr(app, 'asgi_app'):
            logger.info("App has asgi_app attribute (ASGI compatible)")
        else:
            logger.warning("App missing asgi_app attribute")
            
        # Log app type and key attributes
        logger.info(f"App type: {type(app)}")
        logger.info(f"App attributes: {[attr for attr in dir(app) if not attr.startswith('_')]}")
        
    except Exception as e:
        logger.error(f"Error checking app compatibility: {str(e)}")

if __name__ == "__main__":
    logger.info("Starting deployment diagnostics...")
    check_file_structure()
    check_module_imports()
    check_wsgi_compatibility()
    logger.info("\nDiagnostics complete") 
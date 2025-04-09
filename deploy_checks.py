#!/usr/bin/env python3
"""
Pre-deployment validation script for the Neutral News application.
Run this before deploying to Render.com to ensure all dependencies and
configurations are correct.
"""

import os
import sys
import sqlite3
import logging
import requests
import asyncio
from datetime import datetime
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger("deploy_checks")

# Import required modules - with error handling for missing dependencies
try:
    from dotenv import load_dotenv
    load_dotenv()  # Load environment variables from .env file
except ImportError:
    logger.warning("python-dotenv not installed. Environment variables must be set in the system.")

try:
    # Import application modules
    from config_prod import (
        NEWSAPI_ORG_KEY, GUARDIAN_API_KEY, GNEWS_API_KEY, NYT_API_KEY,
        MEDIASTACK_API_KEY, NEWSDATA_API_KEY, AYLIEN_APP_ID, AYLIEN_API_KEY,
        USE_NEWSAPI_ORG, USE_GUARDIAN, USE_GNEWS, USE_NYT,
        USE_MEDIASTACK, USE_NEWSDATA, USE_AYLIEN,
        NEWSAPI_AI_KEY
    )
    from fetchers import REQUEST_TIMEOUT, MAX_RETRIES, fetch_with_error_handling
    # Import the Flask app to create an application context
    from app import app
except ImportError as e:
    logger.error(f"Failed to import required modules: {e}")
    logger.error("Make sure you're running this script from the project root directory")
    sys.exit(1)

def check_environment_variables():
    """Check that all necessary environment variables are set"""
    logger.info("Checking environment variables...")
    
    # Get DB_PATH from app config, environment, or use the default
    db_path = app.config.get("DB_PATH") or os.environ.get("DB_PATH")
    
    required_vars = {
        "DB_PATH": db_path
    }
    
    # API keys that should be present based on configuration
    api_keys = {
        "NEWSAPI_ORG_KEY": (NEWSAPI_ORG_KEY, USE_NEWSAPI_ORG),
        "GUARDIAN_API_KEY": (GUARDIAN_API_KEY, USE_GUARDIAN),
        "GNEWS_API_KEY": (GNEWS_API_KEY, USE_GNEWS),
        "NYT_API_KEY": (NYT_API_KEY, USE_NYT),
        "MEDIASTACK_API_KEY": (MEDIASTACK_API_KEY, USE_MEDIASTACK),
        "NEWSDATA_API_KEY": (NEWSDATA_API_KEY, USE_NEWSDATA),
        "AYLIEN_APP_ID": (AYLIEN_APP_ID, USE_AYLIEN),
        "AYLIEN_API_KEY": (AYLIEN_API_KEY, USE_AYLIEN),
    }
    
    # Check essential variables
    missing_vars = []
    for var_name, value in required_vars.items():
        if not value:
            missing_vars.append(var_name)
            logger.error(f"❌ Required environment variable {var_name} is not set")
        else:
            logger.info(f"✅ {var_name} is set")
    
    # Check API keys
    for key_name, (key_value, enabled) in api_keys.items():
        if enabled and not key_value:
            missing_vars.append(key_name)
            logger.error(f"❌ API key {key_name} is enabled but not set")
        elif enabled:
            # Mask API key for logging
            masked_key = key_value[:2] + "*" * (len(key_value) - 4) + key_value[-2:] if len(key_value) > 4 else "****"
            logger.info(f"✅ {key_name} is set ({masked_key})")
        else:
            logger.info(f"ℹ️ {key_name} is not enabled in config")
    
    # Return False if any required variables are missing
    return len(missing_vars) == 0

def check_database_connection():
    """Check that the database exists and can be connected to"""
    logger.info("Checking database connection...")
    
    # Get DB_PATH directly from app config or environment, don't use get_db_path from routes
    db_path = app.config.get("DB_PATH") or os.environ.get("DB_PATH")
    if not db_path:
        # Use fallback path as last resort
        db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "search_db.sqlite")
        logger.warning(f"Using fallback DB_PATH: {db_path}")
    
    if not db_path:
        logger.error("❌ Could not determine database path")
        return False
    
    logger.info(f"Using database path: {db_path}")
    
    # Check if the database file exists
    if not os.path.exists(db_path):
        logger.error(f"❌ Database file not found at {db_path}")
        return False
    
    # Try to connect to the database
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if required tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        expected_tables = ['search_history', 'hot_topics']
        missing_tables = [table for table in expected_tables if table not in tables]
        
        if missing_tables:
            logger.error(f"❌ Required tables missing: {', '.join(missing_tables)}")
            return False
        
        logger.info(f"✅ Successfully connected to database with tables: {', '.join(tables)}")
        
        # Check for any data
        cursor.execute("SELECT COUNT(*) FROM search_history")
        search_count = cursor.fetchone()[0]
        logger.info(f"ℹ️ Database contains {search_count} saved searches")
        
        conn.close()
        return True
    except sqlite3.Error as e:
        logger.error(f"❌ Database connection error: {e}")
        return False

def check_api_connectivity():
    """Test connectivity to enabled news APIs"""
    logger.info("Checking API connectivity...")
    
    api_tests = []
    
    # Test NewsAPI.org
    if USE_NEWSAPI_ORG:
        api_tests.append(("NewsAPI.org", 
                        "https://newsapi.org/v2/everything", 
                        {"q": "test", "pageSize": 1, "apiKey": NEWSAPI_ORG_KEY}))
    
    # Test Guardian
    if USE_GUARDIAN:
        api_tests.append(("The Guardian", 
                        "https://content.guardianapis.com/search", 
                        {"q": "test", "page-size": 1, "api-key": GUARDIAN_API_KEY}))
    
    # Test GNews
    if USE_GNEWS:
        api_tests.append(("GNews", 
                        "https://gnews.io/api/v4/search", 
                        {"q": "test", "max": 1, "apikey": GNEWS_API_KEY}))
    
    # Test NYT
    if USE_NYT:
        api_tests.append(("New York Times", 
                        "https://api.nytimes.com/svc/search/v2/articlesearch.json", 
                        {"q": "test", "api-key": NYT_API_KEY}))
    
    successful_apis = 0
    failed_apis = 0
    
    for name, url, params in api_tests:
        logger.info(f"Testing connection to {name}...")
        data, error = fetch_with_error_handling(url, params=params)
        
        if error:
            logger.error(f"❌ Failed to connect to {name}: {error}")
            failed_apis += 1
        else:
            logger.info(f"✅ Successfully connected to {name}")
            successful_apis += 1
    
    logger.info(f"API connectivity tests completed: {successful_apis} successful, {failed_apis} failed")
    
    # Consider the check successful if at least 50% of APIs are working
    return successful_apis > 0 and successful_apis >= (len(api_tests) // 2)

def check_port_availability(port=5005):
    """Check if the default port is available"""
    logger.info(f"Checking if port {port} is available...")
    
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(("127.0.0.1", port))
        logger.info(f"✅ Port {port} is available")
        result = True
    except socket.error:
        logger.warning(f"❌ Port {port} is already in use")
        result = False
    finally:
        s.close()
    
    return result

def check_disk_space():
    """Check that there is enough disk space available"""
    logger.info("Checking disk space...")
    
    try:
        import psutil
        disk = psutil.disk_usage('/')
        free_space_mb = disk.free / (1024 * 1024)  # Convert to MB
    except ImportError:
        logger.warning("❌ psutil not installed, can't check disk space")
        return False
    
    required_space = 500
    
    if free_space_mb < required_space:
        logger.error(f"❌ Not enough disk space. Only {free_space_mb:.2f} MB available, need {required_space} MB")
        return False
    else:
        logger.info(f"✅ Sufficient disk space available: {free_space_mb:.2f} MB")
        return True

def run_all_checks():
    """Run all deployment checks and summarize results"""
    logger.info("=" * 50)
    logger.info("STARTING PRE-DEPLOYMENT CHECKS")
    logger.info("=" * 50)
    
    start_time = time.time()
    
    results = {
        "Environment Variables": check_environment_variables(),
        "Database Connection": check_database_connection(),
        "API Connectivity": check_api_connectivity(),
        "Port Availability": check_port_availability(),
    }
    
    # Optional checks that might fail on certain systems
    try:
        results["Disk Space"] = check_disk_space()
    except:
        logger.warning("⚠️ Disk space check skipped (psutil might not be installed)")
    
    # Calculate overall result - pass if all required checks pass
    required_checks = ["Environment Variables", "Database Connection", "API Connectivity"]
    overall_result = all(results[check] for check in required_checks)
    
    # Print summary
    logger.info("=" * 50)
    logger.info("DEPLOYMENT CHECK SUMMARY")
    logger.info("=" * 50)
    
    for check_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        logger.info(f"{status}: {check_name}")
    
    logger.info("=" * 50)
    if overall_result:
        logger.info("✅ ALL REQUIRED CHECKS PASSED - READY FOR DEPLOYMENT")
    else:
        logger.info("❌ SOME CHECKS FAILED - FIX ISSUES BEFORE DEPLOYMENT")
    
    duration = time.time() - start_time
    logger.info(f"Checks completed in {duration:.2f} seconds")
    logger.info("=" * 50)
    
    return overall_result

if __name__ == "__main__":
    success = run_all_checks()
    sys.exit(0 if success else 1) 
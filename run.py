"""
Run script for the Neutral News API using Hypercorn
"""

import os
import asyncio
from hypercorn.config import Config as HypercornConfig
from hypercorn.asyncio import serve

# Import after setting Python path
import sys
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app import app
from app.config import DevelopmentConfig

# Use development config when running locally
app.config.from_object(DevelopmentConfig)

async def main():
    """Main entry point for the application"""
    config = HypercornConfig()
    config.bind = [f"0.0.0.0:{os.environ.get('PORT', '8000')}"]
    config.worker_class = "asyncio"
    config.use_reloader = True
    config.accesslog = "-"  # Log to stdout
    
    await serve(app, config)

if __name__ == "__main__":
    asyncio.run(main()) 
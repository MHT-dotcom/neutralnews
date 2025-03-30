"""
Budget control module for limiting API usage costs.
Implements a simple file-based monthly budget cap for the Stability AI API.
"""

import os
import json
from datetime import datetime
import logging

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
if not logger.handlers:
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    logger.addHandler(ch)

# Stability API costs roughly $0.15 per image generation on average
MONTHLY_BUDGET_USD = 20.0
COST_PER_IMAGE_USD = 0.15
MAX_MONTHLY_GENERATIONS = int(MONTHLY_BUDGET_USD / COST_PER_IMAGE_USD)  # ~133

# Store counter in a simple JSON file
COUNTER_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'stability_usage.json')

def get_monthly_usage():
    """Get current month's API usage count and reset if it's a new month."""
    # Ensure data directory exists
    os.makedirs(os.path.dirname(COUNTER_FILE), exist_ok=True)
    
    current_month = datetime.now().strftime('%Y-%m')
    
    # Default data structure
    data = {
        'month': current_month,
        'count': 0,
        'total_cost': 0.0,
        'history': []
    }
    
    # Load existing data if available
    if os.path.exists(COUNTER_FILE):
        try:
            with open(COUNTER_FILE, 'r') as f:
                data = json.load(f)
                
            # Reset counter if it's a new month
            if data['month'] != current_month:
                # Store old month in history before resetting
                if 'history' not in data:
                    data['history'] = []
                    
                data['history'].append({
                    'month': data['month'],
                    'count': data['count'],
                    'total_cost': data['total_cost']
                })
                
                # Keep only last 12 months in history
                if len(data['history']) > 12:
                    data['history'] = data['history'][-12:]
                
                # Reset current month data
                data['month'] = current_month
                data['count'] = 0
                data['total_cost'] = 0.0
                
                # Save the updated data with history
                with open(COUNTER_FILE, 'w') as f:
                    json.dump(data, f, indent=2)
                
                logger.info(f"Reset budget counter for new month: {current_month}")
                
        except Exception as e:
            # If file is corrupted, reset to defaults
            logger.error(f"Error reading usage data: {e}")
    
    return data

def increment_usage(query):
    """Increment the usage counter for the current month and log query."""
    data = get_monthly_usage()
    
    # Increment counters
    data['count'] += 1
    data['total_cost'] += COST_PER_IMAGE_USD
    
    # Add query to list for this month if we track details
    if 'queries' not in data:
        data['queries'] = []
    
    # Add timestamp and query to the list
    data['queries'].append({
        'timestamp': datetime.now().isoformat(),
        'query': query
    })
    
    # Keep only last 100 queries to avoid file growth
    if len(data['queries']) > 100:
        data['queries'] = data['queries'][-100:]
    
    # Save updated data
    try:
        with open(COUNTER_FILE, 'w') as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        logger.error(f"Error saving usage data: {e}")
    
    # Log status after increment
    remaining = MAX_MONTHLY_GENERATIONS - data['count']
    logger.info(f"Budget status after generation: {data['count']}/{MAX_MONTHLY_GENERATIONS} images " 
                f"(${data['total_cost']:.2f}/${MONTHLY_BUDGET_USD:.2f})")
    logger.info(f"Remaining budget: {remaining} images (${remaining * COST_PER_IMAGE_USD:.2f})")
    
    return data

def is_budget_available():
    """Check if we have budget remaining for the current month."""
    data = get_monthly_usage()
    available = data['count'] < MAX_MONTHLY_GENERATIONS
    
    if not available:
        logger.warning(f"⚠️ Monthly budget limit reached: {data['count']}/{MAX_MONTHLY_GENERATIONS} " 
                     f"(${data['total_cost']:.2f}/${MONTHLY_BUDGET_USD:.2f})")
    else:
        remaining = MAX_MONTHLY_GENERATIONS - data['count']
        logger.info(f"Budget available: {remaining} images remaining " 
                   f"(${remaining * COST_PER_IMAGE_USD:.2f} of ${MONTHLY_BUDGET_USD:.2f})")
        
    return available

def get_budget_summary():
    """Get a human-readable summary of the budget status."""
    data = get_monthly_usage()
    remaining = MAX_MONTHLY_GENERATIONS - data['count']
    
    return {
        'month': data['month'],
        'used': data['count'],
        'limit': MAX_MONTHLY_GENERATIONS,
        'total_cost': data['total_cost'],
        'budget': MONTHLY_BUDGET_USD,
        'remaining': remaining,
        'remaining_cost': remaining * COST_PER_IMAGE_USD,
        'percentage_used': (data['count'] / MAX_MONTHLY_GENERATIONS) * 100 if MAX_MONTHLY_GENERATIONS > 0 else 0
    } 
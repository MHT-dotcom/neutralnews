#!/usr/bin/env python
"""
Script to test image generation with budget control.
"""

import os
import json
import budget_control
from get_img import generate_and_save_image
from flask import Flask
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def setup_test_environment():
    """Set up a Flask test environment."""
    app = Flask(__name__)
    app.config["IMAGE_DIRECTORY"] = os.path.join(os.path.dirname(__file__), "data", "images")
    app.config["DB_PATH"] = os.path.join(os.path.dirname(__file__), "data", "search_db.sqlite")
    return app

def print_budget_info():
    """Print current budget information."""
    budget_info = budget_control.get_budget_summary()
    print("\n==== CURRENT BUDGET STATUS ====")
    print(f"Month: {budget_info['month']}")
    print(f"Used: {budget_info['used']}/{budget_info['limit']} images")
    print(f"Total Cost: ${budget_info['total_cost']:.2f}/${budget_info['budget']:.2f}")
    print(f"Remaining: {budget_info['remaining']} images (${budget_info['remaining_cost']:.2f})")
    print(f"Percentage Used: {budget_info['percentage_used']:.1f}%")
    print("==============================\n")
    return budget_info

def set_budget_count(count):
    """Set the budget count to a specific value."""
    data = budget_control.get_monthly_usage()
    original_count = data['count']
    original_cost = data['total_cost']
    
    # Update the data
    data['count'] = count
    data['total_cost'] = count * budget_control.COST_PER_IMAGE_USD
    
    # Save the updated data
    with open(budget_control.COUNTER_FILE, 'w') as f:
        json.dump(data, f, indent=2)
        
    print(f"Updated count from {original_count} to {count}")
    return original_count, original_cost

def test_normal_image_generation():
    """Test normal image generation when budget is available."""
    # Ensure budget is available
    set_budget_count(0)
    print_budget_info()
    
    with app.app_context():
        print("\nTesting normal image generation...")
        summary = "A sunny day in a beautiful park with trees and a lake."
        query = "beautiful-park"
        
        image_path, status = generate_and_save_image(summary, query, include_images=True)
        
        print(f"Image generation result: path={image_path}, success={status}")
        if image_path:
            print(f"Image exists: {os.path.exists(image_path)}")
            
    print_budget_info()
    return image_path, status

def test_budget_limited_image_generation():
    """Test image generation when budget is exhausted."""
    # Set budget to the limit
    set_budget_count(budget_control.MAX_MONTHLY_GENERATIONS)
    print_budget_info()
    
    with app.app_context():
        print("\nTesting image generation with budget exhausted...")
        summary = "A winter landscape with snow-covered mountains and forests."
        query = "winter-landscape"
        
        image_path, status = generate_and_save_image(summary, query, include_images=True)
        
        print(f"Image generation result: path={image_path}, success={status}")
        if image_path:
            print(f"Image exists: {os.path.exists(image_path)}")
            
    print_budget_info()
    return image_path, status

def test_toggle_off_generation():
    """Test image generation with the include_images toggle off."""
    # Reset budget to available
    set_budget_count(0)
    print_budget_info()
    
    with app.app_context():
        print("\nTesting image generation with toggle off...")
        summary = "An urban cityscape with tall skyscrapers at sunset."
        query = "city-sunset"
        
        image_path, status = generate_and_save_image(summary, query, include_images=False)
        
        print(f"Image generation result: path={image_path}, success={status}")
        
    print_budget_info()
    return image_path, status

def reset_budget():
    """Reset the budget to zero."""
    set_budget_count(0)
    print_budget_info()

def main():
    """Main test function."""
    global app
    app = setup_test_environment()
    
    print("Testing image generation with budget control...")
    
    # Test normal generation
    normal_path, normal_status = test_normal_image_generation()
    
    # Test with budget exhausted
    limited_path, limited_status = test_budget_limited_image_generation()
    
    # Test with toggle off
    toggle_path, toggle_status = test_toggle_off_generation()
    
    # Reset budget
    reset_budget()
    
    # Print summary
    print("\n==== TEST SUMMARY ====")
    print(f"Normal generation: {'SUCCESS' if normal_status else 'FAILED'}")
    print(f"Budget exhausted: {'SUCCESS (properly declined)' if not limited_status else 'FAILED (generated despite budget)'}")
    print(f"Toggle off: {'SUCCESS (properly declined)' if not toggle_status else 'FAILED (generated despite toggle)'}")
    print("======================\n")
    
    print("Test completed.")

if __name__ == "__main__":
    main() 
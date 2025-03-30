#!/usr/bin/env python
"""
Script to test the budget control module functionality.
"""

import budget_control
import json

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

def test_is_budget_available():
    """Test the budget availability check."""
    available = budget_control.is_budget_available()
    print(f"Budget available: {available}")
    return available

def test_increment_usage():
    """Test incrementing the usage counter."""
    print("Incrementing usage counter...")
    data = budget_control.increment_usage("Test query")
    print(f"New count: {data['count']}")
    return data

def test_budget_limit():
    """Test setting usage to near the limit."""
    data = budget_control.get_monthly_usage()
    original_count = data['count']
    original_cost = data['total_cost']
    
    print(f"\nOriginal count: {original_count}")
    
    # Calculate how many more images we need to reach the limit
    limit = budget_control.MAX_MONTHLY_GENERATIONS
    to_add = limit - original_count - 1  # Set to 1 below limit
    
    if to_add > 0:
        print(f"Setting count to 1 below limit ({limit-1})...")
        
        # Manually update the data
        data['count'] = limit - 1
        data['total_cost'] = (limit - 1) * budget_control.COST_PER_IMAGE_USD
        
        # Save the updated data
        with open(budget_control.COUNTER_FILE, 'w') as f:
            json.dump(data, f, indent=2)
            
        print(f"Updated count to {data['count']}")
    else:
        print(f"Count already at or above limit: {original_count}/{limit}")
    
    # Verify the update
    new_data = budget_control.get_monthly_usage()
    print(f"Verified count: {new_data['count']}/{limit}")
    
    # Check if budget is available
    available = budget_control.is_budget_available()
    print(f"Budget available: {available} (should be True if count is 1 below limit)")
    
    return new_data

def test_exceeding_limit():
    """Test what happens when we go over the limit."""
    # Get current data
    data = budget_control.get_monthly_usage()
    count_before = data['count']
    
    # Increment usage one more time
    print("\nIncrementing usage to exceed limit...")
    data = budget_control.increment_usage("Test query exceeding limit")
    
    # Check availability now
    available = budget_control.is_budget_available()
    print(f"Count after increment: {data['count']}")
    print(f"Budget available: {available} (should be False if limit exceeded)")
    
    return data

def reset_to_original(original_count=0, original_cost=0.0):
    """Reset the counter to its original value."""
    data = budget_control.get_monthly_usage()
    data['count'] = original_count
    data['total_cost'] = original_cost
    
    with open(budget_control.COUNTER_FILE, 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"\nReset counter to original value: {original_count}")
    return budget_control.get_monthly_usage()

def main():
    """Main test function."""
    print("Testing budget control module...")
    
    # Get initial state
    initial_info = print_budget_info()
    original_count = initial_info['used']
    original_cost = initial_info['total_cost']
    
    # Basic tests
    test_is_budget_available()
    test_increment_usage()
    print_budget_info()
    
    # Test near limit behavior
    test_budget_limit()
    print_budget_info()
    
    # Test exceeding limit
    test_exceeding_limit()
    print_budget_info()
    
    # Reset to original state
    reset_to_original(original_count, original_cost)
    print_budget_info()
    
    print("Test completed.")

if __name__ == "__main__":
    main() 
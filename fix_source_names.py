#!/usr/bin/env python
"""
Script to fix source names in article json.
This will parse and clean any source object that appears as a stringified dictionary.
"""

import json
import re
import os
import logging

logging.basicConfig(level=logging.INFO)

def extract_name_from_source_str(source):
    """Extract name from a stringified source object"""
    if not isinstance(source, str):
        return source
        
    # Skip if not a stringified dictionary
    if not (source.startswith('{') and '}' in source):
        return source
        
    try:
        # Try to parse it as JSON
        source_obj = json.loads(source.replace("'", '"'))
        if isinstance(source_obj, dict) and 'name' in source_obj:
            return source_obj['name']
    except json.JSONDecodeError:
        # If JSON parsing fails, try regex
        try:
            name_match = re.search(r"['\"]name['\"]:[ ]*['\"]([^'\"]+)['\"]", source)
            if name_match:
                return name_match.group(1)
        except Exception:
            pass
    
    return source

def fix_sources_in_data(data):
    """Fix all sources in the JSON data"""
    if not data:
        return data
        
    # Fix sources in the articles array
    if 'articles' in data and isinstance(data['articles'], list):
        for article in data['articles']:
            if 'source' in article:
                article['source'] = extract_name_from_source_str(article['source'])
    
    # Fix sources in the source distribution
    if 'metadata' in data and 'source_distribution' in data['metadata']:
        source_dist = data['metadata']['source_distribution']
        if source_dist and isinstance(source_dist, dict):
            fixed_dist = {}
            for source, count in source_dist.items():
                fixed_source = extract_name_from_source_str(source)
                # Combine counts if multiple sources resolve to the same name
                if fixed_source in fixed_dist:
                    fixed_dist[fixed_source] += count
                else:
                    fixed_dist[fixed_source] = count
            
            # Replace with fixed distribution
            data['metadata']['source_distribution'] = fixed_dist
    
    return data

# Add this to routes.py as a middleware function
def fix_source_names_middleware(response):
    """Fix source names in JSON responses"""
    if not response.is_json:
        return response
        
    try:
        data = response.get_json()
        fixed_data = fix_sources_in_data(data)
        response.set_data(json.dumps(fixed_data))
    except Exception as e:
        logging.error(f"Error in source name fixing middleware: {e}")
    
    return response

if __name__ == "__main__":
    print("Source name fixing utility loaded")
    print("To use, add the following to your app.py file:")
    print("\nfrom fix_source_names import fix_source_names_middleware")
    print("app.after_request(fix_source_names_middleware)") 
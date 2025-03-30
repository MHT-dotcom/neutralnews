#!/usr/bin/env python
import json
from fix_source_names import fix_sources_in_data

# Sample data with object sources as strings
data = {
    "articles": [
        {
            "title": "Test Article 1",
            "source": "{'name': 'ABC News', 'url': 'https://www.abc.net.au'}"
        },
        {
            "title": "Test Article 2",
            "source": "etfdailynews"
        }
    ],
    "metadata": {
        "source_distribution": {
            "{'name': 'ABC News', 'url': 'https://www.abc.net.au'}": 1,
            "etfdailynews": 3,
            "{'name': 'InfoMoney', 'url': 'https://www.infomoney.com.br'}": 1,
            "{'name': 'finanzen.net', 'url': 'https://www.finanzen.net'}": 2
        }
    }
}

# Fix the sources
fixed_data = fix_sources_in_data(data)

# Print the results
print("BEFORE:")
print(json.dumps(data, indent=2))
print("\nAFTER:")
print(json.dumps(fixed_data, indent=2)) 
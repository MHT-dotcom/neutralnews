from processors import analyze_sentiment

# Test cases
test_texts = [
    "This is a fantastic breakthrough in renewable energy technology!",  # Very positive
    "The stock market showed modest gains today.",  # Slightly positive
    "The weather will be partly cloudy tomorrow.",  # Neutral
    "The company reported lower than expected earnings.",  # Slightly negative
    "Devastating earthquake causes widespread damage.",  # Very negative
]

print("Testing sentiment analysis:")
print("-" * 50)
for text in test_texts:
    score = analyze_sentiment(text)
    print(f"\nText: {text}")
    print(f"Sentiment score: {score:.2f}")

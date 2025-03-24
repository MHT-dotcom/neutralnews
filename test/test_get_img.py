import logging
from get_img import (
    generate_with_stability,
    generate_with_getimg,
    generate_with_openai,
    generate_image_workflow
)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_individual_services():
    """Test each image generation service independently"""
    
    # Test prompt
    test_prompt = "A serene mountain landscape at sunset"
    logger.info(f"Testing with prompt: {test_prompt}")
    
    # Test Stability AI
    logger.info("\n=== Testing Stability AI ===")
    stability_result = generate_with_stability(test_prompt)
    if stability_result:
        stability_result.save("test_stability.png")
        logger.info("✓ Stability AI test successful - image saved as test_stability.png")
    else:
        logger.error("✗ Stability AI test failed")

    # Test Getimg AI
    logger.info("\n=== Testing Getimg AI ===")
    getimg_result = generate_with_getimg(test_prompt)
    if getimg_result:
        getimg_result.save("test_getimg.png")
        logger.info("✓ Getimg AI test successful - image saved as test_getimg.png")
    else:
        logger.error("✗ Getimg AI test failed")

    # Test OpenAI
    logger.info("\n=== Testing OpenAI ===")
    openai_result = generate_with_openai(test_prompt)
    if openai_result:
        openai_result.save("test_openai.png")
        logger.info("✓ OpenAI test successful - image saved as test_openai.png")
    else:
        logger.error("✗ OpenAI test failed")

def test_workflow():
    """Test the complete image generation workflow"""
    
    test_prompts = [
        "A futuristic city skyline at night",
        "A peaceful garden with blooming flowers",
        "An abstract representation of climate change"
    ]
    
    logger.info("\n=== Testing Complete Workflow ===")
    for i, prompt in enumerate(test_prompts, 1):
        logger.info(f"\nTesting prompt {i}: {prompt}")
        result = generate_image_workflow(prompt)
        
        if result:
            output_file = f"test_workflow_{i}.png"
            result.save(output_file)
            logger.info(f"✓ Workflow test {i} successful - image saved as {output_file}")
        else:
            logger.error(f"✗ Workflow test {i} failed")

def test_single_image():
    """Test image generation with a single prompt to minimize credit usage"""
    
    # Test with a simple prompt
    test_prompt = "simple blue circle on white background"
    logger.info(f"Testing with minimal prompt: {test_prompt}")
    
    # Try generating the image
    result = generate_image_workflow(test_prompt)
    
    if result:
        output_file = "test_result.png"
        result.save(output_file)
        logger.info(f"✓ Test successful - image saved as {output_file}")
    else:
        logger.error("✗ Test failed")

if __name__ == "__main__":
    logger.info("Starting image generation tests...")
    
    # Test individual services first
    test_individual_services()
    
    # Test the complete workflow
    test_workflow()
    
    # Test single image
    test_single_image()
    
    logger.info("\nAll tests completed!") 
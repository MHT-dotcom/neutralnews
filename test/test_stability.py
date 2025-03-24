import logging
from get_img import generate_image_workflow

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_stability():
    """Test Stability AI image generation with a single prompt"""
    
    test_prompt = "A simple landscape with mountains and a lake"
    logger.info(f"Testing Stability AI with prompt: {test_prompt}")
    
    result = generate_image_workflow(test_prompt)
    
    if result:
        output_file = "stability_test.png"
        result.save(output_file)
        logger.info(f"✓ Test successful - image saved as {output_file}")
    else:
        logger.error("✗ Test failed")

if __name__ == "__main__":
    logger.info("Starting Stability AI test...")
    test_stability()
    logger.info("Test completed!") 
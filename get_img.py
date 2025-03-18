import stability_sdk.interfaces.gooseai.generation.generation_pb2 as generation_pb2
from stability_sdk import client
from PIL import Image
import io
import os
import logging
import requests  # Added this import
from flask import current_app

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
if not logger.handlers:
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    logger.addHandler(ch)

def generate_with_stability(prompt, size=1024):
    """Generate image using Stability AI SDK v0.8.6 and return PIL Image"""
    logger.info("=== Starting Stability AI generation ===")
    logger.info(f"Prompt used for Stability AI: '{prompt}'")
    try:
        logger.info(f"Stability API key: {'Set' if os.getenv('STABILITY_API_KEY') else 'Not set'}")
        stability_api = client.StabilityInference(
            key=os.getenv('STABILITY_API_KEY', ""),
            verbose=True,
        )
        answers = stability_api.generate(
            prompt=prompt,
            width=size,
            height=size,
        )
        logger.info("Generation request sent")
        for resp in answers:
            for artifact in resp.artifacts:
                if artifact.type == generation_pb2.ArtifactType.ARTIFACT_IMAGE:
                    img = Image.open(io.BytesIO(artifact.binary))
                    logger.info("Image generated successfully with Stability AI")
                    return img
        logger.error("No image artifact found in response")
        return None
    except Exception as e:
        logger.error(f"Stability AI generation failed: {str(e)}", exc_info=True)
        return None

def generate_with_openai(prompt, size=1024):
    """Generate image using OpenAI v1.0.0+ and return PIL Image"""
    logger.info("=== Starting OpenAI generation ===")
    logger.info(f"Prompt used for OpenAI: '{prompt}'")
    try:
        from openai import OpenAI
        logger.info(f"OpenAI API key: {'Set' if os.getenv('OPENAI_API_KEY') else 'Not set'}")
        client = OpenAI(api_key=os.getenv('OPENAI_API_KEY', ""))
        response = client.images.generate(
            prompt=prompt,
            n=1,
            size=f"{size}x{size}"
        )
        
        image_url = response.data[0].url
        response = requests.get(image_url)
        logger.info(f"OpenAI image URL: {image_url[:50]}...")
        if response.status_code == 200:
            logger.info("Image generated successfully with OpenAI")
            return Image.open(io.BytesIO(response.content))
        logger.error(f"Failed to download image: HTTP {response.status_code}")
        return None
    except ImportError:
        logger.error("OpenAI library not installed; skipping OpenAI generation")
        return None
    except Exception as e:
        logger.error(f"OpenAI generation failed: {str(e)}", exc_info=True)
        return None

def generate_and_save_image(query, summary):
    """Generate and save an image based on summary, return path and status"""
    logger.info(f"=== Starting image generation for query: '{query}' ===")
    clean_query = "".join(c if c.isalnum() else "-" for c in query.lower())
    image_path = os.path.join(current_app.config["IMAGE_DIR"], f"{clean_query}.png")
    logger.info(f"Image path: {image_path}")
    
    if os.path.exists(image_path):
        logger.info(f"Image already exists at {image_path}")
        return image_path, True
    
    os.makedirs(os.path.dirname(image_path), exist_ok=True)
    logger.info(f"Images directory ensured: {os.path.dirname(image_path)}")

    prompt = f"A digital illustration of: {summary}"
    logger.info(f"Generating image with prompt: {prompt}")
    
    image = generate_with_stability(prompt)
    if image:
        image.save(image_path)
        logger.info(f"Image saved to {image_path} via Stability AI")
        logger.info(f"Generated image filename: '{clean_query}.png'")
        logger.info(f"File exists after save: {os.path.exists(image_path)}")
        return image_path, True
    
    image = generate_with_openai(prompt)
    if image:
        image.save(image_path)
        logger.info(f"Image saved to {image_path} via OpenAI")
        logger.info(f"Generated image filename: '{clean_query}.png'")
        logger.info(f"File exists after save: {os.path.exists(image_path)}")
        return image_path, True
    
    logger.error(f"Failed to generate image for query: {query}")
    return None, False

if __name__ == "__main__":
    from flask import Flask
    app = Flask(__name__)
    app.config["IMAGE_DIR"] = os.path.join(os.path.dirname(__file__), "static", "images")
    with app.app_context():
        test_query = "Test-Query"
        test_summary = "A futuristic cityscape glowing with neon lights under a starry sky."
        image_path, status = generate_and_save_image(test_query, test_summary)
        print(f"Image Path: {image_path}, Status: {status}")
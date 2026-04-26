import random

async def generate_image(prompt: str) -> str:
    # Placeholder for actual image generation logic (Replicate/DALL-E/Midjourney via API)
    # For now, return a placeholder image based on the prompt hash or random
    
    # In a real implementation:
    # response = requests.post(EXTERNAL_API, json={"prompt": prompt}, headers={"Authorization": KEY})
    # return response.json()["output_url"]
    
    # Returning a sample placeholder image
    return f"https://picsum.photos/seed/{hash(prompt) % 1000}/1024/1024"

import pytest
import os
import sys
from PIL import Image, ImageFilter

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from modules import blur

def test_blur_detection(tmp_path):
    # Create clear image
    clear_img_path = os.path.join(tmp_path, "clear.jpg")
    img = Image.new("RGB", (200, 200), color="white")
    # Draw high contrast shapes to ensure some Laplacian variance
    from PIL import ImageDraw
    draw = ImageDraw.Draw(img)
    draw.rectangle([50, 50, 150, 150], fill="black")
    img.save(clear_img_path)
    
    # Create blurry image
    blurry_img_path = os.path.join(tmp_path, "blurry.jpg")
    blurry_img = img.filter(ImageFilter.GaussianBlur(10))
    blurry_img.save(blurry_img_path)
    
    # Run blur score
    clear_score = blur.get_blur_score(clear_img_path)
    blurry_score = blur.get_blur_score(blurry_img_path)
    
    # Assertions
    assert isinstance(clear_score, float)
    assert isinstance(blurry_score, float)
    assert clear_score > blurry_score

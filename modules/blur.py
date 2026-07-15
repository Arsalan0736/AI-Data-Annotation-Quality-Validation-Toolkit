import cv2
import os

def get_blur_score(image_path):
    """
    Calculate the focus measure of an image using the Variance of Laplacian method.
    Lower scores indicate more blur. Standard threshold is 100.0.
    """
    if not os.path.exists(image_path):
        return 0.0
    try:
        image = cv2.imread(image_path)
        if image is None:
            return 0.0
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        score = cv2.Laplacian(gray, cv2.CV_64F).var()
        return float(score)
    except Exception:
        return 0.0

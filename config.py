import os

# Base paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
IMAGES_DIR = os.path.join(DATA_DIR, "images")
TEXT_DIR = os.path.join(DATA_DIR, "text")
LABELS_DIR = os.path.join(DATA_DIR, "labels")
OUTPUTS_DIR = os.path.join(BASE_DIR, "outputs")
REPORTS_DIR = os.path.join(BASE_DIR, "reports")
ASSETS_DIR = os.path.join(BASE_DIR, "assets")

# Ensure all directories exist
for directory in [DATA_DIR, IMAGES_DIR, TEXT_DIR, LABELS_DIR, OUTPUTS_DIR, REPORTS_DIR, ASSETS_DIR]:
    os.makedirs(directory, exist_ok=True)

# Database path
DB_PATH = os.path.join(BASE_DIR, "toolkit.db")

# Default Class Categories
DEFAULT_CLASSES = ["Dog", "Cat", "Car", "Tree", "Person", "Other"]

# Validation Thresholds
BLUR_THRESHOLD = 100.0  # Variance of Laplacian threshold
SIMILARITY_THRESHOLD = 0.85  # Cosine similarity for duplicate hashing
WRONG_LABEL_THRESHOLD = 0.20  # Cosine similarity threshold for CLIP/MobileNet classification

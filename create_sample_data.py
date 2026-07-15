import os
import shutil
import random
from PIL import Image, ImageDraw, ImageFilter
from modules import database
from config import IMAGES_DIR, TEXT_DIR

def generate_sample_images():
    project_dir = os.path.join(IMAGES_DIR, "sample_image_project")
    os.makedirs(project_dir, exist_ok=True)

    # 1. Helper to draw standard images
    def draw_shape(filename, shape_type, color, text):
        img = Image.new("RGB", (300, 300), color="white")
        draw = ImageDraw.Draw(img)
        if shape_type == "circle":
            draw.ellipse([50, 50, 250, 250], fill=color, outline="black")
        elif shape_type == "rectangle":
            draw.rectangle([50, 100, 250, 200], fill=color, outline="black")
        elif shape_type == "triangle":
            draw.polygon([(150, 50), (50, 250), (250, 250)], fill=color, outline="black")
        elif shape_type == "line":
            draw.line([(150, 50), (150, 250)], fill=color, width=10)
            draw.ellipse([125, 25, 175, 75], fill=color)
        else:
            draw.polygon([(100, 50), (200, 50), (250, 150), (200, 250), (100, 250), (50, 150)], fill=color, outline="black")
        
        # Save standard image
        path = os.path.join(project_dir, filename)
        img.save(path)
        return path, img

    # Draw standard images
    draw_shape("dog_shape.jpg", "circle", "brown", "Dog")
    draw_shape("cat_shape.jpg", "circle", "yellow", "Cat")
    _, car_img = draw_shape("car_shape.jpg", "rectangle", "red", "Car")
    draw_shape("tree_shape.jpg", "triangle", "green", "Tree")
    draw_shape("person_shape.jpg", "line", "pink", "Person")
    draw_shape("other_shape.jpg", "polygon", "blue", "Other")

    # 2. Blurry image (Variance of Laplacian will be low)
    blurry_path = os.path.join(project_dir, "blurry_car.jpg")
    blurry_img = car_img.filter(ImageFilter.GaussianBlur(15))
    blurry_img.save(blurry_path)

    # 3. Duplicate image (Exact replica of car_shape.jpg)
    dup_path = os.path.join(project_dir, "car_duplicate.jpg")
    car_img.save(dup_path)

    # 4. Corrupted image (Write raw broken bytes)
    corr_path = os.path.join(project_dir, "corrupted.jpg")
    with open(corr_path, "wb") as f:
        f.write(b"broken jpeg files containing bad headers and corrupt data stream")

    print("Sample images generated successfully.")

def generate_sample_texts():
    project_dir = os.path.join(TEXT_DIR, "sample_text_project")
    os.makedirs(project_dir, exist_ok=True)

    texts = {
        "review1.txt": "The customer is extremely happy. The delivery was fast and the quality was outstanding!",
        "review2.txt": "This product is absolute garbage, do not buy! It broke on the first use.",
        "review3.txt": "It was an average experience. The product works fine but nothing special.",
        "spam1.txt": "WINNER! You have won a free $1000 Walmart gift card. Click the link to claim now!",
        "spam2.txt": "Are you free to meet for lunch today? Let me know.",
        "spam3.txt": "URGENT: Please verify your bank account details within 24 hours to prevent suspension."
    }

    for filename, content in texts.items():
        path = os.path.join(project_dir, filename)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

    print("Sample texts generated successfully.")

def bootstrap_database():
    database.init_db()

    # 1. Create Image Project
    img_project_id = database.create_project("Sample Image Project", "Image")
    if img_project_id:
        img_filenames = [
            "dog_shape.jpg", "cat_shape.jpg", "car_shape.jpg",
            "tree_shape.jpg", "person_shape.jpg", "other_shape.jpg",
            "blurry_car.jpg", "car_duplicate.jpg", "corrupted.jpg"
        ]
        
        item_ids = {}
        for fname in img_filenames:
            rel_path = os.path.join("sample_image_project", fname)
            item_id = database.add_data_item(img_project_id, rel_path, content=None)
            item_ids[fname] = item_id

        # Add mock annotations to illustrate Majority Voting & Agreement Checker
        # For dog_shape.jpg: Annotator A (Dog), Annotator B (Dog), Annotator C (Cat) -> Majority Dog (66%)
        database.add_annotation(item_ids["dog_shape.jpg"], "Annotator A", "Dog", duration_seconds=4.5)
        database.add_annotation(item_ids["dog_shape.jpg"], "Annotator B", "Dog", duration_seconds=3.8)
        database.add_annotation(item_ids["dog_shape.jpg"], "Annotator C", "Cat", duration_seconds=6.1)

        # For cat_shape.jpg: Annotator A (Cat), Annotator B (Cat), Annotator C (Cat) -> Majority Cat (100%)
        database.add_annotation(item_ids["cat_shape.jpg"], "Annotator A", "Cat", duration_seconds=5.0)
        database.add_annotation(item_ids["cat_shape.jpg"], "Annotator B", "Cat", duration_seconds=4.2)
        database.add_annotation(item_ids["cat_shape.jpg"], "Annotator C", "Cat", duration_seconds=4.9)

        # For car_shape.jpg: Only A and B annotated (Car) -> Majority Car (100%)
        database.add_annotation(item_ids["car_shape.jpg"], "Annotator A", "Car", duration_seconds=3.0)
        database.add_annotation(item_ids["car_shape.jpg"], "Annotator B", "Car", duration_seconds=2.8)

        # For tree_shape.jpg: Annotator A (Dog) - Intentionally wrong label to test wrong label validator!
        database.add_annotation(item_ids["tree_shape.jpg"], "Annotator A", "Dog", duration_seconds=3.5)

        # For person_shape.jpg: Missing annotations (None)

    # 2. Create Text Project
    txt_project_id = database.create_project("Sample Text Project", "Text")
    if txt_project_id:
        txt_filenames = [
            "review1.txt", "review2.txt", "review3.txt",
            "spam1.txt", "spam2.txt", "spam3.txt"
        ]
        
        # We need the content to store in DB
        contents = {
            "review1.txt": "The customer is extremely happy. The delivery was fast and the quality was outstanding!",
            "review2.txt": "This product is absolute garbage, do not buy! It broke on the first use.",
            "review3.txt": "It was an average experience. The product works fine but nothing special.",
            "spam1.txt": "WINNER! You have won a free $1000 Walmart gift card. Click the link to claim now!",
            "spam2.txt": "Are you free to meet for lunch today? Let me know.",
            "spam3.txt": "URGENT: Please verify your bank account details within 24 hours to prevent suspension."
        }

        item_ids = {}
        for fname in txt_filenames:
            rel_path = os.path.join("sample_text_project", fname)
            item_id = database.add_data_item(txt_project_id, rel_path, content=contents[fname])
            item_ids[fname] = item_id

        # Text Annotations
        database.add_annotation(item_ids["review1.txt"], "Annotator A", "Positive", duration_seconds=5.2)
        database.add_annotation(item_ids["review2.txt"], "Annotator A", "Negative", duration_seconds=3.1)
        database.add_annotation(item_ids["spam1.txt"], "Annotator A", "Spam", duration_seconds=2.0)
        database.add_annotation(item_ids["spam2.txt"], "Annotator A", "Not Spam", duration_seconds=4.0)

    print("Database bootstrapped with sample entries successfully.")

if __name__ == "__main__":
    generate_sample_images()
    generate_sample_texts()
    bootstrap_database()

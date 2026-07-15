import pytest
import os
import sys
from PIL import Image

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from modules import database, duplicate
from config import IMAGES_DIR

def test_duplicate_detection(tmp_path):
    # Initialize DB
    database.init_db()
    
    # Create project
    proj_id = database.create_project("Unit Test Dup Project", "Image")
    assert proj_id is not None
    
    # Save target images to the workspace data folder under project name
    project_folder = os.path.join(IMAGES_DIR, "unit_test_dup_project")
    os.makedirs(project_folder, exist_ok=True)
    
    # 1. Create primary image
    img1 = Image.new("RGB", (100, 100), color="blue")
    img1_path = os.path.join(project_folder, "img1.png")
    img1.save(img1_path)
    
    # 2. Create duplicate image
    img2 = Image.new("RGB", (100, 100), color="blue")
    img2_path = os.path.join(project_folder, "img2.png")
    img2.save(img2_path)
    
    # Add to database
    id1 = database.add_data_item(proj_id, "unit_test_dup_project/img1.png")
    id2 = database.add_data_item(proj_id, "unit_test_dup_project/img2.png")
    
    # Run duplicate checker
    dups = duplicate.detect_duplicates(proj_id)
    
    # Assertions
    assert len(dups) == 1
    assert dups[0]["similarity"] == 100.0
    
    # Verify DB state
    item2 = database.get_data_item(id2)
    assert item2["is_duplicate"] == 1
    assert item2["duplicate_of"] == "unit_test_dup_project/img1.png"
    
    # Cleanup files and database
    database.delete_project(proj_id)
    if os.path.exists(img1_path):
        os.remove(img1_path)
    if os.path.exists(img2_path):
        os.remove(img2_path)
    if os.path.exists(project_folder):
        os.rmdir(project_folder)

import pytest
import os
import sys

# Add project root to path so we can import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules import database

def test_database_lifecycle():
    # 1. Initialize
    database.init_db()
    
    # 2. Create Project
    proj_name = "Unit Test Image Project"
    proj_id = database.create_project(proj_name, "Image")
    assert proj_id is not None
    
    # Try duplicate name (should fail/return None)
    dup_id = database.create_project(proj_name, "Image")
    assert dup_id is None
    
    # 3. Add item
    item_id = database.add_data_item(proj_id, "test_file.jpg")
    assert item_id is not None
    
    # Get item
    item = database.get_data_item(item_id)
    assert item["filename"] == "test_file.jpg"
    assert item["project_id"] == proj_id
    
    # 4. Add Annotation
    database.add_annotation(item_id, "Test Annotator", "Dog", duration_seconds=5.0)
    annotations = database.get_annotations_for_item(item_id)
    assert len(annotations) == 1
    assert annotations[0]["label"] == "Dog"
    assert annotations[0]["annotator_name"] == "Test Annotator"
    
    # 5. Check Statistics
    stats = database.get_statistics(proj_id)
    assert stats["total_items"] == 1
    assert stats["annotated_count"] == 1
    
    # 6. Cleanup
    database.delete_project(proj_id)
    project = database.get_project(proj_id)
    assert project is None

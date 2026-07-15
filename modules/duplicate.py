import os
from PIL import Image
import imagehash
from modules import database
from config import IMAGES_DIR, SIMILARITY_THRESHOLD

def detect_duplicates(project_id):
    """
    Scans all image items in a project to find duplicate images.
    Updates the database with is_duplicate, duplicate_of, and similarity_score.
    """
    items = database.get_data_items(project_id)
    if not items:
        return []
        
    hashes = {}
    duplicates = []
    
    # 1. Compute hashes for all valid, non-corrupted images
    for item in items:
        if item["is_corrupted"]:
            continue
            
        image_path = os.path.join(IMAGES_DIR, item["filename"])
        if not os.path.exists(image_path):
            continue
            
        try:
            with Image.open(image_path) as img:
                # Use Perceptual Hash (phash) for robustness to resizing/compression
                h = imagehash.phash(img)
                hashes[item["id"]] = (item["filename"], h)
        except Exception:
            # Mark as corrupted if we can't open it here
            database.update_item_validation(item["id"], is_corrupted=1)

    # Reset duplicate flags first
    for item in items:
        database.update_item_validation(
            item["id"], 
            is_duplicate=0, 
            duplicate_of=None, 
            similarity_score=None
        )

    # 2. Compare all pairs
    item_ids = list(hashes.keys())
    flagged_duplicates = set()
    
    for i in range(len(item_ids)):
        id1 = item_ids[i]
        fname1, h1 = hashes[id1]
        
        # If this item was already flagged as a duplicate of something else, skip it as the master
        if id1 in flagged_duplicates:
            continue
            
        for j in range(i + 1, len(item_ids)):
            id2 = item_ids[j]
            fname2, h2 = hashes[id2]
            
            if id2 in flagged_duplicates:
                continue
                
            # Difference of hashes (0 to 64 bits)
            diff = h1 - h2
            similarity = (64.0 - diff) / 64.0
            
            if similarity >= SIMILARITY_THRESHOLD:
                # Mark id2 as a duplicate of fname1
                database.update_item_validation(
                    id2, 
                    is_duplicate=1, 
                    duplicate_of=fname1, 
                    similarity_score=float(similarity)
                )
                flagged_duplicates.add(id2)
                duplicates.append({
                    "original": fname1,
                    "duplicate": fname2,
                    "similarity": similarity * 100.0
                })
                
    # Refresh project stats
    database.update_statistics(project_id)
    return duplicates

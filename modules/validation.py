import streamlit as st
import os
import time
import pandas as pd
from PIL import Image as PILImage
from config import IMAGES_DIR, TEXT_DIR, BLUR_THRESHOLD, WRONG_LABEL_THRESHOLD, DEFAULT_CLASSES
from modules import database, blur, duplicate

# Preloaded model reference in session state to avoid reloading on every rerun
if "torch_model" not in st.session_state:
    st.session_state.torch_model = None
    st.session_state.torch_transforms = None
    st.session_state.torch_categories = None

def load_mobilenet():
    """Lazily load MobileNet model and weights."""
    if st.session_state.torch_model is not None:
        return
        
    st.info("Loading MobileNet validation model... (this may take a few seconds on first run)")
    try:
        import torch
        import torchvision.transforms as T
        from torchvision.models import mobilenet_v3_large, MobileNet_V3_Large_Weights
        
        # Load weights & model
        weights = MobileNet_V3_Large_Weights.DEFAULT
        model = mobilenet_v3_large(weights=weights)
        model.eval()
        
        st.session_state.torch_model = model
        st.session_state.torch_transforms = weights.transforms()
        st.session_state.torch_categories = weights.meta["categories"]
    except Exception as e:
        st.error(f"Could not load PyTorch/Torchvision: {e}")

def run_label_validation_image(project_id):
    """Run MobileNet classifier and flag discrepancies with annotations."""
    load_mobilenet()
    if st.session_state.torch_model is None:
        return
        
    import torch
    
    items = database.get_data_items(project_id)
    annotations = database.get_all_annotations_for_project(project_id)
    
    # Filter only annotated, non-corrupted images
    annotated_items = {}
    for a in annotations:
        # Group by image_id (taking the first/majority label)
        annotated_items[a["image_id"]] = a["label"]
        
    model = st.session_state.torch_model
    transforms = st.session_state.torch_transforms
    categories = st.session_state.torch_categories
    
    for item in items:
        if item["is_corrupted"] or item["id"] not in annotated_items:
            continue
            
        image_path = os.path.join(IMAGES_DIR, item["filename"])
        if not os.path.exists(image_path):
            continue
            
        try:
            img = PILImage.open(image_path).convert("RGB")
            # Apply transforms
            input_tensor = transforms(img).unsqueeze(0)
            
            with torch.no_grad():
                output = model(input_tensor)
                probabilities = torch.nn.functional.softmax(output[0], dim=0)
                
            # Find top prediction
            top_prob, top_cat_idx = torch.topk(probabilities, 1)
            pred_class = categories[top_cat_idx.item()].lower()
            confidence = float(top_prob.item())
            
            # Map predicted ImageNet class to project classes
            mapped_pred = "Other"
            
            # Keyword matching rules
            dog_kw = ['dog', 'puppy', 'terrier', 'retriever', 'spaniel', 'collie', 'malamute', 'husky', 'poodle', 'pekingese', 'pug', 'chow', 'whippet']
            cat_kw = ['cat', 'tabby', 'kitten', 'leopard', 'jaguar', 'cheetah', 'lion', 'tiger', 'cougar']
            car_kw = ['car', 'cab', 'limousine', 'sports car', 'minivan', 'convertible', 'jeep', 'wagon', 'racer']
            tree_kw = ['tree', 'forest', 'wood', 'pine', 'spruce', 'oak', 'maple']
            person_kw = ['person', 'man', 'woman', 'child', 'scuba', 'groom', 'bride']
            
            if any(k in pred_class for k in dog_kw):
                mapped_pred = "Dog"
            elif any(k in pred_class for k in cat_kw):
                mapped_pred = "Cat"
            elif any(k in pred_class for k in car_kw):
                mapped_pred = "Car"
            elif any(k in pred_class for k in tree_kw):
                mapped_pred = "Tree"
            elif any(k in pred_class for k in person_kw):
                mapped_pred = "Person"
                
            # Compare labeled value with predicted
            annotated_label = annotated_items[item["id"]]
            
            # We compute a pseudo-similarity score
            # If mapped prediction matches annotated label, similarity score is high (e.g. 1.0)
            # If not, similarity score is low (e.g. 0.10) or we can look at the mapped class probability
            # Let's say if it matches, similarity_score = 0.95
            # If mismatched, similarity_score = 0.05
            sim_score = 0.95 if mapped_pred.lower() == annotated_label.lower() else 0.05
            
            # Update database record
            database.update_item_validation(item["id"], similarity_score=sim_score)
        except Exception:
            pass

def run_label_validation_text(project_id):
    """Run scikit-learn TF-IDF classifier to spot text labels outliers."""
    items = database.get_data_items(project_id)
    annotations = database.get_all_annotations_for_project(project_id)
    
    # We need at least 5 annotated text items to run validation
    if len(annotations) < 5:
        return
        
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.linear_model import LogisticRegression
        from sklearn.model_selection import StratifiedKFold
        import numpy as np
        
        # Build dataframe
        item_map = {item["id"]: item for item in items}
        
        data = []
        for ann in annotations:
            it = item_map[ann["image_id"]]
            if it["content"]:
                data.append({
                    "id": it["id"],
                    "text": it["content"],
                    "label": ann["label"]
                })
                
        df = pd.DataFrame(data)
        if len(df["label"].unique()) < 2:
            return  # Needs at least 2 distinct classes to train a classifier
            
        vectorizer = TfidfVectorizer(max_features=500)
        X = vectorizer.fit_transform(df["text"]).toarray()
        y = df["label"].values
        
        # Run 3-fold cross validation to get out-of-fold probability estimates
        skf = StratifiedKFold(n_splits=min(3, len(np.unique(y))))
        oof_probs = np.zeros(len(df))
        
        for train_idx, val_idx in skf.split(X, y):
            X_tr, y_tr = X[train_idx], y[train_idx]
            X_va, y_va = X[val_idx], y[val_idx]
            
            # Make sure we don't crash if subsplit has missing classes
            if len(np.unique(y_tr)) < 2:
                continue
                
            clf = LogisticRegression()
            clf.fit(X_tr, y_tr)
            
            # Predict probability distribution
            probs = clf.predict_proba(X_va)
            classes = clf.classes_.tolist()
            
            # Find the probability of the actual assigned label
            for idx_local, global_idx in enumerate(val_idx):
                target_lbl = y_va[idx_local]
                if target_lbl in classes:
                    class_idx = classes.index(target_lbl)
                    oof_probs[global_idx] = probs[idx_local, class_idx]
                else:
                    oof_probs[global_idx] = 0.0
                    
        # Update SQLite with similarity_score = oof probability
        for index, row in df.iterrows():
            prob = oof_probs[index]
            # If prob is 0 (did not get predicted), let's keep it 0.05
            score = max(0.01, float(prob))
            database.update_item_validation(row["id"], similarity_score=score)
            
    except Exception:
        pass

def render(project):
    st.header(f"🔍 Quality Validation Suite - {project['name']}")
    
    st.write("Run the automated validation tools to scan your dataset for issues.")

    # Action Toolbar
    col_act1, col_act2 = st.columns([1, 4])
    with col_act1:
        if st.button("🚀 Run Full Validation Suite", type="primary", use_container_width=True):
            with st.spinner("Analyzing dataset files..."):
                items = database.get_data_items(project["id"])
                
                # 1. Corrupted detection
                for item in items:
                    if project["type"] == "Image":
                        image_path = os.path.join(IMAGES_DIR, item["filename"])
                        is_corr = 0
                        if not os.path.exists(image_path):
                            is_corr = 1
                        else:
                            try:
                                with PILImage.open(image_path) as img:
                                    img.verify()
                            except Exception:
                                is_corr = 1
                        database.update_item_validation(item["id"], is_corrupted=is_corr)
                    else:
                        # For text, check if empty or fails to read
                        text_path = os.path.join(TEXT_DIR, item["filename"])
                        is_corr = 0
                        if not os.path.exists(text_path):
                            is_corr = 1
                        else:
                            try:
                                with open(text_path, "r", encoding="utf-8") as f:
                                    content = f.read()
                                if not content.strip():
                                    is_corr = 1
                            except Exception:
                                is_corr = 1
                        database.update_item_validation(item["id"], is_corrupted=is_corr)
                
                # 2. Blur detection (Only for Images)
                if project["type"] == "Image":
                    for item in items:
                        if not item["is_corrupted"]:
                            image_path = os.path.join(IMAGES_DIR, item["filename"])
                            score = blur.get_blur_score(image_path)
                            database.update_item_validation(item["id"], blur_score=score)
                            
                # 3. Duplicate detection (Only for Images)
                if project["type"] == "Image":
                    duplicate.detect_duplicates(project["id"])
                    
                # 4. Wrong label detection
                if project["type"] == "Image":
                    run_label_validation_image(project["id"])
                else:
                    run_label_validation_text(project["id"])
                    
                # Finally, refresh statistics
                database.update_statistics(project["id"])
                st.success("Validation suite complete!")
                st.rerun()

    # Load fresh items to display
    items = database.get_data_items(project["id"])
    
    # Tab View for different issues
    tabs = st.tabs([
        "❌ Corrupted Files", 
        "🌫️ Blurry Images", 
        "👯 Duplicates", 
        "❓ Missing Labels", 
        "🏷️ Possible Wrong Labels"
    ])

    # 1. Corrupted Files Tab
    with tabs[0]:
        corrupted = [it for it in items if it["is_corrupted"] == 1]
        st.subheader(f"Corrupted Files Detected ({len(corrupted)})")
        if corrupted:
            df_corr = pd.DataFrame([{
                "ID": c["id"],
                "Filename": c["filename"],
                "Type": project["type"]
            } for c in corrupted])
            st.dataframe(df_corr, use_container_width=True)
        else:
            st.success("No corrupted files found.")

    # 2. Blurry Images Tab
    with tabs[1]:
        if project["type"] == "Text":
            st.info("Blur detection is not applicable to text datasets.")
        else:
            blur_thresh = st.slider("Blur Threshold (Variance of Laplacian)", min_value=10.0, max_value=250.0, value=BLUR_THRESHOLD, step=5.0)
            blurry = [it for it in items if it["blur_score"] is not None and it["blur_score"] < blur_thresh]
            
            st.subheader(f"Blurry Images Detected ({len(blurry)})")
            if blurry:
                cols = st.columns(3)
                for index, b in enumerate(blurry):
                    with cols[index % 3]:
                        image_path = os.path.join(IMAGES_DIR, b["filename"])
                        if os.path.exists(image_path):
                            st.image(image_path, caption=f"{os.path.basename(b['filename'])} | Score: {b['blur_score']:.1f}", use_container_width=True)
            else:
                st.success("No blurry images found below threshold.")

    # 3. Duplicates Tab
    with tabs[2]:
        if project["type"] == "Text":
            st.info("Duplicate image detection is not applicable to text datasets.")
        else:
            duplicates = [it for it in items if it["is_duplicate"] == 1]
            st.subheader(f"Duplicate Images Detected ({len(duplicates)})")
            if duplicates:
                for d in duplicates:
                    col_orig, col_dup = st.columns(2)
                    with col_orig:
                        orig_path = os.path.join(IMAGES_DIR, d["duplicate_of"])
                        if os.path.exists(orig_path):
                            st.image(orig_path, caption=f"Original: {os.path.basename(d['duplicate_of'])}", use_container_width=True)
                    with col_dup:
                        dup_path = os.path.join(IMAGES_DIR, d["filename"])
                        if os.path.exists(dup_path):
                            st.image(dup_path, caption=f"Duplicate: {os.path.basename(d['filename'])} | Similarity: {d['similarity_score']*100:.1f}%", use_container_width=True)
                    st.markdown("---")
            else:
                st.success("No duplicate images found.")

    # 4. Missing Labels Tab
    with tabs[3]:
        # Items with no annotations
        annotations = database.get_all_annotations_for_project(project["id"])
        annotated_ids = set(a["image_id"] for a in annotations)
        missing = [it for it in items if it["id"] not in annotated_ids]
        
        st.subheader(f"Missing Annotations ({len(missing)})")
        if missing:
            df_missing = pd.DataFrame([{
                "ID": m["id"],
                "Filename": m["filename"],
                "Sample Content": m["content"][:60] + "..." if m["content"] else "N/A"
            } for m in missing])
            st.dataframe(df_missing, use_container_width=True)
        else:
            st.success("All items have at least one annotation.")

    # 5. Wrong Labels Tab
    with tabs[4]:
        # Items where similarity_score is less than WRONG_LABEL_THRESHOLD and has an annotation
        annotations = database.get_all_annotations_for_project(project["id"])
        annotated_ids = set(a["image_id"] for a in annotations)
        
        wrong_candidates = [
            it for it in items 
            if it["id"] in annotated_ids 
               and it["similarity_score"] is not None 
               and it["similarity_score"] < WRONG_LABEL_THRESHOLD
        ]
        
        st.subheader(f"Potentially Wrong Labels ({len(wrong_candidates)})")
        st.write("These items have annotations that mismatch the predicted classification patterns.")
        
        if wrong_candidates:
            # Query reviews for reference
            reviews = database.get_reviews_for_project(project["id"])
            reviewed_ids = {r["image_id"]: r for r in reviews}
            
            for wc in wrong_candidates:
                # Find annotation
                ann_list = [a for a in annotations if a["image_id"] == wc["id"]]
                ann_label = ann_list[0]["label"] if ann_list else "Unknown"
                
                # Check review status
                rev_row = reviewed_ids.get(wc["id"])
                
                st.markdown(f"**Item ID:** {wc['id']} | **Filename:** `{os.path.basename(wc['filename'])}`")
                col_item_view, col_review_ctrl = st.columns([3, 2])
                
                with col_item_view:
                    if project["type"] == "Image":
                        image_path = os.path.join(IMAGES_DIR, wc["filename"])
                        if os.path.exists(image_path):
                            st.image(image_path, width=200)
                    else:
                        st.markdown(f"*{wc['content']}*")
                        
                    st.write(f"🏷️ **Annotated Label:** `{ann_label}`")
                    st.write(f"🤖 **Model Match Confidence:** `{wc['similarity_score']*100:.1f}%`")
                    
                    if rev_row:
                        st.info(f"Reviewed status: **{rev_row['status']}** {f'({rev_row['corrected_label']})' if rev_row['corrected_label'] else ''}")
                
                with col_review_ctrl:
                    st.write("Review Action:")
                    rev_status = st.selectbox("Status", ["Approve", "Correct Label"], key=f"rev_sel_{wc['id']}")
                    
                    corrected_label = None
                    if rev_status == "Correct Label":
                        corrected_label = st.text_input("Correct Label Value", value=ann_label, key=f"rev_txt_{wc['id']}")
                        
                    if st.button("Submit Decision", key=f"rev_btn_{wc['id']}"):
                        database.add_review(wc["id"], "Reviewer A", rev_status, corrected_label)
                        st.success("Decision saved!")
                        st.rerun()
                st.markdown("---")
        else:
            st.success("No labels flagged as potentially wrong.")

import streamlit as st
import os
import time
from config import IMAGES_DIR, TEXT_DIR, DEFAULT_CLASSES
from modules import database

def render(project):
    st.header(f"✏️ Annotation View - {project['name']}")

    # Setup Session State keys
    if "current_index" not in st.session_state:
        st.session_state.current_index = 0
    if "start_time" not in st.session_state:
        st.session_state.start_time = time.time()
    if "undo_stack" not in st.session_state:
        st.session_state.undo_stack = []
    if "last_project_id" not in st.session_state or st.session_state.last_project_id != project["id"]:
        st.session_state.last_project_id = project["id"]
        st.session_state.current_index = 0
        st.session_state.undo_stack = []

    # Get data items for active project
    items = database.get_data_items(project["id"])
    if not items:
        st.info("No items in this project. Please go to the Upload page to add data.")
        return

    total_items = len(items)

    # Sidebar parameters for annotation page
    st.sidebar.subheader("Annotation Settings")
    annotator_name = st.sidebar.text_input("Annotator Name", value="Annotator A")
    
    # Class labels selection
    if project["type"] == "Image":
        default_classes_str = ", ".join(DEFAULT_CLASSES)
    else:
        # Check text project name to guess default classes
        if "spam" in project["name"].lower():
            default_classes_str = "Spam, Not Spam"
        else:
            default_classes_str = "Positive, Neutral, Negative"
            
    classes_input = st.sidebar.text_input("Classes (comma-separated)", default_classes_str)
    classes = [c.strip() for c in classes_input.split(",") if c.strip()]
    
    if not classes:
        st.error("Please enter at least one label class.")
        return

    # Bound current index
    if st.session_state.current_index >= total_items:
        st.session_state.current_index = total_items - 1
    if st.session_state.current_index < 0:
        st.session_state.current_index = 0

    # Get active item
    item = items[st.session_state.current_index]

    # Calculate statistics for progress
    annotations_project = database.get_all_annotations_for_project(project["id"])
    
    # Count how many distinct items have annotations by this annotator
    annotated_by_user = set(a["image_id"] for a in annotations_project if a["annotator_name"] == annotator_name)
    annotated_count = len(annotated_by_user)
    
    progress_percentage = int((annotated_count / total_items) * 100) if total_items > 0 else 0
    
    # Progress bar text matching: █ █ █ █ █ 58%
    num_blocks = int(progress_percentage / 10)
    blocks_str = "█ " * num_blocks + "░ " * (10 - num_blocks)
    
    # Display Progress Card
    st.markdown(f"### Progress: `{blocks_str}` **{progress_percentage}%** ({annotated_count}/{total_items} items annotated)")
    
    st.markdown("---")

    # Display panel (Image or Text)
    col_view, col_controls = st.columns([3, 2])
    
    with col_view:
        # Check if item is corrupted
        if item["is_corrupted"]:
            st.error("⚠️ Corrupted image! This file is broken and cannot be read.")
        elif project["type"] == "Image":
            image_path = os.path.join(IMAGES_DIR, item["filename"])
            if os.path.exists(image_path):
                try:
                    st.image(image_path, use_container_width=True)
                except Exception as e:
                    st.error(f"Error displaying image: {e}")
            else:
                st.error(f"Image file not found at path: {image_path}")
        else:
            # Text item
            st.markdown(f"""
            <div style="background-color: #ffffff; padding: 25px; border-radius: 8px; border-left: 5px solid #4A90E2; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
                <p style="font-size: 1.15rem; line-height: 1.6; color: #2C3E50; font-family: monospace;">"{item['content']}"</p>
            </div>
            """, unsafe_allow_html=True)
            
        st.caption(f"Filename: `{os.path.basename(item['filename'])}` (Item ID: {item['id']})")

    with col_controls:
        st.subheader("Select Label")
        
        # Check existing annotation by this annotator for this item
        existing_ann = [a for a in annotations_project if a["image_id"] == item["id"] and a["annotator_name"] == annotator_name]
        current_label = existing_ann[0]["label"] if existing_ann else None
        
        # If there's an existing label, show indicator
        if current_label:
            st.info(f"Currently labeled as: **{current_label}**")

        # Renders label choice using radio buttons or buttons
        selected_label = st.radio("Label options:", classes, index=classes.index(current_label) if current_label in classes else 0)

        st.markdown("###")

        # Action Buttons Layout
        btn_col1, btn_col2, btn_col3 = st.columns(3)
        with btn_col1:
            prev_btn = st.button("⬅️ Previous", use_container_width=True)
        with btn_col2:
            skip_btn = st.button("⏭️ Skip", use_container_width=True)
        with btn_col3:
            next_btn = st.button("Next ➡️", use_container_width=True)
            
        btn_col4, btn_col5 = st.columns(2)
        with btn_col4:
            save_btn = st.button("💾 Save Label", type="primary", use_container_width=True)
        with btn_col5:
            undo_btn = st.button("↩️ Undo Last", use_container_width=True)

        # Trigger logic
        
        # 1. Save Label Action
        if save_btn:
            elapsed_time = time.time() - st.session_state.start_time
            database.add_annotation(
                image_id=item["id"],
                annotator_name=annotator_name,
                label=selected_label,
                duration_seconds=elapsed_time
            )
            # Push to undo stack
            st.session_state.undo_stack.append(item["id"])
            
            # Update stats
            database.update_statistics(project["id"])
            
            # Proceed to next item automatically
            if st.session_state.current_index < total_items - 1:
                st.session_state.current_index += 1
            st.session_state.start_time = time.time()
            st.rerun()

        # 2. Skip Action
        if skip_btn:
            if st.session_state.current_index < total_items - 1:
                st.session_state.current_index += 1
            st.session_state.start_time = time.time()
            st.rerun()

        # 3. Next Action
        if next_btn:
            if st.session_state.current_index < total_items - 1:
                st.session_state.current_index += 1
            st.session_state.start_time = time.time()
            st.rerun()

        # 4. Previous Action
        if prev_btn:
            if st.session_state.current_index > 0:
                st.session_state.current_index -= 1
            st.session_state.start_time = time.time()
            st.rerun()

        # 5. Undo Action
        if undo_btn:
            if st.session_state.undo_stack:
                last_item_id = st.session_state.undo_stack.pop()
                # Find index of this item
                for idx, it in enumerate(items):
                    if it["id"] == last_item_id:
                        st.session_state.current_index = idx
                        break
                # Optional: delete the annotation so they can redefine it
                # We can connect to DB and delete the annotation by user
                conn = database.get_connection()
                cursor = conn.cursor()
                cursor.execute("DELETE FROM Annotations WHERE image_id = ? AND annotator_name = ?", (last_item_id, annotator_name))
                conn.commit()
                conn.close()
                
                database.update_statistics(project["id"])
                st.session_state.start_time = time.time()
                st.rerun()
            else:
                st.warning("No recent annotations in the undo stack for this session.")

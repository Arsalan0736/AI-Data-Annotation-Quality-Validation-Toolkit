import streamlit as st
import os
import zipfile
import time
import pandas as pd
from PIL import Image as PILImage
from config import IMAGES_DIR, TEXT_DIR
from modules import database

def render(project):
    st.header("📥 Upload Dataset")
    
    if project is None:
        st.warning("⚠️ Please select or create a project in the sidebar before uploading.")
        
        st.markdown("### 🤖 Demo Sandbox Bootstrapper")
        st.write("""
        If you are testing this app on Streamlit Cloud or want to explore the toolkit's features immediately, 
        you can seed a sample dataset containing pre-configured image and text classification projects.
        """)
        
        if st.button("🚀 Initialize with Demo Sandbox Dataset", use_container_width=True):
            with st.spinner("Bootstrapping database and generating sample assets..."):
                try:
                    import create_sample_data
                    create_sample_data.generate_sample_images()
                    create_sample_data.generate_sample_texts()
                    create_sample_data.bootstrap_database()
                    
                    st.success("Demo dataset bootstrapped successfully! Refreshing page...")
                    time.sleep(1)
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to bootstrap demo: {e}")
        return

    st.write(f"Add data items to project: **{project['name']}** (Type: **{project['type']}**)")

    if project["type"] == "Image":
        st.subheader("Upload Images (ZIP or individual JPG/PNG files)")
        uploaded_files = st.file_uploader(
            "Choose files", 
            type=["zip", "jpg", "jpeg", "png"], 
            accept_multiple_files=True,
            key="image_uploader"
        )
        
        if uploaded_files:
            if st.button("Process and Save Uploaded Images", use_container_width=True):
                success_count = 0
                error_count = 0
                
                project_folder = os.path.join(IMAGES_DIR, project["name"].replace(" ", "_").lower())
                os.makedirs(project_folder, exist_ok=True)
                
                for uploaded_file in uploaded_files:
                    # Case 1: ZIP File
                    if uploaded_file.name.endswith(".zip"):
                        with zipfile.ZipFile(uploaded_file, 'r') as zip_ref:
                            # Extract all files to project folder
                            for member in zip_ref.infolist():
                                # Avoid directory traversal attacks
                                filename = os.path.basename(member.filename)
                                if not filename:
                                    continue
                                if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                                    source = zip_ref.open(member)
                                    target_path = os.path.join(project_folder, filename)
                                    with open(target_path, "wb") as target:
                                        target.write(source.read())
                                    
                                    # Add to DB
                                    rel_path = os.path.join(project["name"].replace(" ", "_").lower(), filename)
                                    database.add_data_item(project["id"], rel_path, content=None)
                                    success_count += 1
                    # Case 2: Individual Image Files
                    else:
                        filename = uploaded_file.name
                        target_path = os.path.join(project_folder, filename)
                        with open(target_path, "wb") as f:
                            f.write(uploaded_file.getbuffer())
                        
                        # Add to DB
                        rel_path = os.path.join(project["name"].replace(" ", "_").lower(), filename)
                        database.add_data_item(project["id"], rel_path, content=None)
                        success_count += 1
                
                database.update_statistics(project["id"])
                st.success(f"Successfully loaded {success_count} images. Errors: {error_count}")
                st.rerun()

    elif project["type"] == "Text":
        st.subheader("Upload Text Dataset (CSV or individual TXT files)")
        uploaded_files = st.file_uploader(
            "Choose files", 
            type=["csv", "txt"], 
            accept_multiple_files=True,
            key="text_uploader"
        )
        
        if uploaded_files:
            # Check if any CSV is uploaded to show CSV column mapper
            csv_files = [f for f in uploaded_files if f.name.endswith(".csv")]
            txt_files = [f for f in uploaded_files if f.name.endswith(".txt")]
            
            project_folder = os.path.join(TEXT_DIR, project["name"].replace(" ", "_").lower())
            os.makedirs(project_folder, exist_ok=True)
            
            if csv_files:
                st.markdown("### CSV Import settings")
                # Read the first CSV to inspect columns
                df = pd.read_csv(csv_files[0])
                columns = df.columns.tolist()
                
                text_col = st.selectbox("Select Text/Content Column", columns)
                label_col = st.selectbox("Select Label Column (Optional, select 'None' if raw text)", ["None"] + columns)
                
                if st.button("Process CSV & TXT files", use_container_width=True):
                    success_count = 0
                    
                    # 1. Process CSVs
                    for csv_file in csv_files:
                        csv_df = pd.read_csv(csv_file)
                        for index, row in csv_df.iterrows():
                            text_content = str(row[text_col])
                            
                            # Create a unique filename for database representation
                            fname = f"row_{index}_{csv_file.name.replace('.csv', '')}.txt"
                            target_path = os.path.join(project_folder, fname)
                            
                            with open(target_path, "w", encoding="utf-8") as f:
                                f.write(text_content)
                                
                            rel_path = os.path.join(project["name"].replace(" ", "_").lower(), fname)
                            item_id = database.add_data_item(project["id"], rel_path, content=text_content)
                            
                            # If label exists and is not 'None', add as Initial Upload annotation
                            if label_col != "None" and pd.notna(row[label_col]):
                                label_val = str(row[label_col])
                                database.add_annotation(item_id, "Initial Upload", label_val, duration_seconds=0.0)
                                
                            success_count += 1
                    
                    # 2. Process individual TXTs
                    for txt_file in txt_files:
                        content = txt_file.read().decode("utf-8")
                        filename = txt_file.name
                        target_path = os.path.join(project_folder, filename)
                        
                        with open(target_path, "w", encoding="utf-8") as f:
                            f.write(content)
                            
                        rel_path = os.path.join(project["name"].replace(" ", "_").lower(), filename)
                        database.add_data_item(project["id"], rel_path, content=content)
                        success_count += 1
                        
                    database.update_statistics(project["id"])
                    st.success(f"Successfully processed {success_count} text items.")
                    st.rerun()
            else:
                # Only individual txt files uploaded
                if st.button("Process TXT files", use_container_width=True):
                    success_count = 0
                    for txt_file in txt_files:
                        content = txt_file.read().decode("utf-8")
                        filename = txt_file.name
                        target_path = os.path.join(project_folder, filename)
                        
                        with open(target_path, "w", encoding="utf-8") as f:
                            f.write(content)
                            
                        rel_path = os.path.join(project["name"].replace(" ", "_").lower(), filename)
                        database.add_data_item(project["id"], rel_path, content=content)
                        success_count += 1
                        
                    database.update_statistics(project["id"])
                    st.success(f"Successfully processed {success_count} text items.")
                    st.rerun()

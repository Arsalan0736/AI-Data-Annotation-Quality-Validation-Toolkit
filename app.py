import streamlit as st
import os
from config import DEFAULT_CLASSES
from modules import database

# Page Configuration
st.set_page_config(
    page_title="AI Data Annotation & Quality Toolkit",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling for premium feel
st.markdown("""
<style>
    .main {
        background-color: #f8f9fa;
    }
    .stButton>button {
        border-radius: 6px;
        font-weight: 500;
    }
    .css-1r6g72h {
        background-color: #1e1e24;
        color: white;
    }
    .metric-card {
        background-color: white;
        padding: 20px;
        border-radius: 8px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
        border: 1px solid #e9ecef;
        text-align: center;
    }
    .metric-value {
        font-size: 2rem;
        font-weight: bold;
        color: #4A90E2;
    }
    .metric-label {
        font-size: 0.9rem;
        color: #6c757d;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
</style>
""", unsafe_allow_html=True)

# Initialize Database
database.init_db()

# Sidebar - Project Selection & Creation
st.sidebar.title("🤖 ML Ops Annotation Toolkit")
st.sidebar.markdown("---")

# Project List
projects = database.get_projects()
project_names = [p["name"] for p in projects]

selected_project_name = None
selected_project = None

# Create Project Expander in Sidebar
with st.sidebar.expander("📁 Create New Project", expanded=False):
    new_project_name = st.text_input("Project Name")
    project_type = st.selectbox("Data Type", ["Image", "Text"])
    if st.button("Create Project", use_container_width=True):
        if new_project_name.strip():
            proj_id = database.create_project(new_project_name.strip(), project_type)
            if proj_id:
                st.success(f"Project '{new_project_name}' created!")
                st.rerun()
            else:
                st.error("Project name already exists.")
        else:
            st.error("Name cannot be empty.")

# Project selector
if project_names:
    selected_project_name = st.sidebar.selectbox("Active Project", project_names)
    selected_project = next(p for p in projects if p["name"] == selected_project_name)
    
    # Show active project summary info
    st.sidebar.info(f"Type: {selected_project['type']}")
else:
    st.sidebar.warning("No active projects. Please create one.")

st.sidebar.markdown("---")

# Page Navigation
nav_options = [
    "📊 Dashboard",
    "📥 Upload Dataset",
    "✏️ Annotation View",
    "🔍 Quality Validation",
    "🤝 Agreement Checker",
    "📈 Reports & Export"
]
page = st.sidebar.radio("Navigation", nav_options)

# Route to proper module
if selected_project is None and page != "📥 Upload Dataset":
    st.info("👋 Welcome! Please create a project or upload a dataset to begin.")
    # Show upload interface directly as fallback
    from modules import upload_page
    upload_page.render(None)
else:
    # Load module based on select
    if page == "📊 Dashboard":
        from modules import dashboard
        dashboard.render(selected_project)
    elif page == "📥 Upload Dataset":
        from modules import upload_page
        upload_page.render(selected_project)
    elif page == "✏️ Annotation View":
        from modules import annotation
        annotation.render(selected_project)
    elif page == "🔍 Quality Validation":
        from modules import validation
        validation.render(selected_project)
    elif page == "🤝 Agreement Checker":
        from modules import agreement
        agreement.render(selected_project)
    elif page == "📈 Reports & Export":
        from modules import export
        export.render(selected_project)

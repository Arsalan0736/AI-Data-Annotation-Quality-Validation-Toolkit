import streamlit as st
import pandas as pd
from modules import database

def render(project):
    st.header(f"📊 Dashboard - {project['name']}")
    
    # Fetch statistics
    stats = database.get_statistics(project["id"])
    if not stats:
        st.warning("Could not load project statistics.")
        return

    # Compute custom quality score
    # Score = 100 * (1 - (wrong + duplicate + missing + corrupted) / total)
    total = stats["total_items"]
    wrong = stats["wrong_labels_count"]
    dup = stats["duplicate_count"]
    missing = stats["missing_labels_count"]
    corr = stats["corrupted_count"]
    
    if total > 0:
        deductions = wrong + dup + missing + corr
        quality_score = max(0.0, 100.0 * (1.0 - deductions / total))
    else:
        quality_score = 100.0

    # Layout: 4 Metric Columns
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{total}</div>
            <div class="metric-label">Total Items</div>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value" style="color: #2ECC71;">{stats['annotated_count']}</div>
            <div class="metric-label">Annotated</div>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value" style="color: #F39C12;">{stats['pending_count']}</div>
            <div class="metric-label">Pending</div>
        </div>
        """, unsafe_allow_html=True)
    with col4:
        # Style color based on quality score
        q_color = "#2ECC71" if quality_score >= 85 else "#F39C12" if quality_score >= 60 else "#E74C3C"
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value" style="color: {q_color};">{quality_score:.1f}%</div>
            <div class="metric-label">Quality Score</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("###")

    # Layout: Left column for overview & issues, Right column for activity
    left_col, right_col = st.columns([3, 2])
    
    with left_col:
        st.subheader("⚠️ Quality Issues Summary")
        
        has_warnings = False
        if corr > 0:
            st.error(f"🚨 **{corr}** corrupted or unreadable files detected!")
            has_warnings = True
        if dup > 0:
            st.warning(f"👯 **{dup}** duplicate images found in dataset.")
            has_warnings = True
        if missing > 0:
            st.info(f"❓ **{missing}** items are missing annotations.")
            has_warnings = True
        if wrong > 0:
            st.warning(f"🏷️ **{wrong}** annotations flagged as potentially wrong (low similarity).")
            has_warnings = True
            
        if not has_warnings:
            st.success("🎉 No validation issues detected! Your dataset looks clean.")
            
        st.markdown("---")
        
        # Display dataset distribution summary
        st.subheader("📁 Dataset Overview")
        st.write(f"**Project Name:** {project['name']}")
        st.write(f"**Project Type:** {project['type']}")
        st.write(f"**Average Annotation Time:** {stats['avg_annotation_time']:.2f} seconds")
        st.write(f"**Last Sync:** {stats['updated_at']}")

    with right_col:
        st.subheader("🕒 Recent Activity")
        
        # Query recent annotations
        conn = database.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT a.label, a.annotator_name, a.created_at, i.filename
            FROM Annotations a
            JOIN Images i ON a.image_id = i.id
            WHERE i.project_id = ?
            ORDER BY a.created_at DESC
            LIMIT 5
        """, (project["id"],))
        recent_activities = cursor.fetchall()
        conn.close()
        
        if recent_activities:
            for act in recent_activities:
                st.markdown(f"""
                * **{act['annotator_name']}** labeled `...{act['filename'][-30:]}` as **`{act['label']}`**
                  *<span style="font-size: 0.8rem; color: gray;">{act['created_at']}</span>*
                """, unsafe_allow_html=True)
        else:
            st.info("No recent annotation activity found.")

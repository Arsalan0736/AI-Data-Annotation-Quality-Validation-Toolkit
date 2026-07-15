import streamlit as st
import pandas as pd
import json
import io
import os
from config import OUTPUTS_DIR
from modules import database, statistics

def render(project):
    st.header(f"📈 Reports & Export - {project['name']}")
    
    # 1. Renders the statistical charts at the top
    statistics.render(project)
    
    st.markdown("---")
    st.subheader("📥 Export Dataset & Ground Truth")
    
    # Load items and annotations
    items = database.get_data_items(project["id"])
    annotations = database.get_all_annotations_for_project(project["id"])
    reviews = database.get_reviews_for_project(project["id"])
    
    if not items:
        st.info("No items to export.")
        return

    # Build dataset dictionary
    # Group annotations and reviews by image_id
    ann_map = {}
    for a in annotations:
        iid = a["image_id"]
        if iid not in ann_map:
            ann_map[iid] = []
        ann_map[iid].append(a)
        
    rev_map = {r["image_id"]: r for r in reviews}
    
    # Build a consolidated list
    export_rows = []
    ground_truth_rows = []
    
    for item in items:
        iid = item["id"]
        filename = item["filename"]
        content = item["content"]
        
        # Get labels
        item_anns = ann_map.get(iid, [])
        labels = [a["label"] for a in item_anns]
        
        # Majority Vote
        from collections import Counter
        majority = "None"
        if labels:
            majority = Counter(labels).most_common(1)[0][0]
            
        # Review status
        rev = rev_map.get(iid)
        reviewer_status = "Unreviewed"
        reviewer_label = "None"
        if rev:
            reviewer_status = rev["status"]
            reviewer_label = rev["corrected_label"] if rev["corrected_label"] else majority
            
        # Final Ground Truth Label Priority:
        # 1. Reviewer corrected/approved label
        # 2. Majority vote
        # 3. None
        final_label = "None"
        if reviewer_label != "None" and reviewer_label is not None:
            final_label = reviewer_label
        elif majority != "None":
            final_label = majority

        export_rows.append({
            "item_id": iid,
            "filename": filename,
            "content": content if content else "",
            "annotations_count": len(labels),
            "all_annotations": ", ".join(labels),
            "majority_label": majority,
            "review_status": reviewer_status,
            "reviewer_label": reviewer_label,
            "final_ground_truth": final_label
        })
        
        # Ground Truth generator format
        if final_label != "None":
            ground_truth_rows.append({
                "filename": filename,
                "label": final_label
            })

    if not export_rows:
        st.warning("No data to export.")
        return

    df_export = pd.DataFrame(export_rows)
    df_gt = pd.DataFrame(ground_truth_rows)
    
    st.write(f"Consolidated dataset has **{len(df_export)}** items. Ground truth established for **{len(df_gt)}** items.")
    
    # Show preview
    with st.expander("🔍 Preview Export Data"):
        st.dataframe(df_export.head(10), use_container_width=True)

    # Export formats
    st.markdown("#### Choose Export Format")
    col_dl1, col_dl2, col_dl3 = st.columns(3)
    
    # 1. CSV Download
    with col_dl1:
        csv_buffer = io.StringIO()
        df_export.to_csv(csv_buffer, index=False)
        st.download_button(
            label="Download Full CSV",
            data=csv_buffer.getvalue(),
            file_name=f"dataset_{project['name'].lower().replace(' ', '_')}.csv",
            mime="text/csv",
            use_container_width=True
        )
        
    # 2. JSON Download
    with col_dl2:
        json_str = df_export.to_json(orient="records", indent=2)
        st.download_button(
            label="Download Full JSON",
            data=json_str,
            file_name=f"dataset_{project['name'].lower().replace(' ', '_')}.json",
            mime="application/json",
            use_container_width=True
        )
        
    # 3. Excel Download
    with col_dl3:
        excel_buffer = io.BytesIO()
        with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
            df_export.to_excel(writer, sheet_name="Full Dataset", index=False)
            df_gt.to_excel(writer, sheet_name="Ground Truth Mapping", index=False)
        st.download_button(
            label="Download Excel (XLSX)",
            data=excel_buffer.getvalue(),
            file_name=f"dataset_{project['name'].lower().replace(' ', '_')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )

    # Save Ground Truth to outputs folder
    st.markdown("---")
    st.subheader("💾 Ground Truth Generator")
    st.write("Generate a standardized `ground_truth.csv` file in the outputs directory of the toolkit.")
    
    if st.button("Generate and Write ground_truth.csv", type="secondary"):
        out_path = os.path.join(OUTPUTS_DIR, f"{project['name'].lower().replace(' ', '_')}_ground_truth.csv")
        df_gt.to_csv(out_path, index=False)
        st.success(f"Successfully generated and wrote file to: `{out_path}`")

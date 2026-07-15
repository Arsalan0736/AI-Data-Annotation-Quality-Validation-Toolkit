import streamlit as st
import pandas as pd
from collections import Counter
from modules import database

def render(project):
    st.header(f"🤝 Agreement Checker - {project['name']}")
    
    st.write("""
    Compare annotations across multiple annotators.
    This page calculates consensus (Majority Voting) and individual agreement rates.
    """)

    # Load annotations for project
    annotations = database.get_all_annotations_for_project(project["id"])
    if not annotations:
        st.info("No annotations available in this project to check agreement.")
        return

    # Group annotations by image_id
    items_annotations = {}
    for ann in annotations:
        iid = ann["image_id"]
        if iid not in items_annotations:
            items_annotations[iid] = []
        items_annotations[iid].append(ann)

    # Calculate agreement metrics per item
    agreement_data = []
    
    for iid, ann_list in items_annotations.items():
        filename = ann_list[0]["filename"]
        content = ann_list[0]["content"]
        
        # Get count of each label
        labels = [a["label"] for a in ann_list]
        total_votes = len(labels)
        
        counter = Counter(labels)
        majority_label, majority_count = counter.most_common(1)[0]
        
        agreement_percentage = (majority_count / total_votes) * 100.0
        
        # Format annotator specific details
        annotators_breakdown = ", ".join([f"{a['annotator_name']}: {a['label']}" for a in ann_list])
        
        agreement_data.append({
            "Item ID": iid,
            "Filename": filename,
            "Content Preview": content[:40] + "..." if content else "N/A",
            "Annotator Labels": annotators_breakdown,
            "Total Annotators": total_votes,
            "Majority Vote": majority_label,
            "Agreement %": agreement_percentage
        })

    if not agreement_data:
        st.warning("Could not calculate agreement.")
        return

    df_agreement = pd.DataFrame(agreement_data)
    
    # Summary Metrics
    avg_agreement = df_agreement["Agreement %"].mean()
    high_consensus = len(df_agreement[df_agreement["Agreement %"] == 100.0])
    low_consensus = len(df_agreement[df_agreement["Agreement %"] < 70.0])
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Average Agreement Rate", f"{avg_agreement:.1f}%")
    with col2:
        st.metric("100% Consensus Items", f"{high_consensus} items")
    with col3:
        st.metric("Low Consensus (<70%)", f"{low_consensus} items")

    st.markdown("### Detail Table")
    # Styling columns
    st.dataframe(
        df_agreement.style.format({"Agreement %": "{:.1f}%"}), 
        use_container_width=True
    )
    
    # Commiting Ground Truth helper
    st.markdown("---")
    st.subheader("Generate Ground Truth from Consensus")
    st.write("""
    Submit the majority vote decisions as the official ground truth. 
    This will update the database review status to 'Approved' using the majority label values.
    """)
    
    if st.button("Generate & Commit Ground Truth Reviews", type="primary"):
        count_updated = 0
        for item in agreement_data:
            # We add/update a review as Approved with the Majority Vote label
            database.add_review(
                image_id=item["Item ID"],
                reviewer_name="Majority Vote Bot",
                status="Approved",
                corrected_label=item["Majority Vote"]
            )
            count_updated += 1
            
        st.success(f"Successfully generated and committed {count_updated} ground truth reviews!")
        database.update_statistics(project["id"])

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from modules import database

def render(project):
    # This module handles rendering standard statistical panels and Plotly charts.
    st.subheader("📊 Dataset Statistics & Charts")
    
    # 1. Fetch annotations
    annotations = database.get_all_annotations_for_project(project["id"])
    stats = database.get_statistics(project["id"])
    
    if not annotations or not stats:
        st.info("No annotation data available to generate charts. Start annotating first!")
        return

    df_ann = pd.DataFrame(annotations)
    
    # Left / Right Split for Charts
    col_chart1, col_chart2 = st.columns(2)
    
    with col_chart1:
        st.markdown("#### Class Label Distribution")
        # Class distribution pie chart
        label_counts = df_ann["label"].value_counts().reset_index()
        label_counts.columns = ["Class", "Count"]
        
        fig_pie = px.pie(
            label_counts, 
            values="Count", 
            names="Class", 
            hole=0.4,
            color_discrete_sequence=px.colors.qualitative.Pastel
        )
        fig_pie.update_layout(
            margin=dict(l=20, r=20, t=20, b=20),
            legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5)
        )
        st.plotly_chart(fig_pie, use_container_width=True)

    with col_chart2:
        st.markdown("#### Dataset Completion Rate")
        # Completion horizontal stack bar chart
        total = stats["total_items"]
        annotated = stats["annotated_count"]
        pending = stats["pending_count"]
        
        fig_bar = go.Figure()
        fig_bar.add_trace(go.Bar(
            y=["Dataset"],
            x=[annotated],
            name="Annotated",
            orientation='h',
            marker=dict(color="#2ECC71")
        ))
        fig_bar.add_trace(go.Bar(
            y=["Dataset"],
            x=[pending],
            name="Pending",
            orientation='h',
            marker=dict(color="#BDC3C7")
        ))
        fig_bar.update_layout(
            barmode='stack',
            height=200,
            margin=dict(l=20, r=20, t=20, b=20),
            xaxis=dict(range=[0, total]),
            legend=dict(orientation="h", yanchor="bottom", y=-0.6, xanchor="center", x=0.5)
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    st.markdown("---")

    # Time profiling
    st.markdown("#### ⏱️ Average Annotation Time Profiling")
    
    # Compute mean annotation time by label
    avg_times = df_ann.groupby("label")["duration_seconds"].mean().reset_index()
    avg_times.columns = ["Class", "Avg Time (sec)"]
    
    fig_time = px.bar(
        avg_times,
        x="Class",
        y="Avg Time (sec)",
        color="Class",
        text_auto=".2f",
        labels={"Avg Time (sec)": "Average Time (seconds)"},
        color_discrete_sequence=px.colors.qualitative.Safe
    )
    fig_time.update_layout(
        margin=dict(l=20, r=20, t=30, b=20),
        showlegend=False
    )
    st.plotly_chart(fig_time, use_container_width=True)

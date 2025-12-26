import streamlit as st
import requests
import pandas as pd
import plotly.express as px

# This ensures every chart uses the exact same hex code for each state
STATE_COLORS = {
    "High Focus": "#2ecc71",       # Green
    "Low Focus": "#3498db",        # Blue
    "Drowsy": "#f1c40f",           # Yellow
    "High Arousal": "#9b59b6",     # Purple
    "Baseline/Neutral": "#95a5a6", # Gray
    "Artifact": "#e74c3c"          # Red
}

# Mapping for the Line Chart
SCORE_COLORS = {
    "focus_score": "#2ecc71",
    "mind_wandering_score": "#3498db",
    "drowsiness_score": "#f1c40f",
    "arousal_score": "#9b59b6"
}

st.set_page_config(page_title="MindSpeller NeuroProfiler", layout="wide")
st.markdown("<h1 style='text-align: center;'>MindSpeller EEG Profiler</h1>", unsafe_allow_html=True)
st.markdown("---")


if "uploader_key" not in st.session_state:
    st.session_state["uploader_key"] = 0

st.sidebar.header("Data Input")
uploaded_file = st.sidebar.file_uploader(
    "Upload EEG CSV", 
    type=["csv"], 
    key=f"file_uploader_{st.session_state['uploader_key']}"
)


def clear_all():
    st.session_state["uploader_key"] += 1  # Changing the key resets the widget
    for key in [k for k in st.session_state.keys() if k != "uploader_key"]:
        del st.session_state[key]
    st.rerun()

if st.sidebar.button("Clear Dashboard"):
    clear_all()


if uploaded_file:
    with st.spinner('Backend is processing signal...'):
        try:
            files = {"file": (uploaded_file.name, uploaded_file.getvalue(), "text/csv")}
            response = requests.post("http://localhost:8000/upload", files=files)
            
            if response.status_code == 200:
                data = response.json()
                profile = data.get("session_profile", {})
                timeline = data.get("timeline", [])
                scores_data = data.get("scores", [])

                # --- TOP ROW: Profile Overview ---
                col1, col2 = st.columns([1.5, 1])

                with col1:
                    st.markdown("<h3 style='text-align: center;'>Cognitive State Distribution</h3>", unsafe_allow_html=True)
                    df_pie = pd.DataFrame({
                        "State": list(profile.keys()),
                        "Percentage": list(profile.values())
                    })
                    fig_pie = px.pie(
                        df_pie,
                        values="Percentage",
                        names="State",
                        hole=0.4,
                        color="State",
                        color_discrete_map=STATE_COLORS
                    )
                    # Tighten margins to make the pie chart fill the space better
                    fig_pie.update_layout(margin=dict(t=0, b=0, l=0, r=0))
                    st.plotly_chart(fig_pie, use_container_width=True)

                with col2:
                    st.markdown("<h3 style='text-align: center;'>Key Insights</h3>", unsafe_allow_html=True)
                    if data.get("metadata", {}).get("quality_warning"):
                        st.warning("**High Noise Detected:** All segments in this file were noisy. "
                                "The results may not be reliable")
                                        
                    # Container for metrics
                    with st.container(border=True):
                        # Top State Metric
                        top_state = max(profile, key=profile.get)
                        st.metric("Predominant State", top_state, f"{profile[top_state]}% of time")
                        
                        st.divider()
                        
                        # Display other metrics in a 2x2 grid
                        m_col1, m_col2 = st.columns(2)
                        states = [s for s in profile.keys() if s != top_state]
                        
                        for i, state in enumerate(states):
                            target_col = m_col1 if i % 2 == 0 else m_col2
                            target_col.metric(label=state, value=f"{profile[state]}%")
                            
                # --- MIDDLE ROW: Timeline evolution ---
                st.markdown("---")
                st.markdown("<h3 style='text-align: center;'>Temporal Evolution of Brain States</h3>", unsafe_allow_html=True)

                timeline_data = []
                for i, state in enumerate(timeline):
                    timeline_data.append({
                        "State": state,
                        "Start": i * 30,
                        "End": (i + 1) * 30
                    })
                df_timeline = pd.DataFrame(timeline_data)

                fig_timeline = px.bar(
                    df_timeline,
                    base="Start",
                    x=[30] * len(df_timeline),
                    y=[0] * len(df_timeline),
                    color="State",
                    orientation='h',
                    text="State",
                    color_discrete_map=STATE_COLORS # Apply constant colors
                )

                fig_timeline.update_traces(
                    textposition='inside',
                    insidetextanchor='middle',
                    textfont_size=14,
                    marker_line_width=0
                )
                fig_timeline.update_layout(
                    height=150,
                    margin=dict(l=0, r=0, t=30, b=0),
                    xaxis_title="Time (seconds)",
                    yaxis=dict(visible=False), 
                    barmode='stack'
                )
                st.plotly_chart(fig_timeline, use_container_width=True)

                # --- BOTTOM ROW: Score Evolution line chart ---
                if scores_data:
                    st.markdown("---")
                    st.markdown("<h3 style='text-align: center;'>Score Evolution</h3>", unsafe_allow_html=True)
                    df_scores = pd.DataFrame(scores_data)
                    df_scores["Window"] = [f"W{i+1}" for i in range(len(df_scores))]
                    
                    fig_scores = px.line(
                        df_scores, 
                        x="Window", 
                        y=list(SCORE_COLORS.keys()),
                        labels={"value": "Ratio vs Baseline", "variable": "Metric"},
                        title="Cognitive State scores per 30s Window",
                        markers=True,
                        color_discrete_map=SCORE_COLORS
                    )

                    fig_scores.update_layout(
                        title={
                            'text': "Cognitive State scores per 30s Window",
                            'y': 0.9,
                            'x': 0.5,
                            'xanchor': 'center',
                            'yanchor': 'top'
                        },
                        margin=dict(t=50, b=20, l=20, r=20)
                    )

                    fig_scores.add_hline(y=1.0, line_dash="dash", line_color="gray", annotation_text="Baseline")
                    st.plotly_chart(fig_scores, use_container_width=True)

        except Exception as e:
            st.error(f"Could not connect to backend: {e}")

else:
    st.markdown("<br><br>", unsafe_allow_html=True)
    
    st.markdown("""
        <div style="text-align: center;">
            <h3 style="color: #31333F;">Upload an EEG CSV file (~3 mins)</h3>
            <p style="color: #555;">to see the evolution of cognitive states.</p>
        </div>
    """, unsafe_allow_html=True)

    st.markdown("<p style='text-align: center; font-size: 0.8em; color: gray;'>Format: Columns = Channels | Rows = Time points</p>", unsafe_allow_html=True)


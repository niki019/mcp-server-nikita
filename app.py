import streamlit as st
import sqlite3
import pandas as pd
import asyncio
import os
import json
import datetime
from pulse.bootstrap import bootstrap_secrets

# Unpack credentials from environment variables if present (for cloud environments)
bootstrap_secrets()

from pulse.agent.orchestrator import run_pulse_pipeline
from pulse.config import DB_PATH, get_product_config

# Set page configuration with premium tab header
st.set_page_config(
    page_title="Groww Review Pulse | Hub",
    layout="wide",
    page_icon="📊",
    initial_sidebar_state="expanded"
)

# Custom premium CSS styling (Groww Tech Vibe: Mint Green, Sleek Cards, Dark Elements)
st.markdown("""
<style>
    /* Global Styles */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    
    /* Card/Block Container Styling */
    div.stMetric {
        background-color: #1a1c23 !important;
        border: 1px solid #2e3039 !important;
        padding: 15px 20px !important;
        border-radius: 12px !important;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1) !important;
    }
    
    /* Metric Typography */
    div[data-testid="stMetricValue"] {
        color: #00d09c !important;
        font-weight: 700 !important;
        font-size: 2rem !important;
    }
    
    div[data-testid="stMetricLabel"] {
        color: #a0aec0 !important;
        font-weight: 500 !important;
        text-transform: uppercase !important;
        font-size: 0.8rem !important;
        letter-spacing: 0.05em !important;
    }
    
    /* Custom Card Containers */
    .metric-card {
        background: linear-gradient(135deg, #18191f 0%, #111217 100%);
        border: 1px solid #2b2e38;
        border-radius: 14px;
        padding: 24px;
        margin-bottom: 20px;
        box-shadow: 0 8px 16px rgba(0,0,0,0.2);
    }
    
    .metric-card h3 {
        margin: 0 0 10px 0;
        font-size: 1.1rem;
        color: #a0aec0;
        font-weight: 600;
    }
    
    .metric-card p {
        margin: 0;
        font-size: 2.2rem;
        color: #00d09c;
        font-weight: 700;
    }

    /* Premium Header */
    .header-container {
        background: linear-gradient(90deg, #00d09c 0%, #00b0ff 100%);
        padding: 4px;
        border-radius: 14px;
        margin-bottom: 30px;
    }
    .header-content {
        background-color: #0d0e12;
        padding: 24px 32px;
        border-radius: 11px;
    }
    .header-content h1 {
        margin: 0;
        color: #ffffff;
        font-size: 2.2rem;
        font-weight: 700;
        letter-spacing: -0.02em;
    }
    .header-content p {
        margin: 8px 0 0 0;
        color: #718096;
        font-size: 1.1rem;
    }

    /* Buttons */
    div.stButton > button {
        background: linear-gradient(135deg, #00d09c 0%, #05b186 100%) !important;
        color: #ffffff !important;
        font-weight: 600 !important;
        border: none !important;
        padding: 12px 24px !important;
        border-radius: 8px !important;
        transition: all 0.3s ease !important;
        box-shadow: 0 4px 12px rgba(0, 208, 156, 0.2) !important;
        width: 100% !important;
    }
    
    div.stButton > button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 20px rgba(0, 208, 156, 0.4) !important;
    }
</style>
""", unsafe_allow_html=True)

# 1. Page Header (Groww branded gradient outline)
st.markdown("""
<div class="header-container">
    <div class="header-content">
        <h1>📊 Groww Review Pulse Hub</h1>
        <p>Analyze Play Store reviews, manage Google Doc deliverable status, and audit weekly runs.</p>
    </div>
</div>
""", unsafe_allow_html=True)

# 2. Sidebar Configuration Options
st.sidebar.markdown("<h2 style='color:#00d09c;'>⚙️ Control Center</h2>", unsafe_allow_html=True)

prod_config = get_product_config("groww")
default_doc_id = prod_config.get("delivery", {}).get("google_doc_id", "") if prod_config else ""

st.sidebar.markdown("### Run Settings")
target_week = st.sidebar.text_input("ISO 8601 Week", value=datetime.date.today().strftime("%Y-W%W"))
dry_run = st.sidebar.checkbox("Dry Run (Skip Google API Writes)", value=False)
force_send = st.sidebar.checkbox("Force Rerun (Skip Ledger Check)", value=True)

st.sidebar.markdown("---")
st.sidebar.markdown("### Configured Destinations")
st.sidebar.info(f"**Google Doc:**\n`{default_doc_id}`")
st.sidebar.info(f"**Email mode:**\n`{prod_config.get('delivery', {}).get('email', {}).get('default_mode', 'draft')}`")

# 3. DB Queries & Ledger Statistics
runs_exist = os.path.exists(DB_PATH)
total_runs = 0
successful_runs = 0
failed_runs = 0
total_reviews = 0

if runs_exist:
    conn = sqlite3.connect(DB_PATH)
    try:
        # Load tables
        df_runs = pd.read_sql_query("SELECT * FROM runs ORDER BY started_at DESC", conn)
        df_deliveries = pd.read_sql_query("SELECT * FROM deliveries", conn)
        
        # Calculate stats
        total_runs = len(df_runs)
        successful_runs = len(df_runs[df_runs['status'] == 'completed'])
        failed_runs = len(df_runs[df_runs['status'] == 'failed'])
        total_reviews = df_runs['review_count'].sum()
    except Exception as e:
        df_runs = pd.DataFrame()
        df_deliveries = pd.DataFrame()
        st.error(f"Error loading ledger tables: {e}")
    finally:
        conn.close()
else:
    df_runs = pd.DataFrame()
    df_deliveries = pd.DataFrame()

# 4. Premium Stat Cards
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown(f"""
    <div class="metric-card">
        <h3>Total Weekly Runs</h3>
        <p>{total_runs}</p>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown(f"""
    <div class="metric-card">
        <h3>Successful Runs</h3>
        <p style="color:#00d09c;">{successful_runs}</p>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown(f"""
    <div class="metric-card">
        <h3>Failed Runs</h3>
        <p style="color:#ff4d4d;">{failed_runs}</p>
    </div>
    """, unsafe_allow_html=True)

with col4:
    st.markdown(f"""
    <div class="metric-card">
        <h3>Reviews Processed</h3>
        <p style="color:#00b0ff;">{total_reviews}</p>
    </div>
    """, unsafe_allow_html=True)

# 5. Interactive Execution Panel
st.subheader("🚀 Manual Run Execution")

# Display cached execution result (from session state) so it persists after page refresh
if "run_result" in st.session_state:
    result = st.session_state["run_result"]
    if result.get("status") == "completed":
        st.success("Review Pulse pipeline finished successfully!")
        st.balloons()
        st.markdown(f"### 🎉 Run ID: `{result['run_id']}`")
        st.markdown(f"- **Reviews analyzed:** {result['reviews_processed']}")
        st.markdown(f"- **Google Doc report:** [Open Google Doc]({result['doc_url']})")
    elif result.get("status") == "skipped":
        st.warning(f"Run skipped: {result.get('message')}")
    else:
        st.error(f"Run failed: {result.get('error')}")
    # Clear the session state so it doesn't repeat on subsequent manual refreshes
    del st.session_state["run_result"]

if st.sidebar.button("Trigger Weekly Review Pulse"):
    status_box = st.empty()
    status_box.info(f"Starting pipeline execution for week {target_week}...")
    
    # Run the orchestrator pipeline
    try:
        res = asyncio.run(run_pulse_pipeline(
            product_name="groww",
            iso_week=target_week,
            dry_run=dry_run,
            force_send=force_send
        ))
        
        # Save results in session state and trigger rerun to refresh metrics cards
        st.session_state["run_result"] = res
        st.rerun()
            
    except Exception as e:
        st.error(f"Pipeline crashed with exception: {e}")

# 6. Audit Logs Visualizers
tab1, tab2, tab3 = st.tabs(["📋 Execution History", "📦 Deliveries Ledger", "📖 Documentation & Guide"])

with tab1:
    st.subheader("Weekly Run History")
    if not df_runs.empty:
        # Display audit logs beautifully
        styled_runs = df_runs.copy()
        st.dataframe(
            styled_runs,
            column_config={
                "run_id": "Run ID",
                "product": "Product",
                "iso_week": "ISO Week",
                "status": "Execution Status",
                "review_count": "Reviews Count",
                "window_weeks": "Window Size (W)",
                "started_at": "Started At",
                "completed_at": "Completed At",
                "error_message": "Errors"
            },
            hide_index=True,
            use_container_width=True
        )
    else:
        st.info("No run logs found in the SQLite ledger. Run the pipeline to view data.")

with tab2:
    st.subheader("Delivered Reports & Email Teasers")
    if not df_deliveries.empty:
        st.dataframe(
            df_deliveries,
            column_config={
                "run_id": "Run ID",
                "channel": "Delivery Channel",
                "external_id": "Identifier",
                "url": st.column_config.LinkColumn("Document Link"),
                "idempotency_key": "Idempotency Key"
            },
            hide_index=True,
            use_container_width=True
        )
    else:
        st.info("No deliveries have been logged in this database yet.")

with tab3:
    st.subheader("Documentation & Project Guide")
    if os.path.exists("README.md"):
        try:
            with open("README.md", "r", encoding="utf-8") as f:
                readme_content = f.read()
            st.markdown(readme_content)
        except Exception as e:
            st.error(f"Error reading README.md file: {e}")
    else:
        st.info("README.md file not found at the root of the project.")

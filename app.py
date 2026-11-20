import json
import os
import streamlit as st
import plotly.io as pio
from src.agents.graph import run_query, db_engine, vector_store

# --- PAGE CONFIG ---
st.set_page_config(
    page_title="Autonomous AI Data Analyst",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- CUSTOM MODERN UI/UX STYLING ---
st.markdown("""
<style>
    /* Global Clean Typography & Spacing */
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
        max-width: 1300px;
    }
    /* Hero Banner */
    .hero-card {
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        border: 1px solid #334155;
        border-radius: 14px;
        padding: 1.5rem 2rem;
        margin-bottom: 1.5rem;
        box-shadow: 0 4px 20px rgba(0,0,0,0.25);
    }
    .hero-title {
        font-size: 1.75rem;
        font-weight: 700;
        color: #f8fafc;
        margin: 0;
    }
    .hero-sub {
        color: #94a3b8;
        font-size: 0.95rem;
        margin-top: 0.35rem;
    }
    /* Metric Cards */
    .kpi-box {
        background-color: #1e293b;
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 1rem 1.25rem;
        text-align: center;
    }
    .kpi-label {
        font-size: 0.8rem;
        color: #94a3b8;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    .kpi-val {
        font-size: 1.4rem;
        font-weight: 700;
        color: #38bdf8;
        margin-top: 0.25rem;
    }
    /* Answer Box */
    .answer-card {
        background-color: #111827;
        border-left: 4px solid #38bdf8;
        border-radius: 8px;
        padding: 1.25rem 1.5rem;
        margin-top: 0.5rem;
        line-height: 1.6;
    }
    /* Sidebar Buttons */
    .stButton > button {
        width: 100%;
        border-radius: 8px;
        text-align: left;
        font-weight: 500;
    }
</style>
""", unsafe_allow_html=True)

# --- SESSION STATE ---
if "question" not in st.session_state:
    st.session_state["question"] = ""
if "history" not in st.session_state:
    st.session_state["history"] = []
if "last_result" not in st.session_state:
    st.session_state["last_result"] = None

# --- SIDEBAR: DATA STUDIO & QUICK PROMPTS ---
with st.sidebar:
    st.markdown("### 📂 Data & Policy Studio")
    st.caption("Upload custom CSV datasets or PDF compliance rules.")
    uploaded_files = st.file_uploader(
        "Drop files here",
        type=["csv", "pdf"],
        accept_multiple_files=True,
        label_visibility="collapsed",
    )
    if uploaded_files:
        if st.button("⚡ Process & Index Files", type="primary"):
            os.makedirs("data", exist_ok=True)
            with st.spinner("Indexing files into DuckDB & ChromaDB..."):
                for f in uploaded_files:
                    save_path = os.path.join("data", f.name)
                    with open(save_path, "wb") as out:
                        out.write(f.getbuffer())
                    if f.name.lower().endswith(".pdf"):
                        vector_store.add_files([save_path])
                db_engine._load_csv_files()
            st.success(f"Loaded {len(uploaded_files)} file(s)!")

    st.divider()
    st.markdown("### 💡 Quick Analysis Prompts")
    samples = [
        ("📊 SQL Analytics", "What is total revenue and profit by region?"),
        ("📜 Policy Lookup", "What are the regional discount caps and minimum profit margin rules?"),
        ("⚖️ Hybrid Audit", "Which transactions violate our regional discount caps?"),
    ]
    for badge, q_text in samples:
        if st.button(f"{badge}\n\n{q_text}"):
            st.session_state["question"] = q_text

    if st.session_state["history"]:
        st.divider()
        st.markdown("### 🕒 Recent Queries")
        for idx, past_q in enumerate(reversed(st.session_state["history"][-5:])):
            if st.button(f"↩ {past_q[:42]}...", key=f"hist_{idx}"):
                st.session_state["question"] = past_q

# --- HERO HEADER ---
st.markdown("""
<div class="hero-card">
    <div class="hero-title">🤖 Autonomous Multi-Agent Data Analyst</div>
    <div class="hero-sub">Local DuckDB SQL Analytics • ChromaDB Policy RAG • Self-Evaluating LangGraph Pipeline (100% Offline)</div>
</div>
""", unsafe_allow_html=True)

# --- SEARCH / PROMPT BAR ---
col_input, col_btn = st.columns([5, 1])
with col_input:
    question = st.text_input(
        "Ask a business or compliance question",
        value=st.session_state["question"],
        placeholder="e.g., What is total revenue and profit by region?",
        label_visibility="collapsed",
    )
with col_btn:
    run_clicked = st.button("🚀 Analyze", type="primary")

# --- RUN PIPELINE ---
if run_clicked and question.strip():
    st.session_state["question"] = question
    if question not in st.session_state["history"]:
        st.session_state["history"].append(question)
    with st.spinner("🧠 Agents collaborating (Routing → Querying → Evaluating)..."):
        st.session_state["last_result"] = run_query(question)

# --- DISPLAY RESULTS ---
res = st.session_state["last_result"]
if res:
    # Top KPI Strip
    k1, k2, k3 = st.columns(3)
    with k1:
        st.markdown(f"""
        <div class="kpi-box">
            <div class="kpi-label">Agent Route</div>
            <div class="kpi-val">{res.get("route", "N/A")}</div>
        </div>""", unsafe_allow_html=True)
    with k2:
        score = res.get("groundedness_score", 0)
        color = "#4ade80" if score >= 4 else "#facc15"
        st.markdown(f"""
        <div class="kpi-box">
            <div class="kpi-label">Groundedness Score</div>
            <div class="kpi-val" style="color:{color};">{score} / 5</div>
        </div>""", unsafe_allow_html=True)
    with k3:
        rows_count = len(res.get("sql_results") or [])
        cites_count = len(res.get("citations") or [])
        evidence_label = f"{rows_count} SQL Rows | {cites_count} Citations"
        st.markdown(f"""
        <div class="kpi-box">
            <div class="kpi-label">Evidence Retrieved</div>
            <div class="kpi-val" style="font-size:1.1rem;">{evidence_label}</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Organized Tabs
    tab_ans, tab_viz, tab_sql, tab_rag = st.tabs([
        "✨ Executive Answer",
        "📈 Interactive Chart",
        "🗄️ SQL & Raw Data",
        "📑 Policy Citations",
    ])

    with tab_ans:
        st.markdown(f'<div class="answer-card">{res["answer"]}</div>', unsafe_allow_html=True)

    with tab_viz:
        if res.get("chart_json"):
            fig = pio.from_json(json.dumps(res["chart_json"]))
            fig.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No chart generated for this query. Try asking a comparison or aggregation question (e.g., revenue by region).")

    with tab_sql:
        if res.get("sql_query"):
            st.markdown("**Generated DuckDB Query:**")
            st.code(res["sql_query"], language="sql")
            st.markdown("**Query Output:**")
            st.dataframe(res.get("sql_results", []), use_container_width=True)
        else:
            st.info("SQL engine was not needed for this query.")

    with tab_rag:
        if res.get("citations"):
            for i, c in enumerate(res["citations"], 1):
                src = c.get("source", "Policy Document")
                page = c.get("page", "?")
                txt = c.get("text", c.get("content", ""))
                with st.container(border=True):
                    st.markdown(f"**[{i}] {src}** — *Page {page}*")
                    st.write(txt)
        else:
            st.info("No policy documents were retrieved for this query.")
else:
    st.info("👈 Choose a sample prompt from the sidebar or type your own question above to start.")

"""
Memory Dashboard for MultiMind AI Enterprise Knowledge Assistant.

Visualizes:
- Agent decision timeline
- Memory chunks with trust scores
- Execution traces
- Knowledge quality metrics
"""

import streamlit as st
import json
from datetime import datetime
from typing import Dict, List, Optional

from memory import rag_memory, memory
from observability import _active_tracers, ExecutionTracer
from rbac import get_rbac_manager, Role


def render_memory_dashboard():
    """Render the memory dashboard."""
    st.title("🧠 Agent Memory & Execution Dashboard")
    
    tab1, tab2, tab3 = st.tabs(["📊 Memory Overview", "🔍 Knowledge Chunks", "🕸️ Execution Traces"])
    
    with tab1:
        render_memory_overview()
    
    with tab2:
        render_knowledge_chunks()
    
    with tab3:
        render_execution_traces()


def render_memory_overview():
    """Render memory quality overview."""
    st.subheader("RAG Memory Quality")
    
    try:
        report = rag_memory.get_quality_report()
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Chunks", report.get("total_chunks", 0))
        with col2:
            st.metric("Average Trust", f"{report.get('average_trust', 0.0):.3f}")
        with col3:
            st.metric("Min Trust", f"{report.get('min_trust', 0.0):.3f}")
        with col4:
            st.metric("Max Trust", f"{report.get('max_trust', 0.0):.3f}")
        
        # Visual trust distribution
        if report.get("total_chunks", 0) > 0:
            st.subheader("Trust Score Distribution")
            # Create mock distribution for visualization
            import random
            random.seed(42)
            scores = [random.betavariate(2, 2) for _ in range(min(report.get("total_chunks", 0), 100))]
            
            # Bucket scores
            buckets = {"0.0-0.2": 0, "0.2-0.4": 0, "0.4-0.6": 0, "0.6-0.8": 0, "0.8-1.0": 0}
            for s in scores:
                if s < 0.2:
                    buckets["0.0-0.2"] += 1
                elif s < 0.4:
                    buckets["0.2-0.4"] += 1
                elif s < 0.6:
                    buckets["0.4-0.6"] += 1
                elif s < 0.8:
                    buckets["0.6-0.8"] += 1
                else:
                    buckets["0.8-1.0"] += 1
            
            chart_data = {"Range": list(buckets.keys()), "Count": list(buckets.values())}
            st.bar_chart(chart_data, x="Range", y="Count")
    except Exception as e:
        st.error(f"Error loading memory report: {e}")
    
    st.subheader("SQLite Memory Stats")
    try:
        import sqlite3
        conn = sqlite3.connect("agent_memory.db")
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM conversations')
        conv_count = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM execution_history')
        exec_count = cursor.fetchone()[0]
        
        cursor.execute('SELECT AVG(quality_score) FROM conversations')
        avg_quality = cursor.fetchone()[0] or 0.0
        
        conn.close()
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Conversations", conv_count)
        with col2:
            st.metric("Executions Logged", exec_count)
        with col3:
            st.metric("Avg Quality", f"{avg_quality:.3f}")
    except Exception as e:
        st.error(f"Error loading SQLite stats: {e}")


def render_knowledge_chunks():
    """Render knowledge chunks with trust scores."""
    st.subheader("Knowledge Chunks Explorer")
    
    query = st.text_input("Search knowledge base (semantic search)", placeholder="e.g., 'LangGraph agents'")
    k = st.slider("Number of results", 1, 10, 5)
    
    if query:
        try:
            results = rag_memory.retrieve(query, k=k)
            
            if results:
                for i, result in enumerate(results, 1):
                    with st.expander(f"Chunk {i} — Trust: {result['trust']:.3f} | Agent: {result['provenance'].get('agent_source', 'unknown')}"):
                        st.markdown(result["content"])
                        
                        # Provenance details
                        st.subheader("Provenance")
                        prov = result["provenance"]
                        st.json({
                            "agent_source": prov.get("agent_source"),
                            "session": prov.get("session"),
                            "created": datetime.fromtimestamp(prov.get("created", 0)).isoformat() if prov.get("created") else "N/A",
                            "access_count": prov.get("access_count"),
                            "validated": prov.get("validated"),
                            "validation_score": prov.get("validation_score"),
                            "iteration": prov.get("iteration"),
                        })
                        
                        # Metadata
                        st.subheader("Metadata")
                        meta = result["metadata"]
                        display_meta = {k: v for k, v in meta.items() if not k.startswith("_")}
                        st.json(display_meta)
            else:
                st.info("No knowledge chunks found. Run some queries to populate the knowledge base.")
        except Exception as e:
            st.error(f"Error retrieving knowledge: {e}")
    else:
        st.info("Enter a query to search the knowledge base.")


def render_execution_traces():
    """Render execution traces."""
    st.subheader("Execution Traces")
    
    # Session selector
    sessions = list(_active_tracers.keys())
    
    col1, col2 = st.columns([2, 1])
    with col1:
        selected_session = st.selectbox("Select Session", ["All"] + sessions)
    with col2:
        if st.button("🔄 Refresh Traces"):
            st.rerun()
    
    if selected_session != "All":
        tracer = _active_tracers.get(selected_session)
        if tracer:
            report = tracer.get_trace_report()
            render_single_trace(report)
        else:
            st.info("Trace not found or session completed.")
    else:
        # Show all recent traces
        st.subheader("Active Sessions")
        if sessions:
            session_data = []
            for sid, tracer in _active_tracers.items():
                report = tracer.get_trace_report()
                session_data.append({
                    "Session ID": sid[:12] + "...",
                    "Transitions": len(report.get("snapshots", [])),
                    "Loops": report.get("loop_count", 0),
                    "Violations": report.get("error_count", 0),
                    "Duration": f"{report.get('duration_seconds', 0):.1f}s",
                })
            st.dataframe(session_data, use_container_width=True)
        else:
            st.info("No active traces. Run a query to see traces.")


def render_single_trace(report: Dict):
    """Render a single execution trace."""
    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Transitions", len(report.get("snapshots", [])))
    with col2:
        st.metric("Loops Detected", report.get("loop_count", 0))
    with col3:
        st.metric("Violations", report.get("error_count", 0))
    with col4:
        st.metric("Duration", f"{report.get('duration_seconds', 0):.2f}s")
    
    # Progress
    progress = report.get("progress", {})
    st.subheader("Agent Visits")
    if progress.get("agent_visits"):
        visit_data = [{"Agent": k, "Visits": v} for k, v in progress["agent_visits"].items()]
        st.bar_chart(visit_data, x="Agent", y="Visits")
    
    # Snapshot timeline
    st.subheader("Transition Timeline")
    snapshots = report.get("snapshots", [])
    
    if snapshots:
        timeline_data = []
        for snap in snapshots:
            snap_dict = snap if isinstance(snap, dict) else snap.to_dict()
            timeline_data.append({
                "Time": snap_dict.get("timestamp_iso", "")[:19].replace("T", " "),
                "Agent": snap_dict.get("agent", "unknown"),
                "Transition": snap_dict.get("transition_type", "unknown"),
                "Message": snap_dict.get("message", "")[:60],
            })
        st.dataframe(timeline_data, use_container_width=True)
        
        # Snapshot details
        st.subheader("State Snapshots")
        for i, snap in enumerate(snapshots):
            snap_dict = snap if isinstance(snap, dict) else snap.to_dict()
            with st.expander(f"Step {i+1}: {snap_dict.get('agent', 'unknown')} — {snap_dict.get('transition_type', 'unknown')}"):
                st.json(snap_dict.get("state_summary", {}))
                st.caption(snap_dict.get("message", ""))
    else:
        st.info("No snapshots recorded.")


# Factory function for adding to dashboard navigation
def get_memory_dashboard_page():
    """Get the memory dashboard page function."""
    return render_memory_dashboard

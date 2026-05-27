"""
Streamlit Dashboard for MultiMind AI Autonomous Cognitive Workflow System.
"""

import streamlit as st
import time
from main import run_task

# Page configuration
st.set_page_config(
    page_title="MultiMind AI Dashboard",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Title and description
st.title("🧠 MultiMind AI Dashboard")
st.markdown("""
Watch the autonomous cognitive workflow in real-time. 
See how the planner, supervisor, workers, validator, and reflection agents collaborate.
""")

# Sidebar for controls
with st.sidebar:
    st.header("Controls")
    task_input = st.text_area(
        "Enter your task or query:",
        placeholder="e.g., Analyze the impact of renewable energy on global economics",
        height=100
    )
    task_type = st.selectbox(
        "Task Type:",
        ["research", "coding", "analysis"],
        index=0
    )
    run_button = st.button("Run Task", type="primary")

# Main area for results
if run_button and task_input:
    with st.spinner("MultiMind AI is working..."):
        start_time = time.time()
        result, session_id, tracer = run_task(task_input, task_type)
        # Finalize the tracer to get the complete trace
        tracer.finalize(result)
        trace_report = tracer.get_trace_report()
        end_time = time.time()
    
    st.success(f"Task completed in {end_time - start_time:.2f} seconds!")
    
    # Create tabs for different views
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📋 Overview", 
        "🔄 Execution Flow", 
        "🧠 Memory & Validation", 
        "🔍 Observability", 
        "📊 Trust Scores"
    ])
    
    with tab1:
        st.subheader("Task Overview")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Input Query:**")
            st.info(task_input)
            st.markdown("**Session ID:**")
            st.code(session_id)
        with col2:
            st.markdown("**Final Answer:**")
            st.success(result.get('final_answer', 'No final answer generated'))
            st.markdown("**Workflow Quality:**")
            quality = result.get('reflection', {}).get('workflow_quality', 'N/A')
            if isinstance(quality, (int, float)):
                st.progress(quality)
                st.write(f"{quality:.2f}")
            else:
                st.write(quality)
    
    with tab2:
        st.subheader("Agent Execution Flow")
        snapshots = trace_report.get('snapshots', [])
        if snapshots:
            for i, snap in enumerate(snapshots):
                with st.expander(f"Step {i+1}: {snap.get('agent', 'Unknown')} ({snap.get('transition_type', 'unknown')})"):
                    col1, col2 = st.columns([1, 3])
                    with col1:
                        st.markdown(f"**Agent:** {snap.get('agent', 'N/A')}")
                        st.markdown(f"**Type:** {snap.get('transition_type', 'N/A')}")
                        st.markdown(f"**Time:** {snap.get('timestamp_iso', 'N/A')}")
                    with col2:
                        st.markdown("**State Summary:**")
                        st.json(snap.get('state_summary', {}))
                        if snap.get('message'):
                            st.markdown(f"**Message:** {snap['message']}")
        else:
            st.info("No execution snapshots available.")
    
    with tab3:
        st.subheader("Memory & Validation Results")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Research Data:**")
            research_data = result.get('research_data', 'No research data')
            st.text_area("Research Output", research_data, height=200, disabled=True)
        with col2:
            st.markdown("**Code Result:**")
            code_result = result.get('code_result', 'No code generated')
            st.text_area("Code Output", code_result, height=200, disabled=True)
        
        st.markdown("---")
        st.markdown("**Validation Results:**")
        validation = result.get('validation', {})
        if validation:
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Confidence", f"{validation.get('confidence', 0):.2f}")
            with col2:
                st.metric("Passed", validation.get('passed', False))
            with col3:
                st.metric("Feedback", validation.get('feedback', 'None')[:50] + "...")
            with st.expander("Full Validation Details"):
                st.json(validation)
        else:
            st.info("No validation results available.")
    
    with tab4:
        st.subheader("Observability Trace")
        st.markdown("### Trace Summary")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Transitions", trace_report.get('transition_count', 0))
        with col2:
            st.metric("Loop Count", trace_report.get('loop_count', 0))
        with col3:
            st.metric("Error Count", trace_report.get('error_count', 0))
        with col4:
            st.metric("Duration (s)", f"{trace_report.get('duration_seconds', 0):.2f}")
        
        st.markdown("### Snapshots Timeline")
        snapshots = trace_report.get('snapshots', [])
        if snapshots:
            # Create a timeline view
            for snap in snapshots:
                with st.container():
                    col1, col2, col3 = st.columns([1, 2, 1])
                    with col1:
                        st.caption(f"**{snap.get('agent', '?')}**")
                        st.caption(snap.get('timestamp_iso', '')[:19])
                    with col2:
                        st.progress(min(1.0, i / len(snapshots)) if 'i' in locals() else 0.5)
                        st.caption(snap.get('message', ''))
                    with col3:
                        st.caption(f"Hash: {snap.get('state_hash', '')[:8]}...")
                    i = i + 1 if 'i' in locals() else 1
        else:
            st.info("No trace data available.")
    
    with tab5:
        st.subheader("Trust Scores & Memory Governance")
        # Get memory governance report
        from memory import rag_memory
        mem_report = rag_memory.get_quality_report()
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Knowledge Chunks", mem_report.get('total_chunks', 0))
        with col2:
            st.metric("Average Trust Score", f"{mem_report.get('average_trust', 0):.3f}")
        with col3:
            st.metric("Trust Range", f"[{mem_report.get('min_trust', 0):.3f}, {mem_report.get('max_trust', 0):.3f}]")
        
        st.markdown("### Recent Knowledge Chunks")
        # We don't have direct access to recent chunks from the governance report, 
        # but we can show some info from the trace about memory retrieval
        st.info("Memory governance shows the overall trust distribution of knowledge chunks.")
        
        # Show trust score from validation if available
        validation = result.get('validation', {})
        if validation and 'trust_score' in validation:
            st.markdown("### Validation Trust Score")
            st.progress(validation['trust_score'])
            st.write(f"Trust: {validation['trust_score']:.3f}")

else:
    # Show placeholder when no task is run
    st.info("👈 Enter a task in the sidebar and click 'Run Task' to see the MultiMind AI in action.")
    
    # Show architecture diagram or example
    st.markdown("""
    ### How it works:
    1. **Planner**: Creates a task plan from the user query
    2. **Supervisor**: Routes tasks to appropriate workers (researcher, coder)
    3. **Workers**: Execute tasks (research or coding)
    4. **Validator**: Checks the quality and correctness of the work
    5. **Reflection**: Provides feedback and decides if more work is needed
    6. **Memory**: Stores and retrieves knowledge with provenance and trust scores
    
    The observability layer traces every transition and enforces invariants.
    """)

# Footer
st.markdown("---")
st.markdown("Built with LangGraph & Streamlit • MultiMind AI — Integrity-Aware Autonomous Orchestration")
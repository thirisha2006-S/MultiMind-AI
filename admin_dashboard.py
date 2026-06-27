"""
Enterprise Admin Dashboard for MultiMind AI.

Displays:
- Active users
- Agent execution history
- AI usage analytics
- Uploaded documents
- Security alerts
- Query statistics
- Failed approval requests
- Audit logs
"""

import streamlit as st
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from auth import get_auth_manager, is_authenticated, get_current_user
from rbac import get_rbac_manager, Role
from security import get_security_scanner
from approval import get_approval_manager
from feedback import get_feedback_store
from memory import memory, rag_memory
from observability import _active_tracers


def render_admin_dashboard():
    """Render the enterprise admin dashboard."""
    # Check authentication and role
    if not is_authenticated():
        st.warning("🔒 Please login to access the admin dashboard.")
        return
    
    user = get_current_user()
    if not user:
        st.error("Session expired. Please login again.")
        return
    
    # RBAC check
    rbac = get_rbac_manager()
    rbac_user = rbac.get_user(user["user_id"])
    if not rbac_user or rbac_user.role != Role.ADMIN.value:
        st.error("🚫 Access denied. Admin role required.")
        return
    
    st.title("🏢 Enterprise Admin Dashboard")
    st.markdown(f"Welcome, **{user['username']}** | Role: **{user['role']}**")
    
    # Time range selector
    col1, col2, col3 = st.columns(3)
    with col1:
        time_range = st.selectbox("Time Range", ["Last 24 hours", "Last 7 days", "Last 30 days", "All time"], index=1)
    with col2:
        st.metric("Active Sessions", len(_active_tracers))
    with col3:
        st.metric("Total Users", len(rbac.roles))
    
    st.markdown("---")
    
    # Tabs
    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        "👥 Users & Sessions",
        "🤖 Agent Analytics",
        "🔐 Security & Audit",
        "📄 Documents",
        "📊 Usage Stats",
        "⚠️ Alerts & Approvals",
        "🩺 Knowledge Doctor"
    ])
    
    with tab1:
        render_users_tab(rbac)
    
    with tab2:
        render_agent_analytics_tab()
    
    with tab3:
        render_security_tab()
    
    with tab4:
        render_documents_tab()
    
    with tab5:
        render_usage_stats_tab()
    
    with tab6:
        render_alerts_tab()


def render_users_tab(rbac):
    """Render users and sessions tab."""
    st.subheader("Registered Users")
    
    users_data = []
    for user_id, user in rbac.roles.items():
        users_data.append({
            "User ID": user.user_id,
            "Username": user.username,
            "Role": user.role,
            "Department": user.department or "N/A",
        })
    
    if users_data:
        st.dataframe(users_data, use_container_width=True)
    else:
        st.info("No users registered.")
    
    st.subheader("Active Sessions")
    auth_mgr = get_auth_manager()
    active_sessions = auth_mgr.get_active_sessions()
    
    if active_sessions:
        session_data = []
        for sess in active_sessions:
            session_data.append({
                "Session ID": sess["session_id"][:12] + "...",
                "User": sess["username"],
                "Role": sess["role"],
                "Created": sess["created_at"][:19].replace("T", " "),
                "Expires": sess["expires_at"][:19].replace("T", " "),
            })
        st.dataframe(session_data, use_container_width=True)
    else:
        st.info("No active sessions.")


def render_agent_analytics_tab():
    """Render agent analytics tab."""
    st.subheader("Agent Execution History")
    
    # Get execution history from memory
    try:
        import sqlite3
        conn = sqlite3.connect("agent_memory.db")
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT agent, COUNT(*) as count, AVG(success) as success_rate, MAX(timestamp) as last_used
            FROM execution_history
            GROUP BY agent
            ORDER BY count DESC
        ''')
        
        rows = cursor.fetchall()
        conn.close()
        
        if rows:
            agent_data = []
            for row in rows:
                agent_data.append({
                    "Agent": row[0],
                    "Executions": row[1],
                    "Success Rate": f"{row[2]*100:.1f}%" if row[2] else "N/A",
                    "Last Used": row[3][:19].replace("T", " ") if row[3] else "Never",
                })
            st.dataframe(agent_data, use_container_width=True)
        else:
            st.info("No execution history yet. Run some queries first.")
    except Exception as e:
        st.error(f"Error loading agent history: {e}")
    
    st.subheader("Memory Quality Report")
    try:
        report = rag_memory.get_quality_report()
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Knowledge Chunks", report.get("total_chunks", 0))
        with col2:
            st.metric("Average Trust Score", f"{report.get('average_trust', 0.0):.3f}")
        with col3:
            st.metric("Trust Range", f"[{report.get('min_trust', 0.0):.3f}, {report.get('max_trust', 0.0):.3f}]")
    except Exception as e:
        st.error(f"Error loading memory report: {e}")


def render_security_tab():
    """Render security and audit tab."""
    st.subheader("Security Events Log")
    
    scanner = get_security_scanner()
    
    # Filter options
    col1, col2 = st.columns(2)
    with col1:
        severity_filter = st.selectbox("Filter by Severity", ["All", "critical", "high", "medium", "low"], index=0)
    with col2:
        event_type_filter = st.selectbox("Filter by Type", ["All", "prompt_injection", "pii_detected", "sql_injection", "unauthorized_access", "approval_required"], index=0)
    
    severity = None if severity_filter == "All" else severity_filter
    
    events = scanner.audit_logger.get_security_events(severity=severity, limit=100)
    
    if event_type_filter != "All":
        events = [e for e in events if e.get("event_type") == event_type_filter]
    
    if events:
        event_data = []
        for event in events[:50]:
            event_data.append({
                "Time": event.get("timestamp_iso", "")[:19].replace("T", " "),
                "Type": event.get("event_type", ""),
                "Severity": event.get("severity", ""),
                "User": event.get("user_id", "N/A"),
                "Agent": event.get("agent", "N/A"),
                "Description": event.get("description", "")[:80],
            })
        st.dataframe(event_data, use_container_width=True)
    else:
        st.info("No security events recorded.")
    
    st.subheader("Audit Log")
    try:
        audit_entries = scanner.audit_logger.get_audit_log(limit=50)
        if audit_entries:
            audit_data = []
            for entry in audit_entries:
                audit_data.append({
                    "Time": entry.get("timestamp_iso", "")[:19].replace("T", " "),
                    "Event": entry.get("event_type", ""),
                    "User": entry.get("user_id", "N/A"),
                    "Agent": entry.get("agent", "N/A"),
                    "Description": entry.get("description", "")[:80],
                })
            st.dataframe(audit_data, use_container_width=True)
        else:
            st.info("No audit log entries yet.")
    except Exception as e:
        st.error(f"Error loading audit log: {e}")


def render_documents_tab():
    """Render documents tab."""
    st.subheader("Uploaded Documents")
    st.info("Document management requires integration with the document store. Documents uploaded via RAG appear here with metadata.")
    
    try:
        # Try to get documents from memory if available
        if hasattr(rag_memory, 'vector_store') and rag_memory.vector_store:
            # FAISS doesn't expose documents directly, but we can show stats
            total = rag_memory.vector_store.index.ntotal
            st.metric("Total Vectors in Store", total)
            st.caption("Individual document management coming soon.")
        else:
            st.info("No documents in vector store yet.")
    except Exception as e:
        st.info("Vector store not initialized or empty.")


def render_usage_stats_tab():
    """Render usage statistics tab."""
    st.subheader("Query Statistics")
    
    try:
        import sqlite3
        conn = sqlite3.connect("agent_memory.db")
        cursor = conn.cursor()
        
        # Total queries
        cursor.execute('SELECT COUNT(*) FROM conversations')
        total_convs = cursor.fetchone()[0]
        
        # Recent activity (last 7 days)
        cutoff = (datetime.now() - timedelta(days=7)).isoformat()
        cursor.execute('SELECT COUNT(*) FROM conversations WHERE timestamp >= ?', (cutoff,))
        recent_convs = cursor.fetchone()[0]
        
        conn.close()
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Conversations", total_convs)
        with col2:
            st.metric("Recent (7 days)", recent_convs)
        with col3:
            st.metric("Avg per day", f"{recent_convs/7:.1f}" if recent_convs > 0 else "0")
    except Exception as e:
        st.error(f"Error loading stats: {e}")
    
    st.subheader("Feedback Statistics")
    try:
        store = get_feedback_store()
        trends = store.get_feedback_trends(days=7)
        if trends:
            trend_data = []
            for date, counts in trends.items():
                trend_data.append({
                    "Date": date,
                    "👍 Positive": counts.get("thumbs_up", 0),
                    "👎 Negative": counts.get("thumbs_down", 0),
                    "Ratings": counts.get("rating", 0),
                })
            st.dataframe(trend_data, use_container_width=True)
        else:
            st.info("No feedback recorded in the last 7 days.")
        
        # Show retraining signals
        signals = store.get_retraining_signals()
        if signals:
            st.subheader("⚠️ Retraining Signals")
            for signal in signals[:5]:
                st.warning(
                    f"**{signal['agent']}**: {signal['negative_count']}/{signal['total_feedback']} negative "
                    f"({signal['negative_ratio']*100:.1f}%) — {signal['recommendation']}"
                )
    except Exception as e:
        st.error(f"Error loading feedback stats: {e}")


def render_alerts_tab():
    """Render alerts and approvals tab."""
    st.subheader("Pending Approval Requests")
    
    approval_mgr = get_approval_manager()
    pending = approval_mgr.get_pending_requests()
    
    if pending:
        for req in pending:
            with st.expander(f"📋 {req.action} — {req.description[:50]}", expanded=False):
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**Request ID:** {req.request_id}")
                    st.write(f"**User:** {req.user_id}")
                    st.write(f"**Agent:** {req.agent}")
                    st.write(f"**Created:** {datetime.fromtimestamp(req.created_at).isoformat()[:19]}")
                with col2:
                    st.write(f"**Status:** {req.status}")
                    if req.expires_at:
                        st.write(f"**Expires:** {datetime.fromtimestamp(req.expires_at).isoformat()[:19]}")
                
                st.subheader("Proposed Output")
                st.text_area("Output", req.proposed_output, height=150, key=f"output_{req.request_id}", disabled=True)
                
                if req.context:
                    st.subheader("Context")
                    st.json(req.context)
                
                # Approval actions
                col1, col2, col3 = st.columns(3)
                with col1:
                    if st.button(f"✅ Approve", key=f"approve_{req.request_id}"):
                        approval_mgr.approve(req.request_id, user["user_id"], "Approved via admin dashboard")
                        st.success("Approved!")
                        st.rerun()
                with col2:
                    if st.button(f"❌ Reject", key=f"reject_{req.request_id}"):
                        approval_mgr.reject(req.request_id, user["user_id"], "Rejected via admin dashboard")
                        st.error("Rejected!")
                        st.rerun()
                with col3:
                    with st.popover("📝 Modify"):
                        mod_output = st.text_area("Modified Output", req.proposed_output, height=100, key=f"modify_{req.request_id}")
                        if st.button("Save Modification", key=f"save_mod_{req.request_id}"):
                            approval_mgr.approve(req.request_id, user["user_id"], "Modified via admin dashboard", mod_output)
                            st.success("Modified and approved!")
                            st.rerun()
    else:
        st.info("No pending approval requests.")
    
    st.subheader("Recent Security Alerts")
    scanner = get_security_scanner()
    critical_events = scanner.audit_logger.get_security_events(severity="critical", limit=10)
    high_events = scanner.audit_logger.get_security_events(severity="high", limit=10)
    
    all_alerts = critical_events + high_events
    if all_alerts:
        for event in all_alerts[:10]:
            severity_icon = "🔴" if event["severity"] == "critical" else "🟠"
            st.error(f"{severity_icon} **{event['event_type']}** — {event['description'][:80]} ({event.get('timestamp_iso', '')[:19]})")
    else:
        st.success("✅ No critical or high severity security alerts.")
    
    # Knowledge Doctor tab
    with tab7:
        render_knowledge_doctor_tab(user)


def render_knowledge_doctor_tab(user):
    """Render Knowledge Doctor health check tab."""
    from knowledge_doctor import get_knowledge_doctor
    
    st.subheader("🩺 Knowledge Health Check")
    
    doctor = get_knowledge_doctor()
    
    # Run check button
    if st.button("Run Knowledge Check"):
        with st.spinner("Analyzing knowledge base..."):
            report = doctor.check_knowledge_health()
        st.session_state.last_health_report = report.to_dict()
    
    # Display report
    if "last_health_report" in st.session_state:
        report_dict = st.session_state.last_health_report
        
        # Score display
        score = report_dict["knowledge_score"]
        st.metric("Knowledge Health Score", f"{score:.0%}", 
                 delta=None, delta_color="normal" if score >= 0.8 else "inverse")
        
        # Metrics
        st.subheader("📊 Knowledge Metrics")
        for key, value in report_dict.get("metrics", {}).items():
            if isinstance(value, float):
                st.write(f"**{key.replace('_', ' ').title()}:** {value:.2%}")
            else:
                st.write(f"**{key.replace('_', ' ').title()}:** {value}")
        
        # Issues
        st.subheader("🔍 Detected Issues")
        issues = report_dict.get("issues", [])
        if issues:
            for issue in issues:
                severity_icon = {
                    "critical": "🔴",
                    "high": "🟠",
                    "medium": "🟡",
                    "low": "🔵"
                }.get(issue.get("severity", "low"), "⚪")
                
                with st.expander(f"{severity_icon} {issue['issue_type'].title()}", expanded=False):
                    st.write(f"**{issue['description']}**")
                    st.write(f"*Affected:* {', '.join(issue['affected_sources'][:3])}")
                    st.write(f"*Action:* {issue['recommendation']}")
        else:
            st.success("✅ No issues detected. Knowledge base is healthy.")
        
        # Full report
        with st.expander("📋 Full Report"):
            st.json(report_dict)
    else:
        st.info("Click 'Run Knowledge Check' to analyze the knowledge base.")

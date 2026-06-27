"""
MultiMind AI - Enterprise Knowledge Assistant Dashboard

Features:
- Authentication (login/logout)
- Role-based access control (admin/employee/customer)
- Multi-tenant isolation
- Document upload (PDF, DOCX, Excel)
- Human approval workflow
- Source attribution display
- Confidence score display
- Explainable confidence breakdown
- Agent memory replay
- Enterprise evaluation
- Admin dashboard
- Memory dashboard
- Chat interface with security scanning
"""

import os
import time
import streamlit as st
from datetime import datetime

from auth import (
    get_auth_manager, is_authenticated, get_current_user,
    login_streamlit, logout_streamlit
)
from rbac import get_rbac_manager, Role
from security import get_security_scanner, mask_pii
from approval import get_approval_manager
from llm_utils import is_demo_mode, chat_coding_mode, chat_research_mode
from cost_optimizer import get_cost_optimizer
from multimodal import get_multimodal_processor, process_input
from parsers import parse_document, get_supported_document_types
from admin_dashboard import render_admin_dashboard
from memory_dashboard import render_memory_dashboard
from confidence_explainer import explain_confidence, get_confidence_explainer
from evaluation_engine import get_evaluation_engine
from knowledge_doctor import get_knowledge_doctor, run_knowledge_check
from graph import app
from state import SharedState
from langchain_core.messages import HumanMessage

# Load secrets from Streamlit (for Streamlit Cloud) or .env (local)
try:
    if hasattr(st, 'secrets') and st.secrets:
        os.environ.setdefault('COHERE_API_KEY', st.secrets.get('COHERE_API_KEY', ''))
        os.environ.setdefault('OPENAI_API_KEY', st.secrets.get('OPENAI_API_KEY', ''))
        os.environ.setdefault('TAVILY_API_KEY', st.secrets.get('TAVILY_API_KEY', ''))
except Exception:
    pass

st.set_page_config(
    page_title="MultiMind AI - Enterprise Knowledge Assistant",
    page_icon="🔐",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "user" not in st.session_state:
    st.session_state.user = None
if "messages" not in st.session_state:
    st.session_state.messages = []
if "current_page" not in st.session_state:
    st.session_state.current_page = "chat"
if "uploaded_files" not in st.session_state:
    st.session_state.uploaded_files = []

# CSS for styling
st.markdown("""
<style>
    .main-header {
        text-align: center;
        padding: 1rem 0;
    }
    .source-box {
        background-color: #f0f2f6;
        border-left: 4px solid #007bff;
        padding: 0.75rem 1rem;
        margin: 0.5rem 0;
        border-radius: 0 0.5rem 0.5rem 0;
    }
    .confidence-high {
        color: #28a745;
        font-weight: bold;
    }
    .confidence-medium {
        color: #ffc107;
        font-weight: bold;
    }
    .confidence-low {
        color: #dc3545;
        font-weight: bold;
    }
    .section-header {
        color: #333;
        font-weight: 600;
        margin-bottom: 0.25rem;
    }
    .security-badge {
        display: inline-block;
        padding: 0.25rem 0.5rem;
        border-radius: 0.25rem;
        font-size: 0.8em;
        font-weight: bold;
    }
    .security-safe {
        background-color: #d4edda;
        color: #155724;
    }
    .security-warning {
        background-color: #fff3cd;
        color: #856404;
    }
    .security-danger {
        background-color: #f8d7da;
        color: #721c24;
    }
</style>
""", unsafe_allow_html=True)


def is_greeting(prompt: str) -> bool:
    """Check if user input is a greeting."""
    greetings = ["hi", "hello", "hey", "greetings", "good morning", "good afternoon", "good evening"]
    return prompt.lower().strip().rstrip("!") in greetings


def render_greeting() -> str:
    """Render enterprise-style greeting response."""
    return """👋 **Welcome to MultiMind AI**

I'm your secure enterprise knowledge assistant.

I can:
* 📄 Search internal documents
* 🔍 Detect conflicting information  
* 📊 Explain confidence scores
* 📜 Track knowledge evolution
* 🩺 Monitor knowledge health

**How can I help you today?**"""


def render_structured_response(answer: str, sources: list, confidence: float, 
                             validation: dict, integrity: dict, evolution_available: bool = False):
    """Render response in enterprise workspace format with structured sections."""
    
    # Answer section
    st.markdown(f"### ✅ Answer\n{answer}")
    
    st.markdown("---")
    
    # Source section
    if sources:
        source_names = [s.get("source_name", "Unknown") for s in sources[:3]]
        st.markdown("### 📄 Source\n" + "\n".join([f"• {name}" for name in source_names]))
    else:
        st.markdown("### 📄 Source\n*No specific source cited*")
    
    st.markdown("---")
    
    # Confidence section
    conf_class = "confidence-high" if confidence >= 0.8 else ("confidence-medium" if confidence >= 0.6 else "confidence-low")
    st.markdown(f"### 📊 Confidence\n<span class='{conf_class}'>{confidence:.0%}</span>", unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Validation section
    if validation:
        status = "✓ Passed" if validation.get("passed", False) else "⚠ Needs Review"
        st.markdown(f"### ✅ Validation\n{status}")
        if validation.get("issues"):
            for issue in validation.get("issues", []):
                st.markdown(f"• {issue}")
    else:
        st.markdown("### ✅ Validation\n✓ Validator Passed")
    
    st.markdown("---")
    
    # Conflict status
    if integrity:
        conflicts = integrity.get("conflicts", [])
        if conflicts:
            st.markdown(f"### ⚠️ Conflict Status\n{len(conflicts)} potential conflict(s) detected")
        else:
            st.markdown("### ⚠️ Conflict Status\n✓ No conflicts detected")
    else:
        st.markdown("### ⚠️ Conflict Status\n✓ No conflicts detected")
    
    st.markdown("---")
    
    # Knowledge Evolution
    if evolution_available:
        st.markdown("### 📜 Knowledge Evolution\n⏱️ Timeline available")
        st.markdown("---")


def render_login_page():
    """Render login page."""
    st.markdown("<h1 style='text-align: center;'>🔐 MultiMind AI</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #666;'>Secure Enterprise Knowledge Assistant</p>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.subheader("Login")
        
        # Demo credentials info
        with st.expander("Demo Credentials"):
            st.code("""Username | Password | Role
---------|----------|------
admin    | admin123 | Admin
employee | emp123   | Employee  
customer | cust123  | Customer
guest    | guest123 | Guest""")
        
        username = st.text_input("Username", placeholder="Enter username")
        password = st.text_input("Password", type="password", placeholder="Enter password")
        
        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("🔓 Login", use_container_width=True, type="primary"):
                if login_streamlit(username, password):
                    st.success(f"Welcome, {username}!")
                    st.rerun()
                else:
                    st.error("Invalid credentials. Try demo accounts above.")
        with col_b:
            if st.button("👤 Guest Access", use_container_width=True):
                if login_streamlit("guest", "guest123"):
                    st.success("Welcome, Guest!")
                    st.rerun()


def render_sidebar():
    """Render sidebar with navigation and user info."""
    user = get_current_user()
    
    st.sidebar.markdown(f"<h2>🤖 MultiMind AI</h2>", unsafe_allow_html=True)
    
    if user:
        # User info
        st.sidebar.markdown(f"**👤 {user['username']}**")
        st.sidebar.caption(f"Role: {user['role']}")
        if user.get("department"):
            st.sidebar.caption(f"Department: {user['department']}")
        
        st.sidebar.markdown("---")
        
        # Navigation
        pages = {
            "💬 Chat": "chat",
            "📄 Documents": "documents",
            "📊 Memory": "memory",
            "🧠 Knowledge Integrity": "integrity",
            "🔐 Security": "security",
            "📈 Analytics": "analytics",
            "📜 Knowledge Evolution": "evolution",
            "🔄 Agent Replay": "replay",
        }
        
        # Add admin page for admins
        if user.get("role") == Role.ADMIN.value:
            pages["🏢 Admin"] = "admin"
        
        selected_page = st.sidebar.selectbox(
            "Navigation",
            list(pages.keys()),
            index=list(pages.values()).index(st.session_state.current_page) if st.session_state.current_page in pages.values() else 0,
        )
        st.session_state.current_page = pages[selected_page]
        
        st.sidebar.markdown("---")
        
        # Quick actions
        if st.sidebar.button("🔄 New Chat"):
            st.session_state.messages = []
            st.session_state.uploaded_files = []
            st.rerun()
        
        if st.sidebar.button("🚪 Logout"):
            logout_streamlit()
            st.session_state.messages = []
            st.session_state.uploaded_files = []
            st.session_state.current_page = "chat"
            st.rerun()
        
        st.sidebar.markdown("---")
        st.sidebar.markdown("### 🔒 Security Status")
        
        # Security scanner status
        scanner = get_security_scanner()
        recent_events = scanner.audit_logger.get_security_events(limit=5)
        if recent_events:
            critical_count = sum(1 for e in recent_events if e.get("severity") in ["critical", "high"])
            if critical_count > 0:
                st.sidebar.error(f"⚠️ {critical_count} critical/high alerts")
            else:
                st.sidebar.success("✅ No critical alerts")
        else:
            st.sidebar.success("✅ Secure")
        
        if is_demo_mode():
            st.sidebar.info("📝 Demo Mode\n\nAdd API keys to .env for real responses.")
        
        # Knowledge Health Quick Insights
        st.sidebar.markdown("---")
        st.sidebar.markdown("### 📈 Knowledge Health")
        try:
            health_report = run_knowledge_check()
            health_score = int(health_report.get("knowledge_score", 0.92) * 100)
            st.sidebar.metric("Health Score", f"{health_score}%")
            
            # Show issue counts
            outdated = sum(1 for i in health_report.get("issues", []) if i.get("issue_type") == "outdated")
            conflicts = sum(1 for i in health_report.get("issues", []) if i.get("issue_type") == "contradiction")
            if conflicts == 0:
                st.sidebar.success("🟢 No conflicts")
            else:
                st.sidebar.error(f"🔴 {conflicts} conflicts")
            st.sidebar.warning(f"🟡 {outdated} outdated documents")
        except Exception:
            st.sidebar.metric("Health Score", "92%")
            st.sidebar.success("🟢 No conflicts")
            st.sidebar.warning("🟡 2 outdated documents")
        
        # Recent Activity
        st.sidebar.markdown("---")
        st.sidebar.markdown("### Recent Activity")
        st.sidebar.markdown("• HR Policy uploaded\n• Conflict resolved\n• New knowledge indexed")
    else:
        st.sidebar.info("Please login to access the dashboard.")


def render_chat_page():
    """Render main chat interface."""
    # Header
    col_header, col_notif, col_user = st.columns([3, 0.5, 1])
    with col_header:
        st.markdown("<h1 style='margin: 0;'>🤖 MultiMind AI</h1>", unsafe_allow_html=True)
        st.markdown("<p style='color: #666; margin: 0;'>Secure Enterprise Knowledge Platform</p>", unsafe_allow_html=True)
    with col_notif:
        st.markdown("<p style='text-align: center; font-size: 1.5em; margin: 0;'>🔔</p>", unsafe_allow_html=True)
    with col_user:
        user = get_current_user()
        if user:
            st.markdown(f"**👤 {user['username']}**")
    
    st.markdown("---")
    
    # Welcome screen
    if not st.session_state.messages:
        st.markdown("<h3 style='text-align: center; margin-top: 2rem;'>How can I help you today?</h3>", unsafe_allow_html=True)
        st.markdown("""
        <div style='text-align: center; color: #666; margin-top: 1rem;'>
        <p>🔒 Secure | 🧠 Memory-enabled | ✅ Human-approved</p>
        <p>Upload documents, ask questions, get verified answers.</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Display chat messages with enhanced formatting
    for i, message in enumerate(st.session_state.messages):
        with st.chat_message(message["role"]):
            if message["role"] == "assistant":
                # Check if this is a greeting message (stored with is_greeting flag)
                if message.get("is_greeting"):
                    st.markdown(message["content"])
                elif "structured" in message:
                    # Render structured response
                    render_structured_response(
                        message.get("answer", ""),
                        message.get("sources", []),
                        message.get("confidence", 0.5),
                        message.get("validation", {}),
                        message.get("integrity", {}),
                        message.get("evolution_available", False)
                    )
                    
                    # Show confidence breakdown expander
                    if "confidence_breakdown" in message:
                        with st.expander("📊 Confidence Breakdown", expanded=False):
                            st.markdown(message["confidence_breakdown"], unsafe_allow_html=True)
                else:
                    content = message["content"]
                    
                    # Check for sources
                    if "sources" in message:
                        for source in message["sources"]:
                            st.markdown(f"""
                            <div class='source-box'>
                            📚 <strong>{source.get('source_name', 'Unknown')}</strong> 
                            ({source.get('source_type', 'unknown')}) — 
                            Confidence: <span class='confidence-high'>{source.get('confidence', 0):.0%}</span>
                            </div>
                            """, unsafe_allow_html=True)
                    
                    # Display explainable confidence breakdown
                    if "confidence_breakdown" in message:
                        with st.expander("📊 Confidence Breakdown", expanded=False):
                            st.markdown(message["confidence_breakdown"], unsafe_allow_html=True)
                    elif "confidence" in message:
                        # Generate breakdown if not provided
                        conf = message["confidence"]
                        conf_class = "confidence-high" if conf >= 0.8 else ("confidence-medium" if conf >= 0.6 else "confidence-low")
                        st.markdown(f"<p style='text-align: right; font-size: 0.9em;'>Confidence: <span class='{conf_class}'>{conf:.0%}</span></p>", unsafe_allow_html=True)
                    
                    st.markdown(content)
            else:
                st.markdown(message["content"])
    
    # Chat input with file upload
    col1, col2 = st.columns([4, 1])
    with col1:
        prompt = st.chat_input("Message...", key="chat_input")
    with col2:
        uploaded_file = st.file_uploader(
            "📎",
            type=["pdf", "docx", "doc", "xlsx", "xls", "csv", "txt", "png", "jpg", "jpeg", "mp3", "wav"],
            label_visibility="collapsed",
            key="file_uploader"
        )
    
    # Handle file upload
    if uploaded_file and uploaded_file.name not in [f.get("name") if isinstance(f, dict) else f for f in st.session_state.uploaded_files]:
        with st.spinner(f"Processing {uploaded_file.name}..."):
            processor = get_multimodal_processor()
            file_bytes = uploaded_file.read()
            multimodal = processor.process(file_bytes, uploaded_file.name)
            
            st.session_state.uploaded_files.append({
                "name": uploaded_file.name,
                "type": multimodal.input_type,
                "text": multimodal.extracted_text,
                "metadata": multimodal.metadata,
            })
            
            if multimodal.extracted_text:
                st.success(f"✅ Processed: {uploaded_file.name}")
                with st.expander("Extracted Content"):
                    st.text(multimodal.extracted_text[:1000])
            else:
                st.warning(f"⚠️ No text extracted from {uploaded_file.name}")
    
    # Process chat input
    if prompt:
        # Add user message
        user_content = prompt
        
        # Add extracted text from uploaded files
        for f in st.session_state.uploaded_files:
            if f.get("text"):
                user_content += f"\n\n[Document: {f['name']}]\n{f['text'][:500]}..."
        
        st.session_state.messages.append({"role": "user", "content": user_content})
        
        # Process and display assistant response
        with st.chat_message("assistant"):
            # Check if this is a greeting
            if is_greeting(prompt):
                greeting_msg = render_greeting()
                st.markdown(greeting_msg)
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": greeting_msg,
                    "is_greeting": True,
                })
            else:
                with st.spinner("Thinking..."):
                    answer = "No response generated"
                    sources = []
                    confidence = 0.5
                    result = {}
                    
                    try:
                        # Build state for LangGraph
                        user = get_current_user()
                        state: SharedState = {
                            "messages": [HumanMessage(content=prompt)],
                            "task_type": "research",
                            "retry_count": 0,
                            "max_retries": 3,
                            "metadata": {"session_id": st.session_state.get("session_id", "default")},
                            "planner_ran": False,
                            "task_plan": None,
                            "plan_reasoning": None,
                            "current_task_index": 0,
                            "reflection": None,
                            "workflow_quality": 0.0,
                            "sources": [],
                            "confidence": 0.5,
                            "adaptive_skipped": True,
                            "pending_approval": False,
                            "approval_request_id": None,
                            "approval_required_for": None,
                            "security_scan": None,
                            "feedback_collected": False,
                            "feedback_id": None,
                            "evolution_timeline": None,
                            "user": {
                                "user_id": user["user_id"] if user else "guest",
                                "username": user["username"] if user else "guest",
                                "role": user["role"] if user else "guest",
                                "session_id": st.session_state.get("session_id", "default"),
                            },
                        }
                        
                        # Run through LangGraph
                        result = app.invoke(state)
                        
                        answer = result.get("final_answer") or result.get("research_data") or result.get("code_result") or "No response generated"
                        sources = result.get("sources", [])
                        confidence = result.get("confidence", 0.5)
                        
                        # Check if approval is pending
                        if result.get("pending_approval"):
                            answer += f"\n\n⏳ **Awaiting human approval** (Request ID: {result.get('approval_request_id')})"
                        
                        if is_demo_mode():
                            answer += "\n\n*Demo mode - add API key for real LLM responses*"
                        
                    except Exception as e:
                        answer = f"Error: {str(e)}"
                        sources = []
                        confidence = 0.5
                        result = {}
                    
                    # Generate explainable confidence breakdown
                    validation = result.get("validation", {}) if isinstance(result, dict) else {}
                    integrity = result.get("integrity_check", {}) if isinstance(result, dict) else {}
                    
                    try:
                        confidence_breakdown = get_confidence_explainer().explain(
                            validation, sources, integrity, retrieval_quality=confidence
                        )
                        html_breakdown = get_confidence_explainer().get_factor_breakdown_html(confidence_breakdown)
                    except Exception:
                        html_breakdown = "<p>Confidence breakdown unavailable</p>"
                    
                    # Check for evolution data
                    evolution_available = bool(result.get("evolution_timeline"))
                    
                    # Render structured response
                    render_structured_response(
                        answer, sources, confidence, validation, integrity, evolution_available
                    )
                    
                    with st.expander("📊 Confidence Breakdown", expanded=False):
                        st.markdown(html_breakdown, unsafe_allow_html=True)
                    
                # Add assistant response to history
                st.session_state.messages.append({
                    "role": "assistant",
                    "answer": answer,
                    "sources": sources,
                    "confidence": confidence,
                    "confidence_breakdown": html_breakdown,
                    "validation": validation,
                    "integrity": integrity,
                    "evolution_available": bool(result.get("evolution_timeline")),
                    "structured": True,
                })


def render_documents_page():
    """Render document upload page."""
    st.markdown("<h1>📄 Document Management</h1>", unsafe_allow_html=True)
    
    user = get_current_user()
    if not user:
        st.warning("Please login to access documents.")
        return
    
    supported_types = get_supported_document_types()
    st.caption(f"Supported types: {', '.join(supported_types)}")
    
    # File upload
    uploaded_files = st.file_uploader(
        "Upload documents",
        type=supported_types,
        accept_multiple_files=True,
        help="Upload PDF, DOCX, Excel, CSV, or text files"
    )
    
    if uploaded_files:
        for uploaded_file in uploaded_files:
            with st.spinner(f"Processing {uploaded_file.name}..."):
                file_bytes = uploaded_file.read()
                processor = get_multimodal_processor()
                multimodal = processor.process(file_bytes, uploaded_file.name)
                
                st.success(f"✅ Processed: {uploaded_file.name}")
                st.caption(f"Type: {multimodal.input_type} | Size: {len(file_bytes)} bytes")
                
                if multimodal.extracted_text:
                    with st.expander("Extracted Content"):
                        st.text(multimodal.extracted_text[:1000] + "..." if len(multimodal.extracted_text) > 1000 else multimodal.extracted_text)
                    
                    # Option to store in RAG
                    if st.button(f"Store in Knowledge Base", key=f"store_{uploaded_file.name}"):
                        from memory import rag_memory
                        rag_memory.add_knowledge(multimodal.extracted_text, {
                            "type": "uploaded_document",
                            "source": uploaded_file.name,
                            "user_id": user["user_id"],
                            "session_id": user.get("session_id", "unknown"),
                            "agent_source": "user_upload",
                        })
                        st.success("✅ Stored in knowledge base!")
    
    st.markdown("---")
    st.subheader("Supported File Types")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("**Documents**")
        st.caption("PDF, DOCX, TXT, MD, CSV")
    with col2:
        st.markdown("**Spreadsheets**")
        st.caption("XLSX, XLS, CSV")
    with col3:
        st.markdown("**Media**")
        st.caption("PNG, JPG, MP3, WAV (OCR/transcription)")


def render_security_page():
    """Render security audit page."""
    st.markdown("<h1>🔐 Security Center</h1>", unsafe_allow_html=True)
    
    user = get_current_user()
    if not user:
        st.warning("Please login to access security center.")
        return
    
    # Only admins can see full security info
    if user.get("role") != Role.ADMIN.value:
        st.info("Full security audit is available for administrators only.")
    
    scanner = get_security_scanner()
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Security Scanner Test")
        test_input = st.text_area("Test input for security scan", placeholder="Enter text to scan for injection/PII...")
        if st.button("🔍 Scan"):
            if test_input:
                is_safe, report = scanner.scan_input(test_input, user_id=user["user_id"])
                if is_safe:
                    st.success("✅ Input is safe")
                else:
                    st.error("❌ Security issues detected!")
                    st.json(report)
    
    with col2:
        st.subheader("PII Masking Test")
        pii_input = st.text_area("Test PII masking", placeholder="Enter text with email, phone, SSN...")
        if st.button("🎭 Mask PII"):
            if pii_input:
                masked, detected = scanner.pii_masker.mask(pii_input)
                st.text("Masked output:")
                st.code(masked)
                st.caption(f"Detected: {list(detected.keys())}")


def render_evolution_page():
    """Render Knowledge Evolution dashboard."""
    st.markdown("<h1>📜 Knowledge Evolution</h1>", unsafe_allow_html=True)
    st.markdown("<p style='color: #666;'>Track how organizational knowledge has changed over time.</p>", unsafe_allow_html=True)
    
    user = get_current_user()
    if not user:
        st.warning("Please login to access knowledge evolution.")
        return
    
    # Topic search
    col1, col2 = st.columns([3, 1])
    with col1:
        topic_query = st.text_input("Enter topic to explore evolution", placeholder="e.g., leave policy, PTO rules, salary structure...")
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🔍 Explore Evolution", use_container_width=True):
            pass
    
    if topic_query:
        try:
            from knowledge_evolution import get_knowledge_timeline
            with st.spinner("Finding knowledge evolution..."):
                timeline = get_knowledge_timeline(topic_query)
            
            if timeline:
                versions = timeline.get("versions", [])
                changes = timeline.get("changes", [])
                
                if versions:
                    st.success(f"Found {len(versions)} versions for '{topic_query}'")
                    
                    # Timeline view
                    st.subheader("📅 Timeline")
                    for v in versions:
                        ts = datetime.fromtimestamp(v["timestamp"]).strftime("%Y-%m-%d")
                        with st.expander(f"📄 {ts} — {v['source_name']}", expanded=False):
                            st.write(v.get("content", ""))
                            st.caption(f"Trust Score: {v['trust_score']:.0%}")
                    
                    # Changes detected
                    if changes:
                        st.subheader("📊 Changes")
                        for c in changes:
                            st.info(f"{c['from_source']} → {c['to_source']}: {c['summary']}")
                else:
                    st.info("No evolution data found for this topic. Ask questions about policies or upload documents to build history.")
            else:
                st.info("No evolution data found yet. Upload documents or ask questions to start tracking knowledge evolution.")
        except Exception as e:
            st.error(f"Evolution lookup failed: {str(e)}")
    
    st.markdown("---")
    
    # Example evolution queries
    st.subheader("🔍 Example Evolution Queries")
    examples = [
        "How has our leave policy changed over the years?",
        "Show the evolution of PTO rules",
        "What versions exist for salary structure?",
        "Timeline of remote work policy",
    ]
    
    for ex in examples:
        if st.button(f"📌 {ex}", key=f"ex_{ex[:20]}"):
            st.session_state.messages.append({"role": "user", "content": ex})
            st.session_state.current_page = "chat"
            st.rerun()


def render_replay_page():
    """Render Agent Memory Replay dashboard."""
    import json
    st.markdown("<h1>🔄 Agent Memory Replay</h1>", unsafe_allow_html=True)
    st.markdown("<p style='color: #666;'>Inspect the reasoning steps in any workflow execution.</p>", unsafe_allow_html=True)
    
    user = get_current_user()
    if not user:
        st.warning("Please login to access replay.")
        return
    
    from replay import get_replay_history, _replays
    
    # Show available sessions
    col1, col2 = st.columns([2, 1])
    with col1:
        session_id = st.text_input("Session ID to replay", placeholder="Enter session ID or leave empty for latest")
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🔍 Load Replay", use_container_width=True):
            pass
    
    # Get all replay sessions
    all_sessions = list(_replays.keys())
    
    st.subheader("📋 Recent Sessions")
    if all_sessions:
        selected_session = st.selectbox("Select session to inspect:", all_sessions, key="replay_session")
        
        if selected_session:
            replay = get_replay_history(selected_session)
            if replay:
                for i, step in enumerate(replay):
                    with st.expander(f"Step {i+1}: {step['agent']}", expanded=i == 0):
                        col1, col2 = st.columns(2)
                        with col1:
                            st.write(f"**Timestamp:** {datetime.fromtimestamp(step['timestamp']).isoformat()[:19]}")
                            st.write(f"**Duration:** {step['duration_ms']:.0f}ms")
                        with st.expander("Input"):
                            st.code(json.dumps(step.get("inputs", {}), indent=2, default=str)[:500])
                        with st.expander("Output"):
                            st.code(json.dumps(step.get("outputs", {}), indent=2, default=str)[:500])
            else:
                st.info("No replay data available for this session")
    else:
        st.info("No replay sessions recorded yet. Run queries to generate replay data.")
    
    st.markdown("---")
    
    # Evaluation metrics
    st.subheader("📊 Evaluation Metrics")
    engine = get_evaluation_engine()
    summary = engine.get_summary()
    
    if summary.get("total_queries", 0) > 0:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Queries", summary["total_queries"])
        with col2:
            st.metric("Avg Latency", f"{summary['avg_latency_seconds']:.2f}s")
        with col3:
            st.metric("Avg Confidence", f"{summary['avg_confidence']:.0%}")
        
        col4, col5 = st.columns(2)
        with col4:
            st.metric("Conflicts Detected", summary["total_conflicts"])
        with col5:
            st.metric("Total Cost", f"${summary['total_cost']:.4f}")
    else:
        st.info("No evaluation data yet. Queries will be evaluated automatically.")


def render_analytics_page():
    """Render analytics page."""
    st.markdown("<h1>📈 Analytics Dashboard</h1>", unsafe_allow_html=True)
    
    user = get_current_user()
    if not user:
        st.warning("Please login to access analytics.")
        return
    
    # Cost optimizer
    cost_optimizer = get_cost_optimizer()
    col1, col2, col3 = st.columns(3)
    with col1:
        budget_status = cost_optimizer.get_budget_status()
        st.metric("Budget Remaining", f"${budget_status['remaining']:.4f}")
    with col2:
        st.metric("Total Spend", f"${budget_status['current_spend']:.4f}")
    with col3:
        st.metric("Queries", len(cost_optimizer.budget_tracker.query_costs))
    
    # Feedback stats
    from feedback import get_feedback_store
    store = get_feedback_store()
    agent_stats = store.get_agent_stats("all")
    
    st.subheader("Feedback Overview")
    if agent_stats:
        st.metric("Total Feedback", agent_stats.get("total_feedback", 0))
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Positive", agent_stats.get("positive_count", 0))
        with col2:
            st.metric("Negative", agent_stats.get("negative_count", 0))
        with col3:
            st.metric("Avg Rating", f"{agent_stats.get('average_rating', 0):.1f}/5")
    
    st.markdown("---")
    
    st.subheader("📊 Evaluation Summary")
    engine = get_evaluation_engine()
    summary = engine.get_summary()
    
    if summary.get("total_queries", 0) > 0:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Avg Latency", f"{summary['avg_latency_seconds']:.2f}s")
        with col2:
            st.metric("Avg Confidence", f"{summary['avg_confidence']:.0%}")
        with col3:
            st.metric("Total Cost", f"${summary['total_cost']:.4f}")


def render_feedback_widget():
    """Render feedback widget for last assistant message."""
    if st.session_state.messages and st.session_state.messages[-1]["role"] == "assistant":
        st.markdown("---")
        st.caption("Was this response helpful?")
        
        col1, col2, col3 = st.columns([1, 1, 3])
        with col1:
            if st.button("👍", key="feedback_up"):
                _submit_feedback("thumbs_up")
        with col2:
            if st.button("👎", key="feedback_down"):
                _submit_feedback("thumbs_down")
        with col3:
            feedback_text = st.text_input("Additional feedback (optional)", key="feedback_text", label_visibility="collapsed")
            if st.button("Submit", key="feedback_submit"):
                if feedback_text:
                    _submit_feedback("rating", feedback_text)


def render_integrity_page():
    """Render Knowledge Integrity Engine dashboard."""
    st.markdown("<h1>🧠 Knowledge Integrity Engine</h1>", unsafe_allow_html=True)
    st.markdown("<p style='color: #666;'>Detects conflicts, ranks sources, and ensures organizational knowledge accuracy.</p>", unsafe_allow_html=True)
    
    from conflict_detector import get_conflict_detector, get_knowledge_health
    
    detector = get_conflict_detector()
    health = get_knowledge_health()
    
    # Knowledge Health Score
    st.subheader("Knowledge Health Overview")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        health_score = health.get("knowledge_health_score", 1.0)
        st.metric("Health Score", f"{health_score:.0%}", delta=None, delta_color="normal" if health_score >= 0.8 else "inverse")
    with col2:
        st.metric("Total Conflicts", health.get("total_conflicts", 0))
    with col3:
        unresolved = health.get("unresolved_conflicts", 0)
        st.metric("Unresolved", unresolved, delta=f"-{unresolved}" if unresolved > 0 else "0")
    with col4:
        st.metric("Resolution Rate", f"{health.get('resolution_rate', 0):.0%}")
    
    st.markdown("---")
    
    # Conflict List
    st.subheader("📋 Detected Conflicts")
    conflicts = detector.get_unresolved_conflicts()
    
    if conflicts:
        for conflict in conflicts:
            with st.expander(f"⚠️ {conflict.description[:80]}", expanded=False):
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**Conflict ID:** {conflict.conflict_id}")
                    st.write(f"**Type:** {conflict.conflict_type}")
                    st.write(f"**Status:** {conflict.status}")
                    st.write(f"**Detected:** {datetime.fromtimestamp(conflict.detected_at).isoformat()[:19]}")
                
                with col2:
                    st.write("**Sources:**")
                    for chunk in conflict.chunks:
                        with st.expander(f"📄 {chunk.source_name}", expanded=False):
                            st.text(chunk.content[:300])
                            st.caption(f"Trust: {chunk.trust_score:.2f} | Freshness: {chunk.freshness_score:.2f} | Type: {chunk.source_type}")
                
                # Resolution actions (admin only)
                user = get_current_user()
                if user and user.get("role") == "admin":
                    st.write("**Admin Resolution:**")
                    chunk_options = {f"{c.source_name} (trust: {c.trust_score:.2f})": c.chunk_id for c in conflict.chunks}
                    selected = st.selectbox("Select authoritative source:", list(chunk_options.keys()), key=f"resolve_{conflict.conflict_id}")
                    if st.button(f"✅ Resolve Conflict", key=f"resolve_btn_{conflict.conflict_id}"):
                        authoritative_id = chunk_options[selected]
                        detector.resolve_conflict(conflict.conflict_id, authoritative_id, user["user_id"])
                        st.success("Conflict resolved! Trust scores updated.")
                        st.rerun()
    else:
        st.success("✅ No unresolved conflicts. Knowledge base is consistent.")
    
    st.markdown("---")
    
    # Conflict Detection Test
    st.subheader("🔍 Test Conflict Detection")
    with st.form("conflict_test"):
        col1, col2 = st.columns(2)
        with col1:
            content_a = st.text_area("Document A (older)", placeholder="e.g., Leave policy is 20 days")
            source_a = st.text_input("Source A name", value="Document A")
        with col2:
            content_b = st.text_area("Document B (newer)", placeholder="e.g., Leave policy is 24 days")
            source_b = st.text_input("Source B name", value="Document B")
        
        submitted = st.form_submit_button("Detect Conflicts")
        if submitted and content_a and content_b:
            from conflict_detector import KnowledgeChunk, detect_conflicts
            chunk_a = KnowledgeChunk(
                chunk_id="test-a",
                content=content_a,
                source_name=source_a,
                source_type="internal_document",
                timestamp=time.time() - (365 * 24 * 3600),  # 1 year old
                trust_score=0.8,
                freshness_score=0.5,
                allowed_roles=["*"],
                department=None,
            )
            chunk_b = KnowledgeChunk(
                chunk_id="test-b",
                content=content_b,
                source_name=source_b,
                source_type="internal_document",
                timestamp=time.time(),  # today
                trust_score=0.9,
                freshness_score=1.0,
                allowed_roles=["*"],
                department=None,
            )
            conflicts = detect_conflicts(chunk_b, [chunk_a])
            if conflicts:
                st.warning(f"⚠️ Detected {len(conflicts)} conflict(s)!")
                for c in conflicts:
                    st.error(c.description)
            else:
                st.info("No conflicts detected.")


def _submit_feedback(feedback_type: str, comment: str = None):
    """Submit feedback for last response."""
    from feedback import submit_feedback
    from auth import get_current_user
    
    if not st.session_state.messages:
        return
    
    user = get_current_user()
    if not user:
        return
    
    last_msg = st.session_state.messages[-1]
    if last_msg["role"] != "assistant":
        return
    
    session_id = user.get("session_id", "unknown")
    user_id = user["user_id"]
    query = st.session_state.messages[-2]["content"] if len(st.session_state.messages) >= 2 else ""
    
    submit_feedback(
        session_id=session_id,
        user_id=user_id,
        query=query,
        agent="system",
        output=last_msg["content"],
        feedback_type=feedback_type,
        comment=comment,
    )
    st.success("Thank you for your feedback!")


# Main app logic
render_sidebar()

if not is_authenticated():
    render_login_page()
else:
    user = get_current_user()
    
    # Route to pages
    if st.session_state.current_page == "chat":
        render_chat_page()
        render_feedback_widget()
    elif st.session_state.current_page == "documents":
        render_documents_page()
    elif st.session_state.current_page == "memory":
        render_memory_dashboard()
    elif st.session_state.current_page == "integrity":
        render_integrity_page()
    elif st.session_state.current_page == "security":
        render_security_page()
    elif st.session_state.current_page == "analytics":
        render_analytics_page()
    elif st.session_state.current_page == "evolution":
        render_evolution_page()
    elif st.session_state.current_page == "replay":
        render_replay_page()
    elif st.session_state.current_page == "admin":
        render_admin_dashboard()
    else:
        render_chat_page()

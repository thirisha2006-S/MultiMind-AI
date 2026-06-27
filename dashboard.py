"""
MultiMind AI - ChatGPT-Style Chat Interface
Clean, minimalistic chat interface like ChatGPT
"""

import os
import streamlit as st
from datetime import datetime

from auth import (
    get_auth_manager, is_authenticated, get_current_user,
    login_streamlit, logout_streamlit
)
from rbac import get_rbac_manager, Role
from security import get_security_scanner, mask_pii
from llm_utils import is_demo_mode
from multimodal import get_multimodal_processor
from parsers import parse_document, get_supported_document_types
from confidence_explainer import get_confidence_explainer
from knowledge_doctor import run_knowledge_check
from intent_classifier import classify_intent, Intent
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
    page_title="MultiMind AI",
    page_icon="🤖",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Initialize session state
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "user" not in st.session_state:
    st.session_state.user = None
if "messages" not in st.session_state:
    st.session_state.messages = []
if "uploaded_files" not in st.session_state:
    st.session_state.uploaded_files = []

# ChatGPT-style CSS
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    * {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    .stApp {
        background-color: #FFFFFF;
    }
    
    .chat-container {
        max-width: 768px;
        margin: 0 auto;
        padding: 20px;
    }
    
    .chat-message-user {
        background-color: #F7F7F8;
        border-radius: 18px;
        padding: 12px 16px;
        margin: 8px 0;
        margin-left: auto;
        max-width: 85%;
    }
    
    .chat-message-assistant {
        background-color: #FFFFFF;
        border: 1px solid #E5E5E5;
        border-radius: 18px;
        padding: 12px 16px;
        margin: 8px 0;
        max-width: 85%;
        box-shadow: 0 1px 2px rgba(0,0,0,0.03);
    }
    
    .chat-input-container {
        position: fixed;
        bottom: 0;
        left: 0;
        right: 0;
        background: #FFFFFF;
        padding: 20px;
        border-top: 1px solid #E5E5E5;
        z-index: 100;
    }
    
    .main-header {
        text-align: center;
        padding: 20px 0;
        border-bottom: 1px solid #E5E5E5;
        margin-bottom: 20px;
    }
    
    .welcome-message {
        text-align: center;
        padding: 60px 20px;
        color: #666;
    }
    
    .example-question {
        background: #F7F7F8;
        border: 1px solid #E5E5E5;
        border-radius: 12px;
        padding: 8px 12px;
        margin: 5px;
        font-size: 14px;
        cursor: pointer;
    }
    
    .confidence-pill {
        display: inline-block;
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 11px;
        font-weight: 500;
        margin-top: 8px;
    }
    
    .confidence-high { background: #DCFCE7; color: #166534; }
    .confidence-medium { background: #FEF3C7; color: #92400E; }
    .confidence-low { background: #FEE2E2; color: #991B1B; }
</style>
""", unsafe_allow_html=True)


def render_chat_message(content, is_user=False, confidence=None):
    """Render a chat message in ChatGPT style."""
    if is_user:
        st.markdown(f'<div class="chat-message-user">{content}</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="chat-message-assistant">{content}</div>', unsafe_allow_html=True)
        # Only show confidence for actual answers, not greetings/clarifications
        if confidence is not None:
            conf_pct = int(confidence * 100)
            conf_class = "confidence-high" if confidence >= 0.8 else ("confidence-medium" if confidence >= 0.6 else "confidence-low")
            st.markdown(f'<span class="confidence-pill {conf_class}">Confidence: {conf_pct}%</span>', unsafe_allow_html=True)


def render_login_page():
    """Render login page in ChatGPT style."""
    st.markdown("""
    <div class="main-header">
        <h1 style="margin: 0; font-size: 28px;">🤖 MultiMind AI</h1>
        <p style="margin: 5px 0 0 0; color: #666; font-size: 14px;">Secure Enterprise Knowledge Assistant</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.text_input("Username", placeholder="Enter username", key="login_username")
        st.text_input("Password", type="password", placeholder="Enter password", key="login_password")
        
        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("Sign in", use_container_width=True):
                if login_streamlit(st.session_state.login_username, st.session_state.login_password):
                    st.rerun()
        with col_b:
            if st.button("Guest Access", use_container_width=True):
                if login_streamlit("guest", "guest123"):
                    st.rerun()
        
        st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)
        st.info("Demo: admin/admin123 or guest/guest123")


def render_chat_page():
    """Render main chat interface."""
    st.markdown("""
    <div class="main-header" style="padding: 10px 0; margin-bottom: 10px;">
        <h2 style="margin: 0; font-size: 22px;">🤖 MultiMind AI</h2>
    </div>
    """, unsafe_allow_html=True)
    
    # Welcome message
    if not st.session_state.messages:
        st.markdown("""
        <div class="welcome-message">
            <h3 style="margin-bottom: 20px;">How can I help you today?</h3>
            <p style="color: #888; margin-bottom: 30px;">Ask about policies, upload documents, or check knowledge health</p>
            <div style="display: flex; flex-wrap: wrap; justify-content: center; gap: 10px;">
        """, unsafe_allow_html=True)
        
        examples = [
            "What is our leave policy?",
            "Show knowledge health report",
            "Upload a document",
            "How has PTO changed?"
        ]
        for ex in examples:
            if st.button(ex, key=f"ex_{ex[:20]}"):
                st.session_state.messages.append({"role": "user", "content": ex})
        
        st.markdown("</div></div>", unsafe_allow_html=True)
    
    # Display messages
    for message in st.session_state.messages:
        render_chat_message(
            message["content"],
            is_user=message["role"] == "user",
            confidence=message.get("confidence")
        )
    
    # Chat input at bottom
    st.markdown('<div style="height: 100px;"></div>', unsafe_allow_html=True)
    
    # Process input
    if prompt := st.chat_input("Message MultiMind AI..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        with st.spinner("Thinking..."):
            intent, _ = classify_intent(prompt)
            
            user = get_current_user()
            task_type = "research"
            if intent == Intent.CODING_QUERY:
                task_type = "coding"
            
            try:
                state: SharedState = {
                    "messages": [HumanMessage(content=prompt)],
                    "task_type": task_type,
                    "retry_count": 0,
                    "max_retries": 3,
                    "metadata": {"session_id": "default"},
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
                        "session_id": "default",
                    },
                }
                result = app.invoke(state)
                answer = result.get("final_answer") or result.get("code_result") or "No response generated"
                confidence = result.get("confidence", 0.5)
                
                # No confidence shown for conversational replies
                if intent == Intent.CONVERSATION:
                    confidence = None
                    
                if is_demo_mode() and intent != Intent.CONVERSATION:
                    answer += "\n\n* — Demo mode*"
            except Exception as e:
                answer = f"Error: {str(e)}"
                confidence = 0.5
        
        st.session_state.messages.append({
            "role": "assistant",
            "content": answer,
            "confidence": confidence,
        })
        st.rerun()


def render_documents_page():
    """Render document upload in chat style."""
    st.markdown("""
    <div class="main-header">
        <h2 style="margin: 0; font-size: 22px;">📄 Document Upload</h2>
    </div>
    """, unsafe_allow_html=True)
    
    user = get_current_user()
    if not user:
        st.warning("Please sign in to upload documents.")
        return
    
    uploaded_files = st.file_uploader(
        "Upload documents",
        type=["pdf", "docx", "txt", "csv"],
        accept_multiple_files=True,
        label_visibility="collapsed"
    )
    
    if uploaded_files:
        for f in uploaded_files:
            with st.spinner(f"Processing {f.name}..."):
                processor = get_multimodal_processor()
                multimodal = processor.process(f.read(), f.name)
                if multimodal.extracted_text:
                    st.success(f"✅ {f.name} processed")


# Main app logic
if not is_authenticated():
    render_login_page()
else:
    # Simple navigation
    page = st.sidebar.selectbox(
        "Menu",
        ["Chat", "Documents", "Knowledge Health"],
        key="main_menu"
    )
    
    if page == "Chat":
        render_chat_page()
    elif page == "Documents":
        render_documents_page()
    elif page == "Knowledge Health":
        st.markdown("""
        <div class="main-header">
            <h2 style="margin: 0; font-size: 22px;">🩺 Knowledge Health</h2>
        </div>
        """, unsafe_allow_html=True)
        with st.spinner("Running health check..."):
            report = run_knowledge_check()
        st.metric("Health Score", f"{int(report.get('knowledge_score', 0.92) * 100)}%")
    
    # Logout in sidebar
    with st.sidebar:
        if st.button("Sign out"):
            logout_streamlit()
            st.rerun()
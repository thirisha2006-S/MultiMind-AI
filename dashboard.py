"""
MultiMind AI - Pure ChatGPT-Style Chat Interface
Simple, natural conversation like ChatGPT
"""

import os
import streamlit as st

from auth import is_authenticated, get_current_user, login_streamlit, logout_streamlit
from llm_utils import is_demo_mode
from intent_classifier import classify_intent, Intent
from graph import app
from state import SharedState
from langchain_core.messages import HumanMessage

# Load secrets from Streamlit Cloud
try:
    if hasattr(st, 'secrets') and st.secrets:
        os.environ.setdefault('COHERE_API_KEY', st.secrets.get('COHERE_API_KEY', ''))
        os.environ.setdefault('OPENAI_API_KEY', st.secrets.get('OPENAI_API_KEY', ''))
except Exception:
    pass

st.set_page_config(page_title="MultiMind AI", page_icon="🤖", layout="centered")

# Initialize session state
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "user" not in st.session_state:
    st.session_state.user = None
if "messages" not in st.session_state:
    st.session_state.messages = []

# Login page if not authenticated
if not is_authenticated():
    st.markdown("# 🤖 MultiMind AI")
    st.markdown("Secure Enterprise Knowledge Assistant")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.button("Sign in"):
            login_streamlit(username, password)
            st.rerun()
    st.stop()

# Chat display
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Chat input
if prompt := st.chat_input("Message MultiMind AI..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.rerun()

# Process the last user message
if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
    last_prompt = st.session_state.messages[-1]["content"]
    with st.spinner("Thinking..."):
        try:
            user = get_current_user()
            intent, _ = classify_intent(last_prompt)
            task_type = "coding" if intent == Intent.CODING_QUERY else "research"
            
            state: SharedState = {
                "messages": [HumanMessage(content=last_prompt)],
                "task_type": task_type,
                "retry_count": 0, "max_retries": 3,
                "metadata": {"session_id": "default"},
                "planner_ran": False, "task_plan": None, "plan_reasoning": None,
                "current_task_index": 0, "reflection": None, "workflow_quality": 0.0,
                "sources": [], "confidence": 0.5, "adaptive_skipped": True,
                "pending_approval": False, "approval_request_id": None,
                "approval_required_for": None, "security_scan": None,
                "feedback_collected": False, "feedback_id": None, "evolution_timeline": None,
                "user": {"user_id": user["user_id"] if user else "guest", "username": user["username"] if user else "guest", "role": user["role"] if user else "guest", "session_id": "default"},
            }
            result = app.invoke(state)
            answer = result.get("final_answer") or result.get("code_result") or "No response generated"
            
            if intent != Intent.CONVERSATION and is_demo_mode():
                answer += "\n\n* — Demo mode*"
                
        except Exception as e:
            answer = f"Error: {str(e)}"
    
    st.session_state.messages[-1] = {"role": "assistant", "content": answer}
    st.rerun()
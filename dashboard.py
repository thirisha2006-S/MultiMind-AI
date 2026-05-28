"""
ChatGPT-style Streamlit Dashboard for MultiMind AI.
Simple chat interface with clean design.
"""

import streamlit as st
import time
from main import run_task
from llm_utils import is_demo_mode

# Page configuration
st.set_page_config(
    page_title="MultiMind AI",
    page_icon="🤖",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Minimal CSS
st.markdown("""
<style>
    .chat-message {
        padding: 1rem;
        margin: 0.5rem 0;
        border-radius: 10px;
    }
    .user-message {
        background-color: #e3f2fd;
        margin-left: 2rem;
    }
    .ai-message {
        background-color: #f5f5f5;
        margin-right: 2rem;
    }
    .stButton>button {
        border-radius: 20px;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state for chat history
if 'messages' not in st.session_state:
    st.session_state.messages = []

if 'current_result' not in st.session_state:
    st.session_state.current_result = None

# Simple header
st.markdown("<h1 style='text-align: center; margin-bottom: 0;'>🤖 MultiMind AI</h1>", unsafe_allow_html=True)
if is_demo_mode():
    st.markdown("<p style='text-align: center; color: #888; font-size: 0.9rem;'>Demo Mode - Add API key in .env for real responses</p>", unsafe_allow_html=True)

st.markdown("---")

# Display chat history
for msg in st.session_state.messages:
    if msg['role'] == 'user':
        st.markdown(f"<div class='chat-message user-message'><strong>You:</strong> {msg['content']}</div>", unsafe_allow_html=True)
    else:
        st.markdown(f"<div class='chat-message ai-message'><strong>AI:</strong><br>{msg['content']}</div>", unsafe_allow_html=True)

# Handle new input
if 'current_result' in st.session_state and st.session_state.current_result:
    # Display the latest result
    result = st.session_state.current_result['result']
    answer = result.get('final_answer') or result.get('research_data') or 'No answer generated'
    
    # Show answer in chat
    st.markdown(f"<div class='chat-message ai-message'><strong>AI:</strong><br>{answer}</div>", unsafe_allow_html=True)
    
    # Clear result after displaying
    st.session_state.current_result = None

# Input area at bottom - ChatGPT style
with st.form(key="chat_form", clear_on_submit=True):
    col1, col2 = st.columns([5, 1])
    with col1:
        task_input = st.text_input(
            "",
            placeholder="Type your message here...",
            key="input_field",
            label_visibility="collapsed"
        )
    with col2:
        submitted = st.form_submit_button("Send", type="primary")

# Process on submit
if submitted and task_input.strip():
    # Add user message to chat
    st.session_state.messages.append({'role': 'user', 'content': task_input})
    
    # Process with AI
    with st.spinner("Thinking..."):
        try:
            result, session_id, tracer = run_task(task_input, "research")
            tracer.finalize(result)
            st.session_state.current_result = {'result': result}
        except Exception as e:
            st.session_state.current_result = {'result': {'final_answer': f"Error: {str(e)}"}}
    
    st.rerun()

# Clear chat button
if st.session_state.messages:
    if st.button("Clear conversation", type="secondary"):
        st.session_state.messages = []
        st.session_state.current_result = None
        st.rerun()
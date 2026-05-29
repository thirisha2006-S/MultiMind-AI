"""
ChatGPT-style Streamlit Dashboard for MultiMind AI.
Simple, clean chat interface using Streamlit components with broad compatibility.
"""

import os
import streamlit as st
from llm_utils import is_demo_mode, chat_coding_mode, chat_research_mode

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
    layout="centered"
)

# Sidebar
st.sidebar.markdown("<h2>🤖 MultiMind AI</h2>", unsafe_allow_html=True)

# Mode selection using compatibility-safe approach
if "mode" not in st.session_state:
    st.session_state.mode = "Coding"

st.session_state.mode = st.sidebar.selectbox(
    "Mode",
    ["Coding", "Research"],
    index=0,
    key="mode_select",
    help="Coding: Direct LLM answers | Research: Web search enabled"
)

if st.sidebar.button("New Chat"):
    st.session_state.messages = []
    st.session_state.mode = "Coding"
    st.rerun()

st.sidebar.markdown("---")
if is_demo_mode():
    st.sidebar.info("Demo Mode - Add COHERE_API_KEY or OPENAI_API_KEY to .env for real responses")
st.sidebar.markdown("---")
st.sidebar.markdown("Your conversations will appear here")

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Welcome screen
if not st.session_state.messages:
    st.markdown("<h1 style='text-align: center; margin-top: 2rem;'>🤖 MultiMind AI</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #666;'>How can I help you today?</p>", unsafe_allow_html=True)

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Chat input
if prompt := st.chat_input("Message..."):
    # Add user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # Process and display assistant response
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            answer = "No response generated"
            try:
                if st.session_state.mode == "Coding":
                    result = chat_coding_mode(prompt)
                    answer = result.get("final_answer") or "No response generated"
                else:
                    result = chat_research_mode(prompt)
                    answer = result.get("final_answer") or "No response generated"
                if is_demo_mode():
                    answer += "\n\n*Demo mode - add API key for real LLM responses*"
            except Exception as e:
                answer = f"Error: {str(e)}"
            st.markdown(answer)
    
    # Add assistant response to history
    st.session_state.messages.append({"role": "assistant", "content": answer})
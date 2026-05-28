"""
Exact ChatGPT-style Streamlit Dashboard for MultiMind AI.
Clean chat interface with sidebar navigation.
"""

import streamlit as st
import time
from main import run_task
from llm_utils import is_demo_mode

# Page configuration
st.set_page_config(
    page_title="MultiMind AI",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ChatGPT-style CSS
st.markdown("""
<style>
    /* Hide default elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .stDeployButton {display: none;}
    
    /* Chat message styling */
    .chat-container {
        max-width: 800px;
        margin: 0 auto;
        padding: 1rem;
    }
    
    .user-bubble {
        background-color: #0066cc;
        color: white;
        padding: 0.8rem 1.2rem;
        border-radius: 18px;
        border-bottom-right-radius: 4px;
        margin: 0.5rem 0;
        margin-left: auto;
        max-width: 70%;
        word-wrap: break-word;
    }
    
    .ai-bubble {
        background-color: #f0f0f0;
        color: #333;
        padding: 0.8rem 1.2rem;
        border-radius: 18px;
        border-bottom-left-radius: 4px;
        margin: 0.5rem 0;
        margin-right: auto;
        max-width: 70%;
        word-wrap: break-word;
    }
    
    .chat-input-container {
        position: fixed;
        bottom: 0;
        left: 0;
        right: 0;
        background: white;
        padding: 1rem;
        border-top: 1px solid #e5e5e5;
        z-index: 1000;
    }
    
    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background-color: #f9f9f9;
    }
    
    /* Model selector styling */
    .model-info {
        font-size: 0.85rem;
        color: #666;
        padding: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.markdown("<h2>🤖 MultiMind AI</h2>", unsafe_allow_html=True)
    
    st.markdown("---")
    
    # New chat button
    if st.button("➕ New conversation", use_container_width=True, type="primary"):
        st.session_state.messages = []
        st.session_state.current_result = None
        st.rerun()
    
    st.markdown("---")
    
    # Model info
    st.markdown("<div class='model-info'>", unsafe_allow_html=True)
    if is_demo_mode():
        st.markdown("**🔧 Demo Mode**")
        st.markdown("Using mock responses. Add `COHERE_API_KEY` to `.env` for real AI.")
    else:
        st.markdown("**✅ Live Mode**")
        st.markdown("Using Cohere/OpenAI API")
    st.markdown("</div>", unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Conversation history placeholder
    st.markdown("<small><strong>Recent Chats</strong></small>", unsafe_allow_html=True)
    st.markdown("<small style='color: #888;'>Your conversations will appear here</small>", unsafe_allow_html=True)

# Initialize session state
if 'messages' not in st.session_state:
    st.session_state.messages = []

# Main chat area
st.markdown("<div class='chat-container'>", unsafe_allow_html=True)

# Display messages
for msg in st.session_state.messages:
    if msg['role'] == 'user':
        st.markdown(f"<div class='user-bubble'>{msg['content']}</div>", unsafe_allow_html=True)
    else:
        st.markdown(f"<div class='ai-bubble'>{msg['content']}</div>", unsafe_allow_html=True)

st.markdown("</div>", unsafe_allow_html=True)

# Input area at bottom
st.markdown("<div class='chat-input-container'>", unsafe_allow_html=True)
col1, col2 = st.columns([8, 1])
with col1:
    user_input = st.text_input(
        "",
        placeholder="Message MultiMind AI...",
        key="chat_input",
        label_visibility="collapsed"
    )
with col2:
    send_clicked = st.button("Send", type="primary", disabled=not user_input.strip())
st.markdown("</div>", unsafe_allow_html=True)

# Process input
if send_clicked and user_input.strip():
    # Add user message
    st.session_state.messages.append({'role': 'user', 'content': user_input})
    
    # Show thinking indicator
    with st.spinner("Thinking..."):
        try:
            result, session_id, tracer = run_task(user_input, "research")
            tracer.finalize(result)
            answer = result.get('final_answer') or result.get('research_data') or 'No answer generated'
            
            if is_demo_mode():
                answer += "\n\n*Demo mode - add API key for real responses*"
            
            st.session_state.messages.append({'role': 'assistant', 'content': answer})
        except Exception as e:
            st.session_state.messages.append({'role': 'assistant', 'content': f"Error: {str(e)}"})
    
    # Clear input
    st.session_state.chat_input = ""
    st.rerun()
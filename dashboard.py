"""
Simple and User-Friendly Streamlit Dashboard for MultiMind AI.
Designed for easy understanding by all users, including non-technical audiences.
"""

import streamlit as st
import time
from main import run_task

# Page configuration
st.set_page_config(
    page_title="MultiMind AI - See How AI Thinks",
    page_icon="🧠",
    layout="centered",  # Changed to centered for better focus
    initial_sidebar_state="collapsed"  # Start with sidebar collapsed for cleaner look
)

# Custom CSS for better appearance
st.markdown("""
<style>
    .main-header {
        text-align: center;
        padding: 2rem 0;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 10px;
        margin-bottom: 2rem;
    }
    .step-box {
        background-color: #f8f9fa;
        border-left: 4px solid #667eea;
        padding: 1rem;
        margin: 1rem 0;
        border-radius: 0 5px 5px 0;
    }
    .metric-card {
        background-color: white;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        text-align: center;
    }
    .status-success {
        color: #28a745;
        font-weight: bold;
    }
    .status-processing {
        color: #ffc107;
        font-weight: bold;
    }
    .agent-icon {
        font-size: 2rem;
        margin: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown("""
<div class="main-header">
    <h1>🧠 MultiMind AI</h1>
    <p>Watch how our AI thinks, plans, and solves problems step by step</p>
</div>
""", unsafe_allow_html=True)

# Simple explanation
with st.expander("ℹ️ How MultiMind AI Works (Click to expand)", expanded=False):
    st.markdown("""
    MultiMind AI works like a team of experts collaborating to solve your problem:
    
    1. **🧠 Planner** - Breaks down your question into smaller tasks
    2. **👔 Supervisor** - Assigns tasks to the right specialists
    3. **🔍 Researcher** - Finds information and data
    4. **💻 Coder** - Creates solutions and code when needed
    5. **✅ Validator** - Checks if the work is correct and high quality
    6. **🤔 Reflector** - Reviews the process and suggests improvements
    7. **🧠 Memory** - Remembers what it learned for future tasks
    
    Just like a human team, they communicate, check each other's work, and build on each other's ideas!
    """)

# Main input section
st.markdown("### 💬 What would you like MultiMind AI to help with?")

task_input = st.text_area(
    "Type your question or task here:",
    placeholder="Examples:\n• Explain how solar panels work\n• Create a Python script to calculate compound interest\n• Compare electric vs gas cars for environmental impact\n• Write a short story about a robot learning to paint",
    height=120,
    help="Be as specific or as general as you like - the AI will figure out the best approach!"
)

# Task type selection with simple descriptions
task_type = st.selectbox(
    "What type of help do you need?",
    [
        "Research & Information 📚",
        "Writing & Analysis ✍️", 
        "Coding & Technical 💻",
        "Let AI decide 🤖"
    ],
    index=3,
    help="Choose what kind of task this is, or let the AI decide automatically"
)

# Map the friendly names to internal types
task_type_map = {
    "Research & Information 📚": "research",
    "Writing & Analysis ✍️": "analysis", 
    "Coding & Technical 💻": "coding",
    "Let AI decide 🤖": "research"  # Default to research, but the planner will determine the actual type
}
internal_task_type = task_type_map[task_type]

# Run button - make it prominent
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    run_button = st.button(
        "🚀 Start MultiMind AI Thinking Process", 
        type="primary",
        use_container_width=True,
        help="Click to begin the AI's step-by-step thinking process"
    )

# Process and display results
if run_button and task_input.strip():
    # Clear any previous results
    if 'current_result' in st.session_state:
        del st.session_state['current_result']
    
    # Show progress
    progress_container = st.container()
    with progress_container:
        st.markdown("### 🔄 AI Thinking Process in Action")
        
        # Create a visual flow
        flow_cols = st.columns(6)
        agents = ["Planner", "Supervisor", "Researcher", "Coder", "Validator", "Reflector"]
        agent_icons = ["🧠", "👔", "🔍", "💻", "✅", "🤔"]
        
        for i, (col, agent, icon) in enumerate(zip(flow_cols, agents, agent_icons)):
            with col:
                st.markdown(f"<div style='text-align: center'><div style='font-size: 2rem;'>{icon}</div><small>{agent}</small></div>", unsafe_allow_html=True)
                if i < len(flow_cols) - 1:  # Don't show arrow after last item
                    st.markdown("<div style='text-align: center; margin-top: 1rem;'>↓</div>", unsafe_allow_html=True)
    
    # Add a spinner while processing
    with st.spinner("MultiMind AI is working through the problem step by step..."):
        start_time = time.time()
        result, session_id, tracer = run_task(task_input, internal_task_type)
        tracer.finalize(result)
        trace_report = tracer.get_trace_report()
        end_time = time.time()
    
    # Store results in session state
    st.session_state['current_result'] = {
        'result': result,
        'session_id': session_id,
        'trace_report': trace_report,
        'processing_time': end_time - start_time
    }
    
    # Rerun to show results in a clean way
    st.rerun()

# Display results if available
if 'current_result' in st.session_state:
    data = st.session_state['current_result']
    result = data['result']
    session_id = data['session_id']
    trace_report = data['trace_report']
    processing_time = data['processing_time']
    
    st.markdown("---")
    st.markdown(f"### ✅ Completed in {processing_time:.1f} seconds")
    
    # Success message
    st.success("🎉 MultiMind AI has finished thinking through your question!")
    
    # Main result display
    st.markdown("### 📋 AI's Answer")
    
    # Use a nice container for the answer
    with st.container():
        st.markdown(f"""
        <div style="
            background-color: #f0f2f6; 
            padding: 1.5rem; 
            border-radius: 10px; 
            border-left: 4px solid #667eea;
            margin: 1rem 0;
        ">
            {result.get('final_answer', 'No answer generated')}
        </div>
        """, unsafe_allow_html=True)
    
    # Show the thinking process in an expandable section
    with st.expander("🔍 See How the AI Thought Through This (Click to expand)", expanded=False):
        # Show the workflow steps in a simple timeline
        snapshots = trace_report.get('snapshots', [])
        
        if snapshots:
            st.markdown("#### 📝 Step-by-Step Thinking Process")
            
            # Create a simple vertical timeline
            for i, snap in enumerate(snapshots):
                agent_name = snap.get('agent', 'Unknown')
                agent_display_names = {
                    'planner': '🧠 Planner',
                    'supervisor': '👔 Supervisor', 
                    'research_agent': '🔍 Researcher',
                    'coder_agent': '💻 Coder',
                    'validator': '✅ Validator',
                    'reflection': '🤔 Reflector'
                }
                display_name = agent_display_names.get(agent_name, agent_name.title())
                
                # Determine status color based on step
                if i == 0:
                    border_color = "#667eea"  # First step - blue
                    bg_color = "#f0f7ff"
                elif i == len(snapshots) - 1:
                    border_color = "#28a745"  # Last step - green
                    bg_color = "#f0fff4"
                else:
                    border_color = "#ffc107"  # Middle steps - yellow
                    bg_color = "#fffbf0"
                
                st.markdown(f"""
                <div style="
                    border-left: 3px solid {border_color};
                    background-color: {bg_color};
                    padding: 1rem;
                    margin: 1rem 0;
                    border-radius: 0 5px 5px 0;
                ">
                    <h4 style="margin: 0 0 0.5rem 0; color: {border_color};">{display_name}</h4>
                    <p style="margin: 0; color: #666;">
                        {snap.get('message', 'Processing step completed')}
                    </p>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No detailed thinking process recorded for this task.")
    
    # Show quality metrics in a simple way
    st.markdown("### 📊 How Well Did the AI Perform?")
    
    metric_cols = st.columns(3)
    
    # Workflow quality
    with metric_cols[0]:
        reflection = result.get('reflection') or {}
        quality = reflection.get('workflow_quality', 0)
        if isinstance(quality, (int, float)):
            quality_percent = int(quality * 100)
        else:
            quality_percent = 0
            
        st.markdown(f"""
        <div class="metric-card">
            <h3>🎯 Quality Score</h3>
            <h2>{quality_percent}%</h2>
            <p>How good is the answer?</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Confidence
    with metric_cols[1]:
        validation = result.get('validation', {})
        confidence = validation.get('confidence', 0)
        if isinstance(confidence, (int, float)):
            confidence_percent = int(confidence * 100)
        else:
            confidence_percent = 0
            
        st.markdown(f"""
        <div class="metric-card">
            <h3>💪 Confidence</h3>
            <h2>{confidence_percent}%</h2>
            <p>How sure is the AI?</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Speed
    with metric_cols[2]:
        st.markdown(f"""
        <div class="metric-card">
            <h3>⚡ Speed</h3>
            <h2>{processing_time:.1f}s</h2>
            <p>How fast was the thinking?</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Option to run another task
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("💭 Ask Another Question", use_container_width=True):
            # Clear the current result
            del st.session_state['current_result']
            st.rerun()

else:
    # Welcome screen when no task has been run yet
    st.markdown("### 👋 Welcome to MultiMind AI!")
    
    st.markdown("""
    This is a special AI that doesn't just give you quick answers - 
    it **shows you how it thinks** step by step, just like a team of experts 
    working together to solve your problem.
    """)
    
    # Show example questions
    st.markdown("### 💡 Try asking something like:")
    
    example_cols = st.columns(2)
    with example_cols[0]:
        st.markdown("""
        - "How do vaccines work to protect us from diseases?"
        - "Write a Python program that calculates BMI"
        - "What are the pros and cons of working from home?"
        - "Explain the water cycle like I'm 10 years old"
        """)
    
    with example_cols[1]:
        st.markdown("""
        - "Create a simple budget tracker in Excel format"
        - "Why is the sky blue? Explain the science"
        - "Compare different types of renewable energy"
        - "Help me plan a healthy weekly meal plan"
        """)
    
    # Show what makes it special
    st.markdown("### 🌟 What Makes MultiMind AI Special?")
    
    feature_cols = st.columns(3)
    
    with feature_cols[0]:
        st.markdown("""
        ### 🔍 **See the Thinking**
        Watch each step of the AI's reasoning process
        """)
    
    with feature_cols[1]:
        st.markdown("""
        ### 🛡️ **Quality Built-In**
        Automatic checking and validation of answers
        """)
    
    with feature_cols[2]:
        st.markdown("""
        ### 🧠 **Learns & Improves**
        Remembers what works for better future answers
        """)
    
    # Call to action
    st.markdown("---")
    st.markdown("### Ready to see AI thinking in action?")
    st.markdown("Type your question above and click the button to begin!")

# Footer
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: #666; padding: 1rem;'>"
    "Built with Streamlit • MultiMind AI — Making AI Thinking Transparent"
    "</div>", 
    unsafe_allow_html=True
)
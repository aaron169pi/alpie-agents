python
import streamlit as st
import httpx
import json
import streamlit.components.v1 as components
import logging
import sys
import re

# --- Logging Configuration ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("app_debug.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# --- Page Configuration ---
st.set_page_config(
    page_title="169pi HTML Chatbot & Search",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': None,
        'Report a bug': None,
        'About': "# 169pi AI Assistant\nAI-powered development assistant"
    },
    theme={
        "primaryColor": "#1a73e8",
        "secondaryColor": "#00c853",
        "backgroundColor": "#f8f9fa",
        "font": "sans serif"
    }
)

# Custom CSS for enhanced styling
st.markdown("""
<style>
.sidebar .sidebar-content {
    padding-top: 4rem;
    padding-bottom: 4rem;
}

.streamlit-expanderHeader {
    border-left: 4px solid #1a73e8 !important;
}

.streamlit-chat-message.streamlit-chat-message--assistant {
    border-radius: 1rem 1rem 0rem 1rem !important;
}

.streamlit-chat-message.streamlit-chat-message--user {
    border-radius: 1rem 0rem 1rem 1rem !important;
}
</style>
""", unsafe_allow_html=True)

# --- Sidebar Configuration ---
with st.sidebar:
    st.title("Settings")
    st.markdown("---")
    api_key = st.secrets["general"]["api_key"]
    model_name = "alpie-32b"
    tavily_api_key = st.secrets["general"]["tavily_api_key"]  
    if st.button("Clear Chat History", type="primary"):
        logger.info("User cleared chat history.")
        # Clear HTML chat
        st.session_state.messages = [
            {"role": "system", "content": "You are a coding assistant that helps to build an amazing prototype that is functional. You must respond ONLY with code — no explanations, no preambles. Use HTML, CSS, and JavaScript only. Ensure your output is clean, modern, and production-quality — it should awe top-tier developers. Ensure CSS, JS is always inside HTML files only and provide the full code inside
python
import streamlit as st
import httpx
import json
import re
from dotenv import load_dotenv
import os
load_dotenv()

API_KEY = os.getenv("PI_API_KEY")
API_URL = os.getenv("PI_MODEL_ENDPOINT")
MODEL = "alpie-32b"

# Custom CSS styling
CUSTOM_CSS = """
<style>
    body {
        background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
        padding: 20px;
    }
    
    .stApp {
        max-width: 1200px;
        margin: 0 auto;
        background: white;
        border-radius: 15px;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
        padding: 30px;
    }
    
    h1 {
        color: #2b5876;
        font-weight: 700;
        margin-bottom: 30px;
        border-bottom: 2px solid #e9ecef;
        padding-bottom: 15px;
    }
    
    .sidebar .sidebar-content {
        background: #f8f9fa;
        padding: 20px;
    }
    
    .stButton > button {
        background: #2b5876;
        color: white;
        border-radius: 8px;
        padding: 12px 24px;
        font-weight: 500;
        transition: all 0.2s ease;
        border: none;
    }
    
    .stButton > button:hover {
        background: #1d3a51;
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
    }
    
    .stTextInput > input {
        border: 1px solid #dee2e6;
        border-radius: 8px;
        padding: 12px 16px;
        font-size: 16px;
        transition: all 0.2s ease;
    }
    
    .stTextInput > input:focus {
        outline: none;
        border-color: #2b5876;
        box-shadow: 0 0 0 3px rgba(43, 88, 118, 0.1);
    }
    
    .chat-message {
        border-radius: 12px;
        padding: 15px;
        margin-bottom: 15px;
        border-left: 4px solid #2b5876;
    }
    
    .component-container {
        margin-bottom: 30px;
    }
    
    .chat-history {
        background: #f8f9fa;
        padding: 20px;
        border-radius: 8px;
        margin-top: 30px;
    }
    
    .chat-history pre {
        background: none;
        padding: 0;
        font-size: 14px;
        line-height: 1.6;
    }
</style>
"""

st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
st.set_page_config(page_title="Study AI", page_icon="🎓", layout="wide")

st.sidebar.title("⚙️ Study Mode")

mode = st.sidebar.radio(
    "Choose Mode",
    ["Learning", "Flashcards", "Quiz"]
)
with st.spinner(f"Analyzing the query"):
    pass

if mode == "Quiz":
    num_questions = st.sidebar.slider("Number of Questions", 1, 20, 5)
else:
    num_questions = None

st.sidebar.markdown("---")
st.sidebar.caption("Your AI Study Companion 📚")

# ------------------- MAIN TITLE -------------------
st.title("🎓 AI Study Assistant")

# Create Session Memory
if "messages" not in st.session_state:
    st.session_state.messages = []

if "current_flashcard" not in st.session_state:
    st.session_state.current_flashcard = 0

if "flashcard_data" not in st.session_state:
    st.session_state.flashcard_data = []

if "quiz_data" not in st.session_state:
    st.session_state.quiz_data = []

if "last_learning_response" not in st.session_state:
    st.session_state.last_learning_response = None

[... rest of the unchanged code ...]
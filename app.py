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
    layout="wide"
)

# --- Sidebar Configuration ---
with st.sidebar:
    st.title("Settings")
    api_key = st.secrets["general"]["api_key"]
    model_name = "alpie-32b"
    tavily_api_key = st.secrets["general"]["tavily_api_key"]  
    if st.button("Clear Chat History"):
        logger.info("User cleared chat history.")
        # Clear HTML chat
        st.session_state.messages = [
            {"role": "system", "content": "You are a coding assistant that helps to build an amazing prototype that is functional. You must respond ONLY with code — no explanations, no preambles. Use HTML, CSS, and JavaScript only. Ensure your output is clean, modern, and production-quality — it should awe top-tier developers. Ensure CSS, JS is always inside HTML files only and provide the full code inside ```html blocks."}
        ]
        # Clear Search state
        st.session_state.search_step = 0
        st.session_state.search_queries = []
        st.session_state.search_context = ""
        st.session_state.search_topic = ""
        st.session_state.search_full_response = "" # Cache for the text answer
        st.session_state.infographic_html = ""     # Cache for the visual
        st.rerun()
        
    st.markdown("---")
    st.caption("Check your terminal or 'app_debug.log' for error details.")

# --- Session State Initialization ---
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "system", "content": "You are a coding assistant that helps to build an amazing prototype that is functional. You must respond ONLY with code — no explanations, no preambles. Use HTML, CSS, and JavaScript only. Ensure your output is clean, modern, and production-quality — it should awe top-tier developers. Ensure CSS, JS is always inside HTML files only and provide the full code inside ```html blocks."}
    ]

# State for Tab 2 (Search)
if "search_step" not in st.session_state:
    st.session_state.search_step = 0 
if "search_queries" not in st.session_state:
    st.session_state.search_queries = []
if "search_context" not in st.session_state:
    st.session_state.search_context = ""
if "search_topic" not in st.session_state:
    st.session_state.search_topic = ""
if "search_full_response" not in st.session_state:
    st.session_state.search_full_response = ""
if "infographic_html" not in st.session_state:
    st.session_state.infographic_html = ""

# --- Helper Function: Stream Generator ---
def get_stream_generator(messages, api_key, model):
    url = st.secrets["general"]["model_url"]
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "text/event-stream"
    }
    payload = {
        "model": model,
        "stream": True,
        "messages": messages,
        "max_tokens": 16000
    }

    try:
        with httpx.Client(timeout=None) as client:
            with client.stream("POST", url, headers=headers, json=payload) as res:
                if res.status_code != 200:
                    yield f"Error: {res.status_code}"
                    return

                for line in res.iter_lines():
                    line = line.decode("utf-8") if isinstance(line, bytes) else line
                    if not line:
                        continue
                    if line.strip() == "data: [DONE]":
                        return
                    
                    if line.startswith("data: "):
                        try:
                            json_str = line[6:]
                            data = json.loads(json_str)
                            content = data["choices"][0]["delta"].get("content", "")
                            if content:
                                yield content
                        except Exception:
                            continue
    except Exception as e:
        yield f"System Error: {str(e)}"

# --- Helper Function: Non-Streaming LLM Call ---
def get_simple_completion(messages, api_key, model):
    generator = get_stream_generator(messages, api_key, model)
    full_text = ""
    for chunk in generator:
        if chunk.startswith("Error"):
            return chunk
        full_text += chunk
    return full_text

# --- Helper Function: Tavily Search ---
def perform_tavily_search(query, tavily_key):
    url = "https://api.tavily.com/search"
    payload = {
        "api_key": tavily_key,
        "query": query,
        "search_depth": "basic",
        "include_answer": False,
        "max_results": 2
    }
    try:
        response = httpx.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            data = response.json()
            results = data.get("results", [])
            context_str = "\n".join([f"- {r['content']} (Source: {r['url']})" for r in results])
            return context_str
        else:
            return f"Error searching Tavily: {response.status_code}"
    except Exception as e:
        return f"Exception during search: {e}"

# --- Helper Function: Parse and Render Output ---
def parse_and_render(content, show_html=True):
    final_response = content
    if "</think>" in content:
        parts = content.split("</think>", 1)
        thought_process = parts[0].replace("<think>", "").strip()
        final_response = parts[1].strip()
        with st.expander("Thinking"):
            st.markdown(thought_process)
    
    st.markdown(final_response)

    if show_html:
        html_blocks = re.findall(r"```html(.*?)```", final_response, re.DOTALL)
        if html_blocks:
            st.markdown("---")
            st.subheader("🖼️ Live HTML Preview")
            for i, html_code in enumerate(html_blocks):
                with st.container(border=True):
                    st.caption(f"Preview #{i+1}")
                    components.html(html_code.strip(), height=600, scrolling=True)


# --- Tabs Configuration ---
tab1, tab2 = st.tabs(["Coding Agent", " Deep Research"])

# ==========================================
# TAB 1: EXISTING HTML CHATBOT
# ==========================================
with tab1:
    
    messages_container = st.container()
    
    with messages_container:
        for msg in st.session_state.messages:
            if msg["role"] != "system":
                with st.chat_message(msg["role"]):
                    if msg["role"] == "user":
                        st.write(msg["content"])
                    else:
                        if msg["content"].startswith("Error:") or msg["content"].startswith("System Error:"):
                            st.error(msg["content"])
                        else:
                            parse_and_render(msg["content"])

    if prompt := st.chat_input("Type a message (e.g., 'Create a login form in HTML')...", key="html_chat_input"):
        if not api_key:
            st.error("Please enter your LLM API Key in the sidebar.")
            st.stop()

        st.session_state.messages.append({"role": "user", "content": prompt})
        
        with messages_container:
            with st.chat_message("user"):
                st.write(prompt)

            with st.chat_message("assistant"):
                stream_placeholder = st.empty()
                full_response = ""
                is_error = False
                
                stream_gen = get_stream_generator(st.session_state.messages, api_key, model_name)
                
                for chunk in stream_gen:
                    if chunk.startswith("Error:") or chunk.startswith("System Error:"):
                        is_error = True
                        full_response = chunk
                        stream_placeholder.error(chunk)
                        break
                    
                    full_response += chunk
                    stream_placeholder.markdown(full_response + "▌")
                
                if not is_error:
                    stream_placeholder.empty()
                    parse_and_render(full_response)
                
                st.session_state.messages.append({"role": "assistant", "content": full_response})

# ==========================================
# TAB 2: DEEP RESEARCH (TAVILY)
# ==========================================
with tab2:
    st.header("Deep Research Agent")
    st.caption("Enter a topic -> Agent auto-researches -> Answer synthesized -> Generate Infographics.")

    research_container = st.container()

    with research_container:
        # Step 0: Initial Input & Auto-Launch
        if st.session_state.search_step == 0:
            with st.form("search_init_form"):
                topic = st.text_input("What do you want to research?", placeholder="e.g. Current trends in electric vehicles")
                submitted = st.form_submit_button("Start Research")
                
                if submitted and topic:
                    if not api_key:
                        st.error("LLM API Key missing.")
                    elif not tavily_api_key:
                        st.error("Tavily API Key missing in sidebar.")
                    else:
                        st.session_state.search_topic = topic
                        st.session_state.search_context = "" 
                        st.session_state.search_full_response = ""
                        st.session_state.infographic_html = ""
                        
                        with st.spinner("Analyzing topic & generating queries..."):
                            gen_prompt = f"""
                            You are a research assistant. 
                            Generate exactly 4 specific web search queries to gather comprehensive information about: "{topic}".
                            Return ONLY the queries as a numbered list (1. query...).
                            """
                            temp_msgs = [{"role": "user", "content": gen_prompt}]
                            raw_response = get_simple_completion(temp_msgs, api_key, model_name)
                            
                            if "</think>" in raw_response:
                                raw_response = raw_response.split("</think>")[1].strip()
                                
                            queries = []
                            for line in raw_response.split('\n'):
                                clean_line = re.sub(r'^\d+\.\s*', '', line.strip()).strip()
                                if clean_line:
                                    queries.append(clean_line)
                            
                            st.session_state.search_queries = queries[:4]
                            st.session_state.search_step = 2
                            st.rerun()

        # Step 2: Execute Search & Synthesize
        if st.session_state.search_step == 2:
            st.subheader(f"Researching: {st.session_state.search_topic}")
            
            # 1. Perform Searches (if context is empty)
            if not st.session_state.search_context:
                status_text = st.empty()
                progress_bar = st.progress(0)
                full_context = ""
                
                with st.expander("View generated search queries", expanded=True):
                    for q in st.session_state.search_queries:
                        st.write(f"- {q}")

                for i, query in enumerate(st.session_state.search_queries):
                    status_text.text(f"Searching web for: {query}...")
                    result = perform_tavily_search(query, tavily_api_key)
                    full_context += f"\n\n--- Results for '{query}' ---\n{result}"
                    progress_bar.progress((i + 1) / len(st.session_state.search_queries))
                
                st.session_state.search_context = full_context
                progress_bar.progress(100)
                status_text.text("Search complete. Synthesizing answer...")
            
            # 2. Synthesize Answer (or show cached answer)
            st.markdown("### 📝 Research Findings")
            
            # If we haven't generated the text answer yet:
            if not st.session_state.search_full_response:
                final_prompt = f"""
                You are a comprehensive research assistant.
                User Question: "{st.session_state.search_topic}"
                
                Below is the raw data retrieved from several web searches:
                {st.session_state.search_context}
                
                Instructions:
                1. Synthesize a detailed answer based strictly on the provided context.
                2. Cite sources where possible (urls are provided in context).
                3. Use Markdown formatting.
                """
                
                search_msgs = [{"role": "user", "content": final_prompt}]
                
                with st.chat_message("assistant"):
                    stream_placeholder = st.empty()
                    full_response = ""
                    is_error = False
                    
                    stream_gen = get_stream_generator(search_msgs, api_key, model_name)
                    
                    for chunk in stream_gen:
                        if chunk.startswith("Error:") or chunk.startswith("System Error:"):
                            is_error = True
                            full_response = chunk
                            stream_placeholder.error(chunk)
                            break
                        full_response += chunk
                        stream_placeholder.markdown(full_response + "▌")
                    
                    if not is_error:
                        stream_placeholder.empty()
                        # Save to state so we don't regenerate on button clicks
                        st.session_state.search_full_response = full_response
                        parse_and_render(full_response)
            else:
                # If cached, just render the cached response
                parse_and_render(st.session_state.search_full_response, show_html=False)

            # 3. Infographic Generation Section
            st.markdown("---")
            col1, col2 = st.columns([1, 4])
            
            with col1:
                # Button to trigger infographic generation
                if st.button("📊 Generate Infographics", type="primary"):
                    if not st.session_state.search_context:
                        st.error("No data available to visualize.")
                    else:
                        st.session_state.infographic_html = "GENERATING" # Marker
                        st.rerun()

            with col2:
                if st.button("Start New Research"):
                    st.session_state.search_step = 0
                    st.session_state.search_queries = []
                    st.session_state.search_context = ""
                    st.session_state.search_topic = ""
                    st.session_state.search_full_response = ""
                    st.session_state.infographic_html = ""
                    st.rerun()

            # 4. Handle Infographic Generation & Display
            if st.session_state.infographic_html == "GENERATING":
                with st.spinner("Analyzing data and designing interactive dashboard..."):
                    # Create prompt for the visual specialist
                    visual_prompt = f"""
You are an expert Frontend Developer and Blog Report Writer.

Task: Create a single, self-contained HTML file (with embedded CSS and JS) that looks like a clean, 
modern blog article. The goal is to present all the research data below in the form of a long, 
readable blog post. Add charts only where they naturally help illustrate a point.

Requirements:

1. The output should feel like a **generic blog page**:
   - A large title
   - An introduction
   - Multiple long paragraphs and sections
   - Smooth dark-mode design
   - Comfortable reading layout

2. Use **Chart.js** (via CDN: https://cdn.jsdelivr.net/npm/chart.js) **only if useful** to support the text.
   - At most 2–3 charts.
   - Charts should not dominate the page — they should support the writing.

3. The blog should be **verbose, narrative, and easy to read**, expanding the research data into a 
   flowing article instead of a summary or bullet points.

4. The structure should resemble a typical long blog post:
   - Title
   - Intro paragraph
   - Main body with subsections
   - Occasional charts placed between relevant paragraphs
   - Final closing thoughts

5. The final answer must be ONLY the full HTML inside a ```html block.

6. Use and expand the following data into a detailed blog-style article:
{st.session_state.search_context}
{st.session_state.search_full_response}
"""

                    
                    msgs = [{"role": "user", "content": visual_prompt}]
                    
                    # We stream it to show progress, but we only really care about the final HTML
                    full_code_response = get_simple_completion(msgs, api_key, model_name)
                    
                    # Extract HTML
                    html_match = re.search(r"```html(.*?)```", full_code_response, re.DOTALL)
                    if html_match:
                        st.session_state.infographic_html = html_match.group(1).strip()
                    else:
                        st.session_state.infographic_html = "ERROR: Could not generate HTML."
                    
                    st.rerun()
            
            elif st.session_state.infographic_html and st.session_state.infographic_html != "GENERATING" and not st.session_state.infographic_html.startswith("ERROR"):
                st.subheader("📊 Interactive Research Dashboard")
                with st.container(border=True):
                    components.html(st.session_state.infographic_html, height=800, scrolling=True)
            
            elif st.session_state.infographic_html.startswith("ERROR"):
                st.error("Failed to generate valid HTML for the infographic. Please try again.")

import streamlit as st
from supabase import create_client
from sentence_transformers import SentenceTransformer
import requests
import json
import time

# --- PAGE CONFIG ---
st.set_page_config(page_title="LyceeAI", page_icon="🎓", layout="centered")

# --- DATABASE & AI SETUP ---
try:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    openrouter_key = st.secrets["OPENROUTER_API_KEY"]
except Exception as e:
    st.error("Secrets are missing. Please check your Streamlit Cloud settings.")
    st.stop()

supabase = create_client(url, key)

@st.cache_resource
def load_embed():
    return SentenceTransformer('all-MiniLM-L6-v2')

# --- THE AUTO-ROUTER ENGINE (Infinite Reliability) ---
def ask_openrouter(messages):
    endpoint = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {openrouter_key}",
        "HTTP-Referer": "https://lyceeai.streamlit.app", 
        "Content-Type": "application/json"
    }
    
    # Using 'openrouter/auto' - This automatically picks the best working model
    data = {
        "model": "openrouter/auto",
        "messages": messages,
        "temperature": 0.4
    }
    
    # We will try 3 times automatically before giving up
    for attempt in range(3):
        try:
            response = requests.post(endpoint, headers=headers, data=json.dumps(data), timeout=45)
            if response.status_code == 200:
                return response.json()['choices'][0]['message']['content']
            elif response.status_code == 401:
                return "Error: Your API Key is invalid or hasn't updated yet. Please wait 5 minutes."
            else:
                time.sleep(2) # Wait 2 seconds before retrying
                continue
        except:
            time.sleep(2)
            continue
            
    return "The system is warming up for your 10 users. Please try one more time!"

# --- SIDEBAR ---
with st.sidebar:
    st.header("🛠 Founder Tools")
    st.info("Mode: Auto-Routing (High Uptime)")
    
    if st.button("🔍 Audit Knowledge Base"):
        try:
            res = supabase.table("documents").select("content").limit(2).execute()
            for item in res.data:
                st.code(f"DB Entry: {item['content'][:100]}...")
        except:
            st.error("Database Connection Issue.")
    
    st.divider()
    if st.button("🗑 Clear My Chat"):
        st.session_state.messages = []
        st.rerun()

# --- APP INTERFACE ---
st.title("🎓 LyceeAI")
st.caption("Active Mentor for Tunisian Baccalaureate")

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Ask a question..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Finding the best AI for you..."):
            try:
                # 1. SEARCH
                query_vec = load_embed().encode(prompt).tolist()
                result = supabase.rpc("match_documents", {
                    "query_embedding": query_vec,
                    "match_threshold": 0.05, 
                    "match_count": 3 
                }).execute()
                
                context = "\n".join([item['content'] for item in result.data]) if result.data else "General academic knowledge."

                # 2. SYSTEM
                system_msg = f"You are LyceeAI, a professional tutor. Use context: {context}."
                
                chat_history = [{"role": "system", "content": system_msg}]
                for msg in st.session_state.messages[-3:]:
                    chat_history.append(msg)
                
                # 3. GENERATE
                response_text = ask_openrouter(chat_history)
                
                st.markdown(response_text)
                st.session_state.messages.append({"role": "assistant", "content": response_text})
                
            except Exception as e:
                st.error("System is busy. Please resend.")

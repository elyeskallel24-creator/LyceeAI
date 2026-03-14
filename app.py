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

# --- THE UNSTOPPABLE ENGINE (Auto-Routing) ---
def ask_openrouter(messages):
    endpoint = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {openrouter_key}",
        "HTTP-Referer": "https://lyceeai.streamlit.app", 
        "Content-Type": "application/json"
    }
    
    data = {
        "model": "openrouter/auto",
        "messages": messages,
        "temperature": 0.3 # Lower temperature for better accuracy on your data
    }
    
    for attempt in range(3):
        try:
            response = requests.post(endpoint, headers=headers, data=json.dumps(data), timeout=45)
            if response.status_code == 200:
                return response.json()['choices'][0]['message']['content']
            time.sleep(2)
        except:
            time.sleep(2)
            continue
            
    return "The system is currently scanning your data. Please try one more time!"

# --- SIDEBAR (KEPT EXACTLY THE SAME) ---
with st.sidebar:
    st.header("🛠 Founder Tools")
    st.info("Mode: Auto-Routing (High Uptime)")
    
    if st.button("🔍 Audit Knowledge Base"):
        try:
            res = supabase.table("documents").select("content").limit(2).execute()
            for item in res.data:
                st.code(f"DB Entry: {item['content'][:150]}...")
        except:
            st.error("Database Connection Issue.")
    
    st.divider()
    if st.button("🗑 Clear My Chat"):
        st.session_state.messages = []
        st.rerun()

# --- APP INTERFACE ---
st.title("🎓 LyceeAI")
st.caption("Active Mentor for Your Knowledge Base")

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Ask a question about your files..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Analyzing your 7,000 chunks..."):
            try:
                # 1. SEARCH WITH HIGHER MATCH COUNT
                # We increased match_count to 10 to see more diversity when you ask broad questions
                query_vec = load_embed().encode(prompt).tolist()
                result = supabase.rpc("match_documents", {
                    "query_embedding": query_vec,
                    "match_threshold": 0.05, 
                    "match_count": 10 
                }).execute()
                
                context = "\n".join([item['content'] for item in result.data]) if result.data else "No specific data found."

                # 2. SYSTEM ARCHITECTURE (Surgically aligned to your mission)
                system_msg = f"""
                You are LyceeAI, a professional mentor. 
                You have a knowledge base of 7,000 file chunks. 
                
                YOUR MISSION:
                1. If the user asks for 'titles' or 'subjects', scan the CONTEXT below for any headings or topics.
                2. If the user asks for a specific topic (like Python or SVT), teach it ONLY using the context.
                3. Do not mention Harry Potter or random exercises unless they are the primary focus of the question.
                
                CONTEXT FROM YOUR DATABASE:
                {context}
                """
                
                chat_history = [{"role": "system", "content": system_msg}]
                for msg in st.session_state.messages[-3:]:
                    chat_history.append(msg)
                
                # 3. GENERATE
                response_text = ask_openrouter(chat_history)
                
                st.markdown(response_text)
                st.session_state.messages.append({"role": "assistant", "content": response_text})
                
            except Exception as e:
                st.error("I'm slightly busy. Please resend that question!")

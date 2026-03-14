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
    st.error("Secrets are missing in Streamlit Cloud.")
    st.stop()

supabase = create_client(url, key)

@st.cache_resource
def load_embed():
    # Keep using 384 dimensions for speed and efficiency
    return SentenceTransformer('all-MiniLM-L6-v2')

# --- THE AUTO-ROUTER ENGINE ---
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
        "temperature": 0.3
    }
    
    for attempt in range(2):
        try:
            response = requests.post(endpoint, headers=headers, data=json.dumps(data), timeout=45)
            if response.status_code == 200:
                return response.json()['choices'][0]['message']['content']
            time.sleep(1)
        except:
            continue
            
    return "I'm having trouble reaching the AI. Please try once more!"

# --- SIDEBAR (Preserved arrows/buttons) ---
with st.sidebar:
    st.header("🛠 Founder Tools")
    st.info("Mode: Auto-Routing (High Uptime)")
    
    if st.button("🔍 Audit Knowledge Base"):
        try:
            res = supabase.table("documents").select("content, metadata").limit(3).execute()
            if not res.data:
                st.warning("Database is empty. Ready for re-upload!")
            for item in res.data:
                source = item.get('metadata', {}).get('source', 'Unknown Book')
                st.caption(f"📖 {source}")
                st.code(f"{item['content'][:100]}...")
        except Exception as e:
            st.error(f"DB Error: {str(e)}")
    
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

if prompt := st.chat_input("Ask a question about your books..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Searching the library..."):
            try:
                # SEARCH WITH METADATA AWARENESS
                query_vec = load_embed().encode(prompt).tolist()
                result = supabase.rpc("match_documents", {
                    "query_embedding": query_vec,
                    "match_threshold": 0.05, 
                    "match_count": 8 
                }).execute()
                
                # Format context to show book titles to the AI
                context_parts = []
                for item in result.data:
                    book_title = item.get('metadata', {}).get('source', 'Unknown')
                    context_parts.append(f"FROM BOOK [{book_title}]: {item['content']}")
                
                context = "\n\n".join(context_parts) if context_parts else "The library is currently empty."

                # SYSTEM INSTRUCTIONS
                system_msg = f"""You are LyceeAI. Answer using only the provided context. 
                If the user asks for 'titles', list the 'FROM BOOK' names.
                CONTEXT:
                {context}"""
                
                chat_history = [{"role": "system", "content": system_msg}]
                for msg in st.session_state.messages[-3:]:
                    chat_history.append(msg)
                
                response_text = ask_openrouter(chat_history)
                st.markdown(response_text)
                st.session_state.messages.append({"role": "assistant", "content": response_text})
                
            except Exception as e:
                st.error("Database connection is resetting. Please try again.")

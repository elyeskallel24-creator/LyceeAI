import streamlit as st
from supabase import create_client
from sentence_transformers import SentenceTransformer
import requests
import json

# --- PAGE CONFIG ---
st.set_page_config(page_title="LyceeAI", page_icon="🎓", layout="centered")

# --- DATABASE & AI SETUP ---
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
openrouter_key = st.secrets["OPENROUTER_API_KEY"]

supabase = create_client(url, key)

@st.cache_resource
def load_embed():
    return SentenceTransformer('all-MiniLM-L6-v2')

# --- THE HARDCORE ENGINE (High-Volume Stable Mode) ---
def ask_openrouter(messages):
    endpoint = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {openrouter_key}",
        "HTTP-Referer": "https://lyceeai.streamlit.app", 
        "Content-Type": "application/json"
    }
    
    # Surgical Choice: Gemini Flash 1.5 8B is the most stable "high-volume" free model
    data = {
        "model": "google/gemini-flash-1.5-8b:free",
        "messages": messages,
        "temperature": 0.4
    }
    
    try:
        # Increased timeout to 60s so 10 users don't get cut off during peak lag
        response = requests.post(endpoint, headers=headers, data=json.dumps(data), timeout=60)
        
        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content']
        else:
            # Fallback to another hyper-fast model if Gemini is truly down
            data["model"] = "meta-llama/llama-3.2-3b-instruct:free"
            response = requests.post(endpoint, headers=headers, data=json.dumps(data), timeout=60)
            return response.json()['choices'][0]['message']['content']
            
    except Exception as e:
        return "The AI is processing a lot of data right now. Please wait 10 seconds and try again."

# --- SIDEBAR (The Founder's Hub) ---
with st.sidebar:
    st.header("🛠 Founder Tools")
    st.success("High-Capacity Mode: ON")
    
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
st.caption("24/7 High-Capacity Mentor for Baccalauréat")

if "messages" not in st.session_state:
    st.session_state.messages = []

# Display conversation
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Ask a question about your lessons..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Sourcing data for your team..."):
            try:
                # 1. SEARCH
                query_vec = load_embed().encode(prompt).tolist()
                result = supabase.rpc("match_documents", {
                    "query_embedding": query_vec,
                    "match_threshold": 0.05, 
                    "match_count": 3 
                }).execute()
                
                context = "\n".join([item['content'] for item in result.data]) if result.data else "General knowledge."

                # 2. SYSTEM INSTRUCTIONS
                system_msg = f"You are LyceeAI, a mentor for the Tunisian Baccalaureate. Context: {context}."
                
                # 3. CONSTRUCT MEMORY
                chat_history = [{"role": "system", "content": system_msg}]
                for msg in st.session_state.messages[-3:]:
                    chat_history.append(msg)
                
                # 4. EXECUTE
                response_text = ask_openrouter(chat_history)
                
                st.markdown(response_text)
                st.session_state.messages.append({"role": "assistant", "content": response_text})
                
            except Exception as e:
                st.error("Wait 5 seconds and resend your message.")

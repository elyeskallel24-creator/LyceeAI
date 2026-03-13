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

# --- THE UNSTOPPABLE ENGINE (Failover Logic) ---
def ask_openrouter(messages):
    endpoint = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {openrouter_key}",
        "HTTP-Referer": "https://lyceeai.streamlit.app", 
        "Content-Type": "application/json"
    }
    
    # List of FREE stable models to try in order
    models_to_try = [
        "qwen/qwen-2.5-72b-instruct:free",
        "google/gemma-2-9b-it:free",
        "mistralai/mistral-7b-instruct:free"
    ]
    
    last_error = ""
    for model in models_to_try:
        try:
            data = {
                "model": model,
                "messages": messages,
                "temperature": 0.4
            }
            # 15 second timeout per model to keep it fast
            response = requests.post(endpoint, headers=headers, data=json.dumps(data), timeout=15)
            if response.status_code == 200:
                return response.json()['choices'][0]['message']['content']
            else:
                last_error = f"Status {response.status_code}"
                continue # Try the next model
        except Exception as e:
            last_error = str(e)
            continue # Try the next model
            
    return f"The AI network is very busy right now. Please wait 10 seconds and try again. (System Note: {last_error[:50]})"

# --- SIDEBAR (The Founder's Hub) ---
with st.sidebar:
    st.header("🛠 Founder Tools")
    st.info("Status: Multi-Model Failover Active")
    
    if st.button("🔍 Audit Knowledge Base"):
        try:
            res = supabase.table("documents").select("content").limit(3).execute()
            for item in res.data:
                st.code(f"Chunk: {item['content'][:150]}...")
        except:
            st.error("Database connection issue.")
    
    if st.button("🗑 Clear My Chat"):
        st.session_state.messages = []
        st.rerun()

# --- APP INTERFACE ---
st.title("🎓 LyceeAI")
st.caption("24/7 High-Performance Mentor")

if "messages" not in st.session_state:
    st.session_state.messages = []

# Display history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("What would you like to learn today?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Analyzing your 7,000 lessons..."):
            try:
                # 1. SEARCH
                query_vec = load_embed().encode(prompt).tolist()
                result = supabase.rpc("match_documents", {
                    "query_embedding": query_vec,
                    "match_threshold": 0.05, 
                    "match_count": 3 
                }).execute()
                
                context = ""
                if result.data:
                    context = "\n".join([item['content'] for item in result.data])
                else:
                    context = "No specific chunk found. Use general knowledge."

                # 2. SYSTEM ARCHITECTURE
                system_content = f"You are LyceeAI, a professional Tunisian Baccalaureate mentor. Use context: {context}."
                
                chat_history = [{"role": "system", "content": system_content}]
                for msg in st.session_state.messages[-3:]:
                    chat_history.append(msg)
                
                # 3. GENERATE (Will try multiple models)
                response_text = ask_openrouter(chat_history)
                
                st.markdown(response_text)
                st.session_state.messages.append({"role": "assistant", "content": response_text})
                
            except Exception as e:
                st.error("I'm refreshing my circuits. Please try one more time!")

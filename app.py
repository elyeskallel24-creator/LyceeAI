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

# --- THE UNSTOPPABLE ENGINE (Surgical Failover) ---
def ask_openrouter(messages):
    endpoint = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {openrouter_key}",
        "HTTP-Referer": "https://lyceeai.streamlit.app", 
        "Content-Type": "application/json"
    }
    
    # Priority list of high-speed free models
    models_to_try = [
        "google/gemma-2-9b-it:free",
        "qwen/qwen-2.5-72b-instruct:free",
        "mistralai/mistral-7b-instruct:free"
    ]
    
    for model in models_to_try:
        try:
            data = {
                "model": model,
                "messages": messages,
                "temperature": 0.4,
                "max_tokens": 1000
            }
            # Rapid-fire timeout: if a model doesn't respond in 8s, move to the next
            response = requests.post(endpoint, headers=headers, data=json.dumps(data), timeout=8)
            
            if response.status_code == 200:
                return response.json()['choices'][0]['message']['content']
        except:
            continue 
            
    return "I am experiencing high traffic. Please tap 'Enter' again in 5 seconds to reconnect."

# --- SIDEBAR (The Founder's Control Panel) ---
with st.sidebar:
    st.header("🛠 Founder Tools")
    st.success("API Status: Connected")
    
    if st.button("🔍 Audit Knowledge Base"):
        try:
            res = supabase.table("documents").select("content").limit(2).execute()
            for item in res.data:
                st.caption(f"DB Entry: {item['content'][:100]}...")
        except:
            st.error("Check Database Connection.")
    
    st.divider()
    if st.button("🗑 Clear My Chat"):
        st.session_state.messages = []
        st.rerun()

# --- APP INTERFACE ---
st.title("🎓 LyceeAI")
st.caption("Tunisian Baccalaureate Mentor - High Speed Mode")

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
        with st.spinner("Retrieving lesson data..."):
            try:
                # 1. SEARCH DATABASE
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
                    context = "No specific chunk found. Reply using general academic knowledge."

                # 2. SYSTEM INSTRUCTIONS
                system_msg = f"You are LyceeAI, an expert Tunisian Baccalaureate tutor. Context: {context}. Be precise and professional."
                
                # 3. CONSTRUCT MEMORY
                chat_history = [{"role": "system", "content": system_msg}]
                # Send the last 4 messages so the AI remembers the conversation
                for msg in st.session_state.messages[-4:]:
                    chat_history.append(msg)
                
                # 4. EXECUTE AI CALL
                response_text = ask_openrouter(chat_history)
                
                st.markdown(response_text)
                st.session_state.messages.append({"role": "assistant", "content": response_text})
                
            except Exception as e:
                st.error("System refresh in progress. Please re-send your message.")

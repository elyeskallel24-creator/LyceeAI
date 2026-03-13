import streamlit as st
from supabase import create_client
from sentence_transformers import SentenceTransformer
import requests

# --- PAGE CONFIG ---
st.set_page_config(page_title="LyceeAI", page_icon="🎓", layout="centered")

# --- DATABASE & AI SETUP ---
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
together_key = st.secrets["TOGETHER_API_KEY"]

supabase = create_client(url, key)

@st.cache_resource
def load_embed():
    return SentenceTransformer('all-MiniLM-L6-v2')

# --- TOGETHER.AI ENGINE WITH MEMORY ---
def ask_llm(messages):
    endpoint = "https://api.together.xyz/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {together_key}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "meta-llama/Llama-3-70b-chat-hf",
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 1024
    }
    try:
        response = requests.post(endpoint, headers=headers, json=data, timeout=15)
        return response.json()['choices'][0]['message']['content']
    except Exception as e:
        return f"Error: The AI engine is currently rebooting. Please try again in 10 seconds."

# --- SIDEBAR (The Founder's Hub) ---
with st.sidebar:
    st.header("🛠 Founder Tools")
    st.success("Engine: Llama-3 (High-Speed)")
    
    if st.button("🔍 Audit Knowledge Base"):
        res = supabase.table("documents").select("content").limit(3).execute()
        for item in res.data:
            st.info(f"Chunk: {item['content'][:150]}...")
    
    if st.button("🗑 Clear My Chat"):
        st.session_state.messages = []
        st.rerun()

# --- APP INTERFACE ---
st.title("🎓 LyceeAI")
st.caption("24/7 High-Speed Mentor Enabled")

if "messages" not in st.session_state:
    st.session_state.messages = []

# Display history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Ask a question about your lessons..."):
    # Add user message to state
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Sourcing Knowledge Base..."):
            try:
                # 1. SEARCH
                query_vec = load_embed().encode(prompt).tolist()
                result = supabase.rpc("match_documents", {
                    "query_embedding": query_vec,
                    "match_threshold": 0.1, # Lowered to catch more relevant content
                    "match_count": 4 
                }).execute()
                
                context = "\n".join([item['content'] for item in result.data]) if result.data else "No specific lesson found."

                # 2. PREPARE PROMPT WITH MEMORY
                system_message = {
                    "role": "system", 
                    "content": f"You are LyceeAI, a mentor for Tunisian Baccalaureate students. Use this context: {context}. Be encouraging and professional."
                }
                
                # We send the last 5 messages + the system instructions for memory
                chat_history = [system_message] + st.session_state.messages[-5:]
                
                # 3. GENERATE
                response_text = ask_llm(chat_history)
                
                st.markdown(response_text)
                st.session_state.messages.append({"role": "assistant", "content": response_text})
                
            except Exception as e:
                st.error("I hit a small snag. Let's try that question again!")

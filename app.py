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

# --- OPENROUTER ENGINE (The Unstoppable Engine) ---
def ask_openrouter(messages):
    endpoint = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {openrouter_key}",
        "HTTP-Referer": "https://lyceeai.streamlit.app", # Required by OpenRouter
        "Content-Type": "application/json"
    }
    
    # Using a high-performance FREE model
    data = {
        "model": "mistralai/mistral-7b-instruct:free", 
        "messages": messages,
        "temperature": 0.7
    }
    
    try:
        response = requests.post(endpoint, headers=headers, data=json.dumps(data), timeout=20)
        response.raise_for_status()
        return response.json()['choices'][0]['message']['content']
    except Exception as e:
        return f"AI is briefly recalibrating. Just wait 5 seconds and try your question again! (Error: {str(e)[:50]})"

# --- SIDEBAR (The Hub) ---
with st.sidebar:
    st.header("🛠 Founder Tools")
    st.success("Engine: OpenRouter (Free Tier)")
    
    if st.button("🔍 Audit Knowledge Base"):
        res = supabase.table("documents").select("content").limit(3).execute()
        for item in res.data:
            st.info(f"Chunk: {item['content'][:150]}...")
    
    if st.button("🗑 Clear My Chat"):
        st.session_state.messages = []
        st.rerun()

# --- APP INTERFACE ---
st.title("🎓 LyceeAI")
st.caption("Free, Unlimited High-Speed Learning")

if "messages" not in st.session_state:
    st.session_state.messages = []

# Display history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Ask a question about your lessons..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Consulting your database..."):
            try:
                # 1. SEARCH
                query_vec = load_embed().encode(prompt).tolist()
                result = supabase.rpc("match_documents", {
                    "query_embedding": query_vec,
                    "match_threshold": 0.1,
                    "match_count": 4 
                }).execute()
                
                context = "\n".join([item['content'] for item in result.data]) if result.data else "No specific lesson found."

                # 2. PREPARE PROMPT WITH MEMORY
                system_content = f"You are LyceeAI, a professional mentor for the Tunisian Baccalaureate. Use this lesson context: {context}. Keep answers helpful and structured."
                
                # Format for OpenRouter
                chat_history = [{"role": "system", "content": system_content}]
                for msg in st.session_state.messages[-5:]:
                    chat_history.append(msg)
                
                # 3. GENERATE
                response_text = ask_openrouter(chat_history)
                
                st.markdown(response_text)
                st.session_state.messages.append({"role": "assistant", "content": response_text})
                
            except Exception as e:
                st.error("Connection hiccup! One more try should do it.")

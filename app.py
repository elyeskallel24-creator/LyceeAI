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

# --- OPENROUTER ENGINE (Ultra-Stable Version) ---
def ask_openrouter(messages):
    endpoint = "https://openrouter.ai/api/v1/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {openrouter_key}",
        "HTTP-Referer": "https://lyceeai.streamlit.app", 
        "Content-Type": "application/json"
    }
    
    # We are switching to Qwen 2.5 72B - it's currently the most stable free model
    data = {
        "model": "qwen/qwen-2.5-72b-instruct:free", 
        "messages": messages,
        "temperature": 0.3 # Low temperature for high accuracy
    }
    
    try:
        response = requests.post(endpoint, headers=headers, data=json.dumps(data), timeout=30)
        
        # If the model is down, we automatically try a backup free model
        if response.status_code != 200:
            data["model"] = "huggingfaceh4/zephyr-7b-beta:free"
            response = requests.post(endpoint, headers=headers, data=json.dumps(data), timeout=30)

        response.raise_for_status()
        return response.json()['choices'][0]['message']['content']
    except Exception as e:
        return "I'm connecting to the knowledge base... please click 'Enter' one more time!"

# --- SIDEBAR (Founder's Dashboard) ---
with st.sidebar:
    st.header("🛠 Founder Tools")
    st.success("Engine: OpenRouter (Multi-Model)")
    
    if st.button("🔍 Audit Knowledge Base"):
        try:
            res = supabase.table("documents").select("content").limit(3).execute()
            for item in res.data:
                st.info(f"Chunk: {item['content'][:150]}...")
        except:
            st.error("Could not connect to database.")
    
    if st.button("🗑 Clear My Chat"):
        st.session_state.messages = []
        st.rerun()

# --- APP INTERFACE ---
st.title("🎓 LyceeAI")
st.caption("24/7 Academic Mentor for Baccalauréat")

if "messages" not in st.session_state:
    st.session_state.messages = []

# Display conversation history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Ask a question about your lessons..."):
    # Store user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Searching your 7,000 lessons..."):
            try:
                # 1. VECTOR SEARCH
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
                    context = "No specific lesson chunk found. Answer based on general Baccalaureate knowledge."

                # 2. SYSTEM ARCHITECTURE
                system_content = f"You are LyceeAI. Use this lesson data: {context}. Respond professionally in the language the user uses."
                
                # Build message list for AI
                chat_history = [{"role": "system", "content": system_content}]
                # Send last 3 exchanges for context memory
                for msg in st.session_state.messages[-3:]:
                    chat_history.append(msg)
                
                # 3. GET RESPONSE
                response_text = ask_openrouter(chat_history)
                
                st.markdown(response_text)
                st.session_state.messages.append({"role": "assistant", "content": response_text})
                
            except Exception as e:
                st.error("I'm having a quick technical refresh. Please try your question again!")

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
together_key = st.secrets["TOGETHER_API_KEY"]

supabase = create_client(url, key)

@st.cache_resource
def load_embed():
    return SentenceTransformer('all-MiniLM-L6-v2')

# --- TOGETHER.AI FUNCTION (The new engine) ---
def ask_llm(system_prompt, user_prompt):
    endpoint = "https://api.together.xyz/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {together_key}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "meta-llama/Llama-3-70b-chat-hf",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 1024
    }
    response = requests.post(endpoint, headers=headers, json=data)
    return response.json()['choices'][0]['message']['content']

# --- SIDEBAR (Still here and better!) ---
with st.sidebar:
    st.header("🛠 Founder Tools")
    st.success("Engine: Together.ai (Llama 3)")
    
    if st.button("🔍 Audit Data"):
        res = supabase.table("documents").select("content").limit(3).execute()
        for item in res.data:
            st.info(f"Chunk: {item['content'][:150]}...")

# --- APP INTERFACE ---
st.title("🎓 LyceeAI")
st.caption("24/7 High-Speed Access Enabled")

# Initialize isolated chat history for each user
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Ask about your lessons..."):
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
                    "match_threshold": 0.15, 
                    "match_count": 5 
                }).execute()
                
                context = "\n".join([item['content'] for item in result.data]) if result.data else "No context found."

                # 2. GENERATE
                system_instructions = f"""
                You are LyceeAI, a mentor for the Tunisian Baccalaureate.
                USE THIS CONTEXT TO ANSWER: {context}
                
                If the user says 'Hello', greet them warmly and ask which subject they want to study.
                If they ask 'what subjects', analyze the context and list what you see (e.g. English, SVT).
                """
                
                response_text = ask_llm(system_instructions, prompt)
                
                st.markdown(response_text)
                st.session_state.messages.append({"role": "assistant", "content": response_text})
            except Exception as e:
                st.error("Engine busy. Please try again in a moment.")

import streamlit as st
from supabase import create_client
from sentence_transformers import SentenceTransformer
import google.generativeai as genai

# --- PAGE CONFIG ---
st.set_page_config(page_title="LyceeAI", page_icon="🎓", layout="centered")

# --- DATABASE & AI SETUP ---
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
gemini_key = st.secrets["GEMINI_KEY"]

supabase = create_client(url, key)
genai.configure(api_key=gemini_key)

@st.cache_resource
def get_model():
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods: return m.name
    return "models/gemini-1.5-flash"

model_gemini = genai.GenerativeModel(get_model())

@st.cache_resource
def load_embed(): return SentenceTransformer('all-MiniLM-L6-v2')

# --- APP INTERFACE ---
st.title("🎓 LyceeAI")

if "messages" not in st.session_state:
    st.session_state.messages = []

# --- DEBUG TOOL (Only for you, the founder) ---
with st.sidebar:
    st.header("Founder Tools")
    if st.button("🔍 Audit Database"):
        # This pulls the first 3 rows to see what is actually inside
        test_res = supabase.table("documents").select("content").limit(3).execute()
        for i, item in enumerate(test_res.data):
            st.write(f"Chunk {i+1}:", item['content'][:200] + "...")

# Display chat
for message in st.session_state.messages:
    with st.chat_message(message["role"]): st.markdown(message["content"])

if prompt := st.chat_input("What are we studying?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Checking your lessons..."):
            # 1. SEARCH
            query_embedding = load_embed().encode(prompt).tolist()
            result = supabase.rpc("match_documents", {
                "query_embedding": query_embedding,
                "match_threshold": 0.1, # Very low to force a match
                "match_count": 3
            }).execute()
            
            context = "\n".join([f"DATA: {item['content']}" for item in result.data]) if result.data else "No data found."

            # 2. THE DYNAMIC BRAIN
            system_prompt = f"""
            You are LyceeAI Mentor. 
            RULES:
            1. Use the 'DATABASE CONTEXT' below to answer.
            2. If 'DATABASE CONTEXT' mentions specific subjects, offer to teach those.
            3. If the context is empty, ask the user to specify a topic from their curriculum.
            
            DATABASE CONTEXT:
            {context}
            """
            
            chat = model_gemini.start_chat(history=[])
            response = chat.send_message(system_prompt + "\n\nUser: " + prompt)
            st.markdown(response.text)
            st.session_state.messages.append({"role": "assistant", "content": response.text})

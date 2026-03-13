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

# SMART MODEL PICKER: This finds what YOUR key is allowed to use
@st.cache_resource
def get_available_model():
    try:
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                return m.name
        return "models/gemini-1.5-flash" # Fallback
    except:
        return "models/gemini-1.5-flash"

model_name = get_available_model()
model_gemini = genai.GenerativeModel(model_name)

@st.cache_resource
def load_embed_model():
    return SentenceTransformer('all-MiniLM-L6-v2')

embed_model = load_embed_model()

# --- APP INTERFACE ---
st.title("🎓 LyceeAI")
st.caption(f"Connected via: {model_name}")

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Ask a question about your lessons..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Searching..."):
            try:
                # 1. Search Knowledge Base
                query_embedding = load_embed_model().encode(prompt).tolist()
                result = supabase.rpc("match_documents", {
                    "query_embedding": query_embedding,
                    "match_threshold": 0.1,
                    "match_count": 2
                }).execute()

                context = ""
                if result.data:
                    context = "\n".join([f"Lesson: {item['content']}" for item in result.data])
                
                # 2. Generate Answer
                full_prompt = f"Context: {context}\n\nQuestion: {prompt}"
                response = model_gemini.generate_content(full_prompt)
                
                st.markdown(response.text)
                st.session_state.messages.append({"role": "assistant", "content": response.text})
            except Exception as e:
                st.error(f"Try one more time: {str(e)}")

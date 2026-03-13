import streamlit as st
from supabase import create_client
from sentence_transformers import SentenceTransformer
import google.generativeai as genai

# --- PAGE CONFIG ---
st.set_page_config(page_title="LyceeAI", page_icon="🎓", layout="centered")

st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; background-color: #0057B8; color: white; }
    .stTextInput>div>div>input { border-radius: 5px; }
    </style>
    """, unsafe_allow_html=True)

# --- DATABASE & AI SETUP ---
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
gemini_key = st.secrets["GEMINI_KEY"]

supabase = create_client(url, key)
genai.configure(api_key=gemini_key)

# Using the most widely compatible model name for Free Tier
model_gemini = genai.GenerativeModel('gemini-pro')

@st.cache_resource
def load_model():
    return SentenceTransformer('all-MiniLM-L6-v2')

embed_model = load_model()

# --- APP INTERFACE ---
st.title("🎓 LyceeAI")
st.caption("Advanced AI Tutor for Baccalauréat SVT")

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
        with st.spinner("Analyzing lesson data..."):
            try:
                # 1. Search Knowledge Base
                query_embedding = embed_model.encode(prompt).tolist()
                result = supabase.rpc("match_documents", {
                    "query_embedding": query_embedding,
                    "match_threshold": 0.1, # Lowest possible threshold to ensure WE GET SOMETHING
                    "match_count": 2
                }).execute()

                context = ""
                if result.data:
                    context = "\n".join([f"Lesson content: {item['content']}" for item in result.data])
                
                # 2. Generate Answer
                full_prompt = f"You are a professional SVT tutor. Use this context: {context}\n\nQuestion: {prompt}"
                response = model_gemini.generate_content(full_prompt)
                
                st.markdown(response.text)
                st.session_state.messages.append({"role": "assistant", "content": response.text})
            except Exception as e:
                # If even gemini-pro fails, we will know exactly why
                st.error(f"AI Service Alert: {str(e)}")

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
    try:
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods: return m.name
        return "models/gemini-1.5-flash"
    except: return "models/gemini-1.5-flash"

model_name = get_model()
model_gemini = genai.GenerativeModel(model_name)

@st.cache_resource
def load_embed(): return SentenceTransformer('all-MiniLM-L6-v2')

# --- FOUNDER TOOLS SIDEBAR ---
with st.sidebar:
    st.header("🛠 Founder Tools")
    
    if st.button("🔍 Quick Audit"):
        # Pulling very small snippets to save tokens
        test_res = supabase.table("documents").select("content").limit(3).execute()
        for item in test_res.data:
            st.code(item['content'][:100] + "...")
            
    if st.button("📋 Identify Subjects"):
        with st.spinner("Quick Scan..."):
            # We only pull 5 snippets now (much lighter on the API)
            sample = supabase.table("documents").select("content").limit(5).execute()
            sample_text = "\n".join([d['content'] for d in sample.data])
            try:
                # Short, simple prompt to keep tokens low
                res = model_gemini.generate_content(f"List 2-3 subjects found in this text: {sample_text}")
                st.session_state.subjects = res.text
                st.success("Detected!")
            except:
                st.warning("API still busy. Try the chat instead.")

# --- APP INTERFACE ---
st.title("🎓 LyceeAI")
if "subjects" in st.session_state:
    st.caption(f"Subjects: {st.session_state.subjects}")

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]): st.markdown(message["content"])

if prompt := st.chat_input("Ask a question..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)

    with st.chat_message("assistant"):
        try:
            # 1. SEARCH (Reduced match count to save resources)
            query_embedding = load_embed().encode(prompt).tolist()
            result = supabase.rpc("match_documents", {
                "query_embedding": query_embedding,
                "match_threshold": 0.15, 
                "match_count": 3 
            }).execute()
            
            context = ""
            if result.data:
                context = "\n".join([item['content'] for item in result.data])

            # 2. SYSTEM BRAIN (Minimalist to avoid hitting limits)
            response = model_gemini.generate_content(f"Context: {context}\n\nUser: {prompt}")
            
            st.markdown(response.text)
            st.session_state.messages.append({"role": "assistant", "content": response.text})
        except Exception as e:
            st.error("The AI is resting. Please wait 1 minute before your next question.")

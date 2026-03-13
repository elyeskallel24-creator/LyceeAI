import streamlit as st
from supabase import create_client
from sentence_transformers import SentenceTransformer
import google.generativeai as genai
import time

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

model_name = get_model()
model_gemini = genai.GenerativeModel(model_name)

@st.cache_resource
def load_embed(): return SentenceTransformer('all-MiniLM-L6-v2')

# --- FOUNDER TOOLS SIDEBAR ---
with st.sidebar:
    st.header("🛠 Founder Tools")
    st.info(f"Model: {model_name}")
    
    if st.button("🔍 Audit Data"):
        test_res = supabase.table("documents").select("content").limit(5).execute()
        for i, item in enumerate(test_res.data):
            st.text_area(f"Chunk {i+1}", item['content'][:200], height=100)
            
    if st.button("📋 Refresh Subject Map"):
        with st.spinner("Scanning database..."):
            # Pulling a diverse sample from the 7000 chunks
            sample = supabase.table("documents").select("content").limit(15).execute()
            sample_text = "\n".join([d['content'] for d in sample.data])
            try:
                res = model_gemini.generate_content(f"Analyze these snippets and list the 3 primary academic subjects found (e.g., Biology, English, etc.):\n{sample_text}")
                st.session_state.detected_subjects = res.text
                st.success("Subjects updated!")
            except Exception as e:
                st.error("API is busy. Wait 30 seconds.")

# --- APP INTERFACE ---
st.title("🎓 LyceeAI")
if "detected_subjects" in st.session_state:
    st.caption(f"Knowledge Base: {st.session_state.detected_subjects[:100]}...")

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]): st.markdown(message["content"])

if prompt := st.chat_input("Ask about your lessons..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Mentor is thinking..."):
            try:
                # 1. SEARCH
                query_embedding = load_embed().encode(prompt).tolist()
                result = supabase.rpc("match_documents", {
                    "query_embedding": query_embedding,
                    "match_threshold": 0.12, 
                    "match_count": 6 
                }).execute()
                
                context = ""
                if result.data:
                    context = "\n".join([item['content'] for item in result.data if len(item['content']) > 40])

                # 2. SYSTEM BRAIN
                system_prompt = f"""
                You are LyceeAI, a mentor for the Tunisian Baccalaureate.
                CONTEXT FROM DATABASE: {context}
                
                MISSION:
                - Use the context to teach. 
                - If the user asks for 'subjects', list the ones found in the context (like English or SVT).
                - If you can't find the answer in the context, say: 'I have 7000 chunks of data, but I couldn't find that specific detail. Can you rephrase or ask about another topic like SVT?'
                """
                
                # 3. GENERATE (With history)
                response = model_gemini.generate_content(system_prompt + "\n\nUser: " + prompt)
                
                st.markdown(response.text)
                st.session_state.messages.append({"role": "assistant", "content": response.text})
            except Exception as e:
                if "429" in str(e):
                    st.error("The API key is 'tired'. Please wait 60 seconds for the free tier to reset.")
                else:
                    st.error(f"Error: {str(e)}")

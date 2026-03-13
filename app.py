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

# --- FOUNDER TOOLS SIDEBAR ---
with st.sidebar:
    st.header("🛠 Founder Tools")
    if st.button("🔍 Audit: What's inside?"):
        # Pulling chunks to see the diversity of the 7000 files
        test_res = supabase.table("documents").select("content").limit(10).execute()
        for i, item in enumerate(test_res.data):
            st.info(f"Chunk {i+1}: {item['content'][:150]}...")
            
    if st.button("📋 List Detected Topics"):
        st.write("Asking AI to summarize the database...")
        # We pull 20 random chunks to give the AI a 'sample' of the whole drive
        sample = supabase.table("documents").select("content").limit(20).execute()
        sample_text = "\n".join([d['content'] for d in sample.data])
        res = model_gemini.generate_content(f"Based on these snippets, what are the 3 main academic subjects here? \n{sample_text}")
        st.success(res.text)

# Display chat
for message in st.session_state.messages:
    with st.chat_message(message["role"]): st.markdown(message["content"])

if prompt := st.chat_input("Ask a specific question (e.g., 'Tell me about SVT')"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Filtering Knowledge Base..."):
            # 1. SEARCH with higher count to get past the 'noise'
            query_embedding = load_embed().encode(prompt).tolist()
            result = supabase.rpc("match_documents", {
                "query_embedding": query_embedding,
                "match_threshold": 0.15, 
                "match_count": 8 # Increased to find real lessons hidden under 'noise'
            }).execute()
            
            context = ""
            if result.data:
                # We filter out very short 'noisy' chunks
                context = "\n".join([f"LESSON DATA: {item['content']}" for item in result.data if len(item['content']) > 50])

            # 2. THE MENTOR SYSTEM
            system_prompt = f"""
            You are the LyceeAI Mentor. 
            CONTEXT: {context}
            
            YOUR GOAL: 
            - Be a supportive academic tutor.
            - If the user says 'Hello', greet them and ask what academic subject (SVT, Physics, English, etc.) they want to study.
            - If the context contains grammar exercises, treat them as 'English Lessons'.
            - If the context contains Biology/SVT, treat them as 'SVT Lessons'.
            - IMPORTANT: If you don't find a topic, ask the user: 'Which specific chapter from your 7000 lessons should we open today?'
            """
            
            chat = model_gemini.start_chat(history=[])
            response = chat.send_message(system_prompt + "\n\nUser: " + prompt)
            st.markdown(response.text)
            st.session_state.messages.append({"role": "assistant", "content": response.text})

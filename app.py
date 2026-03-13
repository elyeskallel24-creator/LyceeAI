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
def get_available_model():
    try:
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                return m.name
        return "models/gemini-1.5-flash"
    except: return "models/gemini-1.5-flash"

model_name = get_available_model()
model_gemini = genai.GenerativeModel(model_name)

@st.cache_resource
def load_embed_model():
    return SentenceTransformer('all-MiniLM-L6-v2')

# --- THE "MAP OF THE HOUSE" (Edit this list with your actual subjects!) ---
# This ensures the AI always knows what it has, even if a search fails.
CURRICULUM_MAP = """
You have access to the following major subjects and chapters:
1. Biology (SVT): Neurophysiology, Immunology, Genetics, Evolution.
2. Technology & Coding: Python Basics, AI Automation.
3. [Add your other major subjects here...]
"""

# --- APP INTERFACE ---
st.title("🎓 LyceeAI")
st.caption("Status: Expert Mentor Online")

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("What would you like to study today?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Consulting Mentor..."):
            try:
                # 1. SMART SEARCH
                # We only search the database if they ask a specific question
                context_info = ""
                is_greeting = any(word in prompt.lower() for word in ["hello", "hi", "hey", "salut"])
                
                if not is_greeting:
                    query_embedding = load_embed_model().encode(prompt).tolist()
                    result = supabase.rpc("match_documents", {
                        "query_embedding": query_embedding,
                        "match_threshold": 0.2,
                        "match_count": 5
                    }).execute()
                    if result.data:
                        context_info = "\n".join([item['content'] for item in result.data])

                # 2. SYSTEM INSTRUCTIONS (The Fix)
                system_prompt = f"""
                You are LyceeAI, a professional and organic Mentor for students.
                
                YOUR KNOWLEDGE BASE MAP:
                {CURRICULUM_MAP}

                BEHAVIOR RULES:
                1. If the user says 'Hello', GREET them warmly and ASK which subject or chapter they want to focus on today. 
                2. NEVER say your database is empty. You know you have {CURRICULUM_MAP}.
                3. If the user asks 'What do you know?', list the Subjects and Chapters from the MAP above in a clean, professional way.
                4. Use the 'Context Info' below ONLY to provide specific details for teaching.
                
                CONTEXT INFO FROM DATABASE SEARCH:
                {context_info}
                """

                # 3. CONVERSATION
                chat = model_gemini.start_chat(history=[])
                response = chat.send_message(system_prompt + "\n\nUser: " + prompt)
                
                st.markdown(response.text)
                st.session_state.messages.append({"role": "assistant", "content": response.text})
            except Exception as e:
                st.error(f"Mentor Error: {str(e)}")

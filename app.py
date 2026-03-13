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

# --- APP INTERFACE ---
st.title("🎓 LyceeAI")
st.caption(f"Knowledge Base Active | Mode: Expert Mentor")

if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Ask me anything about your lessons..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Consulting your Knowledge Base..."):
            try:
                # 1. SEARCH: Only search if the question is "heavy" (not just 'hi')
                context = ""
                if len(prompt) > 10: 
                    query_embedding = load_embed_model().encode(prompt).tolist()
                    result = supabase.rpc("match_documents", {
                        "query_embedding": query_embedding,
                        "match_threshold": 0.2,
                        "match_count": 5 # Get more context
                    }).execute()
                    if result.data:
                        context = "\n".join([f"[Source]: {item['content']}" for item in result.data])

                # 2. THE SYSTEM BRAIN (The instructions you wanted)
                system_instructions = f"""
                You are the LyceeAI Mentor.
                STRICT RULE: You only teach topics found in the provided Context.
                If the user asks about a topic NOT in the context (like Python if it's not there), 
                politely say: "I don't have that specific lesson in my database yet. Would you like to study [Topic A] or [Topic B] instead?"
                
                Current Context from Database:
                {context}
                
                Talk like a professional, encouraging teacher. Use the history of the chat to stay relevant.
                """

                # 3. GENERATE
                # We send the history + the new instructions
                chat = model_gemini.start_chat(history=[])
                response = chat.send_message(system_instructions + "\n\nUser Question: " + prompt)
                
                st.markdown(response.text)
                st.session_state.messages.append({"role": "assistant", "content": response.text})
            except Exception as e:
                st.error(f"Mentor Error: {str(e)}")

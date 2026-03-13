import streamlit as st
from supabase import create_client
from sentence_transformers import SentenceTransformer
import requests
import json
import time

# --- LUXURY PAGE CONFIG ---
st.set_page_config(page_title="LyceeAI | Enterprise", page_icon="🎓", layout="centered")

# --- CUSTOM CORPORATE STYLING ---
st.markdown("""
    <style>
        /* Main Background */
        .stApp {
            background-color: #0E1117;
        }
        
        /* Sidebar Styling */
        [data-testid="stSidebar"] {
            background-color: #161B22;
            border-right: 1px solid #30363D;
        }
        
        /* Chat Input Styling */
        .stChatInputContainer {
            padding-bottom: 20px;
        }
        
        /* Header Logo/Text */
        .founder-header {
            font-family: 'Inter', sans-serif;
            color: #58A6FF;
            font-weight: 700;
            font-size: 1.2rem;
            margin-bottom: 20px;
        }
        
        /* Remove Streamlit branding */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        
        /* Custom Button */
        .stButton>button {
            width: 100%;
            border-radius: 5px;
            background-color: #21262D;
            color: #C9D1D9;
            border: 1px solid #30363D;
        }
        .stButton>button:hover {
            border-color: #58A6FF;
            color: #58A6FF;
        }
    </style>
""", unsafe_allow_html=True)

# --- DATABASE & AI SETUP ---
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
openrouter_key = st.secrets["OPENROUTER_API_KEY"]

supabase = create_client(url, key)

@st.cache_resource
def load_embed():
    return SentenceTransformer('all-MiniLM-L6-v2')

def ask_openrouter(messages):
    endpoint = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {openrouter_key}",
        "HTTP-Referer": "https://lyceeai.streamlit.app", 
        "Content-Type": "application/json"
    }
    data = {
        "model": "openrouter/auto",
        "messages": messages,
        "temperature": 0.4
    }
    for attempt in range(2):
        try:
            response = requests.post(endpoint, headers=headers, data=json.dumps(data), timeout=45)
            if response.status_code == 200:
                return response.json()['choices'][0]['message']['content']
            time.sleep(1)
        except:
            continue
    return "High demand detected. Re-sending your request..."

# --- SIDEBAR (Luxury Dashboard) ---
with st.sidebar:
    st.markdown('<div class="founder-header">LYCEEAI FOUNDER</div>', unsafe_allow_html=True)
    st.success("SYSTEM: ONLINE")
    
    st.divider()
    
    if st.button("🔍 AUDIT DATA"):
        res = supabase.table("documents").select("content").limit(1).execute()
        for item in res.data:
            st.caption(f"SYNCED: {item['content'][:100]}...")
            
    if st.button("🗑 RESET SESSION"):
        st.session_state.messages = []
        st.rerun()
    
    st.divider()
    st.markdown("### Support Team\n- Raven\n- Clo\n- Hannibal")

# --- APP INTERFACE ---
st.title("🎓 LyceeAI")
st.markdown("---")

if "messages" not in st.session_state:
    st.session_state.messages = []

# Display conversation
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Enter your query..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Processing Knowledge..."):
            try:
                # 1. SEARCH
                query_vec = load_embed().encode(prompt).tolist()
                result = supabase.rpc("match_documents", {
                    "query_embedding": query_vec,
                    "match_threshold": 0.05, 
                    "match_count": 3 
                }).execute()
                
                context = "\n".join([item['content'] for item in result.data]) if result.data else "General academic knowledge."

                # 2. SYSTEM
                system_msg = f"You are LyceeAI, an elite mentor for the Tunisian Baccalaureate. Use context: {context}. Be concise and professional."
                
                chat_history = [{"role": "system", "content": system_msg}]
                for msg in st.session_state.messages[-3:]:
                    chat_history.append(msg)
                
                # 3. GENERATE
                response_text = ask_openrouter(chat_history)
                
                st.markdown(response_text)
                st.session_state.messages.append({"role": "assistant", "content": response_text})
                
            except Exception as e:
                st.error("System Refresh. Re-submit your query.")

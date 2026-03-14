import streamlit as st
from supabase import create_client
from sentence_transformers import SentenceTransformer
import requests
import json
import time

# --- PAGE CONFIG ---
st.set_page_config(page_title="LyceeAI", page_icon="🎓", layout="wide")

# --- DB & AI SETUP ---
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
openrouter_key = st.secrets["OPENROUTER_API_KEY"]
supabase = create_client(url, key)

@st.cache_resource
def load_embed():
    return SentenceTransformer('all-MiniLM-L6-v2')

def ask_openrouter(messages):
    endpoint = "https://openrouter.ai/api/v1/chat/completions"
    headers = {"Authorization": f"Bearer {openrouter_key}", "Content-Type": "application/json"}
    data = {"model": "openrouter/auto", "messages": messages, "temperature": 0.4}
    try:
        res = requests.post(endpoint, headers=headers, data=json.dumps(data), timeout=30)
        return res.json()['choices'][0]['message']['content']
    except:
        return "System is busy. Please try again."

# --- AUTH LOGIC ---
if "user" not in st.session_state:
    st.session_state.user = None

def signup():
    st.subheader("📝 Créer un compte")
    new_user = st.text_input("Nom d'utilisateur (3-15 chars)", key="reg_user")
    new_pass = st.text_input("Mot de passe (min 8 chars)", type="password", key="reg_pass")
    confirm_pass = st.text_input("Confirmez le mot de passe", type="password", key="reg_confirm")
    
    if st.button("S'inscrire"):
        if 3 <= len(new_user) <= 15 and len(new_pass) >= 8 and new_pass == confirm_pass:
            # Check if user exists
            exists = supabase.table("users_profile").select("*").eq("username", new_user).execute()
            if exists.data:
                st.error("Nom d'utilisateur déjà pris.")
            else:
                st.session_state.temp_user = {"username": new_user, "password": new_pass}
                st.session_state.step = "onboarding"
                st.rerun()
        else:
            st.error("Veuillez vérifier vos informations.")

def login():
    st.subheader("🔑 Se connecter")
    user = st.text_input("Nom d'utilisateur", key="log_user")
    pwd = st.text_input("Mot de passe", type="password", key="log_pass")
    if st.button("Se connecter"):
        res = supabase.table("users_profile").select("*").eq("username", user).eq("password", pwd).execute()
        if res.data:
            st.session_state.user = res.data[0]
            st.rerun()
        else:
            st.error("Identifiants incorrects.")

# --- ONBOARDING (Level/Section/Method) ---
def onboarding():
    st.header("🎯 Personnalisez votre expérience")
    level = st.selectbox("Choisissez votre niveau", ["1ère année secondaire", "2ème année (Coming Soon)", "3ème année (Coming Soon)", "4ème année (Baccalauréat)"])
    
    if "1ère" in level:
        section = st.radio("Section", ["Générale", "Sport"])
    elif "Baccalauréat" in level:
        section = st.radio("Section", ["Mathématiques", "Sciences Exp", "Économie", "Technique", "Lettre", "Sport", "Informatique"])
    else:
        st.warning("Ce niveau sera bientôt disponible.")
        st.stop()

    method = st.text_area("Comment voulez-vous apprendre ? (Ex: Méthode active, résumés, exercices...)", min_chars=80, max_chars=150)
    
    if st.button("Finaliser"):
        user_data = {
            **st.session_state.temp_user,
            "level": level,
            "section": section,
            "teaching_method": method
        }
        supabase.table("users_profile").insert(user_data).execute()
        st.session_state.user = user_data
        st.session_state.step = "chat"
        st.rerun()

# --- MAIN APP ROUTING ---
if st.session_state.user is None:
    tab1, tab2 = st.tabs(["Se connecter", "S'inscrire"])
    with tab1: login()
    with tab2: signup()
    if "step" in st.session_state and st.session_state.step == "onboarding":
        st.divider()
        onboarding()
else:
    # --- SIDEBAR (SAME DESIGN) ---
    with st.sidebar:
        st.header("🛠 Founder Tools")
        st.info(f"Élève: {st.session_state.user['username']}")
        st.write(f"Niveau: {st.session_state.user['level']}")
        st.write(f"Section: {st.session_state.user['section']}")
        if st.button("🗑 Clear My Chat"):
            st.session_state.messages = []
            st.rerun()
        if st.button("🚪 Déconnexion"):
            st.session_state.user = None
            st.rerun()

    # --- CHAT INTERFACE ---
    st.title(f"🎓 LyceeAI - {st.session_state.user['level']}")
    
    if "messages" not in st.session_state: st.session_state.messages = []
    for m in st.session_state.messages:
        with st.chat_message(m["role"]): st.markdown(m["content"])

    if prompt := st.chat_input("Posez une question sur vos cours..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Consultation des livres officiels..."):
                # Search filtered by user's Level and Section
                query_vec = load_embed().encode(prompt).tolist()
                result = supabase.rpc("match_documents", {
                    "query_embedding": query_vec,
                    "match_threshold": 0.1,
                    "match_count": 5,
                    "filter_level": st.session_state.user['level'],
                    "filter_section": st.session_state.user['section']
                }).execute()
                
                context = "\n".join([item['content'] for item in result.data])
                method = st.session_state.user['teaching_method']
                
                sys_msg = f"Tu es LyceeAI. L'élève est en {st.session_state.user['level']}, section {st.session_state.user['section']}. Sa méthode préférée: {method}. Utilise ce contexte: {context}"
                
                history = [{"role": "system", "content": sys_msg}] + st.session_state.messages[-4:]
                response = ask_openrouter(history)
                st.markdown(response)
                st.session_state.messages.append({"role": "assistant", "content": response})

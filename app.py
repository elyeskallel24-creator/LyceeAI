import streamlit as st
from supabase import create_client
from sentence_transformers import SentenceTransformer
import requests
import json
import time
from io import BytesIO
import pypdf

# --- PAGE CONFIG ---
st.set_page_config(page_title="LyceeAI", page_icon="🎓", layout="wide")

# --- LUXURY CSS ---
st.markdown("""
<style>
    .stApp { background-color: #f8f9fa; }
    .main { background: white; border-radius: 20px; padding: 20px; }
    div.stButton > button {
        border-radius: 10px; border: none; 
        background-color: #007bff; color: white;
        font-weight: bold; width: 100%; transition: 0.3s;
    }
    div.stButton > button:hover { background-color: #0056b3; transform: translateY(-2px); }
    .stTextInput > div > div > input { border-radius: 10px; }
    .sidebar .sidebar-content { background-image: linear-gradient(#2e3192, #1bffff); color: white; }
</style>
""", unsafe_allow_html=True)

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
        return "Système occupé. Réessayez dans 5 secondes."

# --- AUTH STATE ---
if "user" not in st.session_state: st.session_state.user = None
if "step" not in st.session_state: st.session_state.step = "auth"

# --- LOGIN/SIGNUP UI ---
def auth_screen():
    st.title("🎓 LyceeAI")
    st.caption("La plateforme d'élite pour le Baccalauréat Tunisien")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        tab1, tab2 = st.tabs(["🔒 Connexion", "📝 Inscription"])
        with tab1:
            u = st.text_input("Nom d'utilisateur", key="l_u")
            p = st.text_input("Mot de passe", type="password", key="l_p")
            if st.button("Se connecter"):
                res = supabase.table("users_profile").select("*").eq("username", u).eq("password", p).execute()
                if res.data:
                    st.session_state.user = res.data[0]
                    st.session_state.step = "chat"
                    st.rerun()
                else: st.error("Utilisateur ou mot de passe incorrect.")
        
        with tab2:
            nu = st.text_input("Choisir un nom d'utilisateur", key="s_u")
            np = st.text_input("Créer un mot de passe", type="password", key="s_p")
            cp = st.text_input("Confirmer le mot de passe", type="password", key="s_c")
            if st.button("Créer mon compte"):
                if 3<=len(nu)<=15 and len(np)>=8 and np==cp:
                    st.session_state.temp_user = {"username": nu, "password": np}
                    st.session_state.step = "onboarding"
                    st.rerun()
                else: st.error("Critères: Nom (3-15 chars), Pass (8+ chars).")

# --- ONBOARDING ---
def onboarding():
    st.header("🎯 Configuration de votre profil")
    level = st.selectbox("Niveau", ["1ère année secondaire", "4ème année (Baccalauréat)"])
    if "1ère" in level:
        section = st.radio("Section", ["Générale", "Sport"])
    else:
        section = st.radio("Section", ["Mathématiques", "Sciences Exp", "Économie", "Technique", "Lettre", "Sport", "Informatique"])
    
    st.write("Méthode d'apprentissage (80-150 caractères)")
    method = st.text_area("Ex: Je préfère des explications simplifiées avec des mots-clés en arabe pour les concepts complexes.", height=150)
    
    if st.button("Lancer LyceeAI"):
        if 80 <= len(method) <= 150:
            user_data = {**st.session_state.temp_user, "level": level, "section": section, "teaching_method": method}
            supabase.table("users_profile").insert(user_data).execute()
            st.session_state.user = user_data
            st.session_state.step = "chat"
            st.rerun()
        else: st.warning(f"Actuellement {len(method)} caractères. Il en faut entre 80 et 150.")

# --- ADMIN UPLOADER ---
def admin_tool():
    st.divider()
    st.subheader("🚀 Founder Library")
    up_lvl = st.selectbox("Niveau", ["1ère année secondaire", "4ème année (Baccalauréat)"], key="up_lvl")
    up_sec = st.text_input("Section exacte (Ex: Mathématiques)", key="up_sec")
    up_subj = st.text_input("Matière", key="up_subj")
    f = st.file_uploader("Fichier PDF", type="pdf")
    if f and st.button("Injecter"):
        with st.spinner("Traitement..."):
            reader = pypdf.PdfReader(BytesIO(f.read()))
            model = load_embed()
            for page in reader.pages:
                txt = page.extract_text()
                if len(txt) > 100:
                    vec = model.encode(txt).tolist()
                    supabase.table("documents").insert({
                        "content": txt, "embedding": vec,
                        "metadata": {"level": up_lvl, "section": up_sec, "subject": up_subj}
                    }).execute()
            st.success("Livre ajouté!")

# --- APP ROUTING ---
if st.session_state.step == "auth": auth_screen()
elif st.session_state.step == "onboarding": onboarding()
else:
    # --- CHAT & SIDEBAR ---
    with st.sidebar:
        st.title("🛠 LyceeAI Admin")
        st.success(f"Connecté: {st.session_state.user['username']}")
        st.write(f"Niveau: {st.session_state.user['level']}")
        if st.button("🗑 Vider le chat"):
            st.session_state.messages = []
            st.rerun()
        if st.button("🚪 Déconnexion"):
            st.session_state.user = None
            st.session_state.step = "auth"
            st.rerun()
        admin_tool()

    st.title(f"🎓 Dashboard - {st.session_state.user['level']}")
    if "messages" not in st.session_state: st.session_state.messages = []
    for m in st.session_state.messages:
        with st.chat_message(m["role"]): st.markdown(m["content"])

    if prompt := st.chat_input("Posez votre question..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Consultation de la bibliothèque..."):
                q_vec = load_embed().encode(prompt).tolist()
                result = supabase.rpc("match_documents", {
                    "query_embedding": q_vec, "match_threshold": 0.1, "match_count": 6,
                    "filter_level": st.session_state.user['level'],
                    "filter_section": st.session_state.user['section']
                }).execute()
                
                context = "\n".join([i['content'] for i in result.data]) if result.data else "Pas de contexte."
                sys_msg = f"Tu es LyceeAI. Élève: {st.session_state.user['level']} {st.session_state.user['section']}. Méthode: {st.session_state.user['teaching_method']}. Contexte: {context}"
                res = ask_openrouter([{"role": "system", "content": sys_msg}] + st.session_state.messages[-4:])
                st.markdown(res)
                st.session_state.messages.append({"role": "assistant", "content": res})

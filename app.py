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

# --- AUTH STATE --- 
if "user" not in st.session_state: 
    st.session_state.user = None 
if "step" not in st.session_state: 
    st.session_state.step = "auth" 

# --- ONBOARDING --- 
def onboarding(): 
    st.header("🎯 Personnalisez votre expérience") 
    level = st.selectbox("Choisissez votre niveau", ["1ère année secondaire", "4ème année (Baccalauréat)"]) 
    
    if "1ère" in level: 
        section = st.radio("Section", ["Générale", "Sport"]) 
    else: 
        section = st.radio("Section", ["Mathématiques", "Sciences Exp", "Économie", "Technique", "Lettre", "Sport", "Informatique"]) 

    st.write("Décrivez votre méthode d'apprentissage (80-150 caractères)") 
    method = st.text_area("Ex: Je veux des résumés courts suivis d'exercices d'application directs.", help="Soyez précis.") 
    
    char_count = len(method) 
    st.caption(f"Caractères: {char_count}/150") 

    if st.button("Finaliser l'inscription"): 
        if 80 <= char_count <= 150: 
            user_data = { 
                "username": st.session_state.temp_user["username"], 
                "password": st.session_state.temp_user["password"], 
                "level": level, 
                "section": section, 
                "teaching_method": method 
            } 
            try: 
                supabase.table("users_profile").insert(user_data).execute() 
                st.session_state.user = user_data 
                st.session_state.step = "chat" 
                st.success("Compte créé !") 
                st.rerun() 
            except Exception as e: 
                st.error(f"Erreur: {e}") 
        else: 
            st.warning(f"Description trop courte ou trop longue ({char_count}).") 

# --- UPLOADER --- 
def admin_uploader(): 
    st.divider() 
    st.subheader("📤 Bibliothèque Master") 
    up_level = st.selectbox("Niveau", ["1ère année secondaire", "4ème année (Baccalauréat)"], key="up_lvl") 
    up_sec = st.text_input("Section", key="up_sec") 
    up_subj = st.text_input("Matière", key="up_subj") 
    uploaded_file = st.file_uploader("PDF", type="pdf") 
    
    if uploaded_file and st.button("Injecter"): 
        with st.spinner("Processing..."): 
            reader = pypdf.PdfReader(BytesIO(uploaded_file.read())) 
            embed_model = load_embed() 
            for i, page in enumerate(reader.pages): 
                text = page.extract_text() 
                if len(text.strip()) > 100: 
                    vector = embed_model.encode(text).tolist() 
                    supabase.table("documents").insert({ 
                        "content": text, 
                        "metadata": {"level": up_level, "section": up_sec, "subject": up_subj}, 
                        "embedding": vector 
                    }).execute() 
            st.success("Terminé !") 

# --- AUTH UI --- 
def auth_screen(): 
    tab1, tab2 = st.tabs(["Se connecter", "S'inscrire"]) 
    with tab1: 
        u = st.text_input("Utilisateur", key="l_u") 
        p = st.text_input("Password", type="password", key="l_p") 
        if st.button("Entrer"): 
            res = supabase.table("users_profile").select("*").eq("username", u).eq("password", p).execute() 
            if res.data: 
                st.session_state.user = res.data[0] 
                chat_res = supabase.table("chat_history").select("*").eq("username", u).order("created_at").execute() 
                st.session_state.messages = [{"role": m["role"], "content": m["content"]} for m in chat_res.data] 
                st.session_state.step = "chat" 
                st.rerun() 
            else: st.error("Inconnu.") 
    with tab2: 
        nu = st.text_input("Nouvel Utilisateur", key="s_u") 
        np = st.text_input("Nouveau Password", type="password", key="s_p") 
        cp = st.text_input("Confirmer", type="password", key="s_c") 
        if st.button("Créer"): 
            if 3<=len(nu)<=15 and len(np)>=8 and np==cp: 
                st.session_state.temp_user = {"username": nu, "password": np} 
                st.session_state.step = "onboarding" 
                st.rerun() 
            else: st.error("Invalide.") 

# --- MAIN APP LOGIC --- 
if st.session_state.step == "auth": 
    auth_screen() 
elif st.session_state.step == "onboarding": 
    onboarding() 
else: 
# --- SIDEBAR START --- 
    with st.sidebar: 
        # 1. TOP SECTION 
        st.markdown(f"### 🌶️ Aslema **{st.session_state.user['username']}** !") 
        
        if st.session_state.user['username'] == "elyes": 
            st.divider() 
            st.header("🛠 Founder Tools") 
            if st.button("🗑 Clear Chat"): 
                st.session_state.messages = [] 
                st.rerun() 
            admin_uploader() 

        # 2. THE SPACER 
        # This allows the top content to be scrollable while the footer stays pinned.
        st.container(height=400, border=False) 

        # 3. FIXED FOOTER SECTION
        st.markdown("""
            <style>
                [data-testid="stSidebarUserContent"] {
                    display: flex;
                    flex-direction: column;
                    height: 100vh;
                }
                .stButton {
                    margin-top: auto;
                }
            </style>
        """, unsafe_allow_html=True)

        st.divider()  
        if st.button("🚪 Déconnexion", use_container_width=True): 
            st.session_state.user = None 
            st.session_state.messages = [] 
            st.session_state.step = "auth" 
            st.rerun() 
        
        # Updated Branding Tag
        st.caption("LyceeAI v1.0 | Quantara-SPMAT") 
# --- SIDEBAR END --- 

    st.title("🎓 LyceeAI") 
    if "messages" not in st.session_state: st.session_state.messages = [] 
    
    # Show history 
    for m in st.session_state.messages: 
        with st.chat_message(m["role"]): st.markdown(m["content"]) 

    # Chat Input 
    if prompt := st.chat_input("Posez une question..."): 
        st.session_state.messages.append({"role": "user", "content": prompt}) 
        supabase.table("chat_history").insert({"username": st.session_state.user["username"], "role": "user", "content": prompt}).execute() 
        with st.chat_message("user"): st.markdown(prompt) 

        with st.chat_message("assistant"): 
            with st.spinner("Recherche..."): 
                try: 
                    q_vec = load_embed().encode(prompt).tolist() 
                    rpc_params = { 
                        "query_embedding": q_vec, 
                        "match_threshold": 0.1, 
                        "match_count": 5, 
                        "filter_level": str(st.session_state.user['level']), 
                        "filter_section": str(st.session_state.user['section']) 
                    } 
                    result = supabase.rpc("match_documents", rpc_params).execute() 

                    context = "\n".join([item['retrieved_content'] for item in result.data]) if result.data else "Pas de contexte." 
                    
                    sys_msg = f"Tu es LyceeAI. Élève: {st.session_state.user['level']}. Méthode: {st.session_state.user['teaching_method']}. Contexte: {context}" 
                    history = [{"role": "system", "content": sys_msg}] + st.session_state.messages[-4:] 
                    
                    res_text = ask_openrouter(history) 
                    st.markdown(res_text) 
                    st.session_state.messages.append({"role": "assistant", "content": res_text}) 

                    supabase.table("chat_history").insert({"username": st.session_state.user["username"], "role": "assistant", "content": res_text}).execute() 
                except Exception as e: 
                    st.error(f"Erreur: {e}")

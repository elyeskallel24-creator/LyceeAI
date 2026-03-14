import streamlit as st
from supabase import create_client
import re
import requests
import json
import time
from sentence_transformers import SentenceTransformer

# --- 1. CONFIG & STYLING ---
st.set_page_config(page_title="LyceeAI", page_icon="🎓", layout="centered")

# Custom CSS for the "Luxury" Feel (Gaussian Blur & Red/Green States)
st.markdown("""
<style>
    .stApp {
        background-color: #0E1117;
    }
    .main-logo {
        font-size: 50px;
        font-weight: 800;
        text-align: center;
        color: #FFFFFF;
        margin-bottom: 30px;
        letter-spacing: -2px;
    }
    div[data-testid="stForm"] {
        border: 1px solid #30363d;
        border-radius: 15px;
        background-color: rgba(22, 27, 34, 0.8);
        backdrop-filter: blur(10px);
    }
</style>
""", unsafe_allow_html=True)

# --- 2. DATABASE SETUP ---
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

@st.cache_resource
def load_embed():
    return SentenceTransformer('all-MiniLM-L6-v2')

# --- 3. AUTHENTICATION LOGIC ---
def sign_up_user(username, password):
    try:
        # Check if user exists
        check = supabase.table("users").select("*").eq("username", username).execute()
        if len(check.data) > 0:
            return False, "Ce nom d'utilisateur est déjà pris."
        
        # Insert new user
        supabase.table("users").insert({"username": username, "password": password}).execute()
        return True, "Success"
    except Exception as e:
        return False, str(e)

def login_user(username, password):
    res = supabase.table("users").select("*").eq("username", username).eq("password", password).execute()
    return len(res.data) > 0

# --- 4. THE LANDING PAGE (Logo + 2 Buttons) ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "page" not in st.session_state:
    st.session_state.page = "landing"

if not st.session_state.authenticated:
    st.markdown('<div class="main-logo">LyceeAI</div>', unsafe_allow_html=True)
    
    if st.session_state.page == "landing":
        col1, col2 = st.columns(2)
        with col1:
            if st.button("S’inscrire", use_container_width=True):
                st.session_state.page = "signup"
                st.rerun()
        with col2:
            if st.button("Se connecter", use_container_width=True):
                st.session_state.page = "login"
                st.rerun()

    # --- SIGN UP MODAL LOGIC ---
    elif st.session_state.page == "signup":
        with st.form("signup_form"):
            st.subheader("Créer un compte")
            
            # 1. Username
            u_name = st.text_input("nom d'utilisateur", placeholder="entrez votre nom d'utilisateur...")
            u_valid = len(u_name) >= 3 and len(u_name) <= 15
            
            # 2. Password
            pwd = st.text_input("mot de passe", type="password", placeholder="entrez votre mot de passe...")
            pwd_valid = len(pwd) >= 8 and any(c.isdigit() for c in pwd) and any(c.isupper() for c in pwd) and any(c.islower() for c in pwd)
            
            # 3. Confirm Password
            pwd_conf = st.text_input("réécrivez votre mot de passe", type="password", placeholder="doit être identique à celui saisi ci-dessus...")
            conf_valid = (pwd == pwd_conf) and (len(pwd_conf) > 0)
            
            submit = st.form_submit_button("S’inscrire", use_container_width=True)
            
            if submit:
                errors = 0
                if not u_valid:
                    st.error("le nom d'utilisateur doit comporter au moins 3 caractères et au maximum 15 caractères")
                    errors += 1
                if not pwd_valid:
                    st.error("8 caractères minimum, des lettres majuscules et minuscules, contient des chiffres.")
                    errors += 1
                if not conf_valid:
                    st.error("les mots de passe doivent être identiques")
                    errors += 1
                
                if errors == 0:
                    success, msg = sign_up_user(u_name, pwd)
                    if success:
                        st.success("Compte créé ! Connectez-vous maintenant.")
                        time.sleep(1)
                        st.session_state.page = "login"
                        st.rerun()
                    else:
                        st.error(msg)
        
        if st.button("← Retour"):
            st.session_state.page = "landing"
            st.rerun()

    # --- LOGIN PAGE ---
    elif st.session_state.page == "login":
        with st.form("login_form"):
            st.subheader("Se connecter")
            u_login = st.text_input("nom d'utilisateur")
            p_login = st.text_input("mot de passe", type="password")
            if st.form_submit_button("Connexion"):
                if login_user(u_login, p_login):
                    st.session_state.authenticated = True
                    st.rerun()
                else:
                    st.error("Identifiants incorrects")
        if st.button("← Retour"):
            st.session_state.page = "landing"
            st.rerun()

# --- 5. THE CHAT APP (Only visible after login) ---
else:
    # [PASTE YOUR WORKING CHAT CODE HERE STARTING FROM THE SIDEBAR]
    with st.sidebar:
        st.header("🛠 Founder Tools")
        if st.button("Log Out"):
            st.session_state.authenticated = False
            st.rerun()
        st.divider()
        if st.button("🗑 Clear My Chat"):
            st.session_state.messages = []
            st.rerun()

    st.title("🎓 LyceeAI Chat")
    # ... Rest of your chat code (OpenRouter call, vector search, etc.) ...

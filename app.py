import streamlit as st 
from supabase import create_client 
from sentence_transformers import SentenceTransformer 
import requests 
import json 
import time 
from io import BytesIO 
import pypdf
import uuid
import json

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
if "page" not in st.session_state:
    st.session_state.page = "dashboard"

# --- DIAGNOSTIC ENGINE ---
def diagnostic_survey():
    st.markdown("<h2 style='text-align: center;'>🧠 Diagnostic Haute Performance</h2>", unsafe_allow_html=True)
    
    if "diag_step" not in st.session_state:
        st.session_state.diag_step = 1
        st.session_state.diag_answers = []
        st.session_state.user_gender = None 
        st.session_state.user_lang = None

    total_questions = 35 
    progress = st.session_state.diag_step / total_questions
    st.progress(progress, text=f"Analyse en cours : Étape {st.session_state.diag_step} sur {total_questions}")

    # --- STEP 1: GENDER SELECTION ---
    if st.session_state.diag_step == 1:
        st.subheader("Choisissez votre forme d'adresse")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Masculin", use_container_width=True):
                st.session_state.user_gender = "male"
                st.session_state.diag_step += 1
                st.rerun()
        with col2:
            if st.button("Féminin", use_container_width=True):
                st.session_state.user_gender = "female"
                st.session_state.diag_step += 1
                st.rerun()

    # --- STEP 2: LANGUAGE SELECTION ---
    elif st.session_state.diag_step == 2:
        st.subheader("Langue de l'audit / لغة التدقيق")
        lang = st.selectbox("Langue préférée", ["Français", "العربية", "English"])
        if st.button("Confirmer / تأكيد", use_container_width=True):
            st.session_state.user_lang = lang
            st.session_state.diag_step += 1
            st.rerun()

    # --- STEP 3: DEADLINE / END GOAL (MANDATORY) ---
    elif st.session_state.diag_step == 3:
        labels = {
            "Français": "Quelle est la date précise de votre objectif final (examen) ?",
            "العربية": "ما هو التاريخ المحدد لهدفك النهائي (الامتحان)؟",
            "English": "What is the exact date of your final goal (exam)?"
        }
        st.subheader(labels.get(st.session_state.user_lang, labels["English"]))
        deadline = st.date_input("Date")
        if st.button("Valider la date", use_container_width=True):
            st.session_state.diag_answers.append({"q": "Deadline", "a": str(deadline)})
            st.session_state.diag_step += 1
            st.rerun()

    # --- STEP 4+: DYNAMIC AI QUESTIONS ---
    else:
        if f"q_{st.session_state.diag_step}" not in st.session_state:
            lang_instruction = {
                "Françcais": "Répondez uniquement en Français. Soyez direct et professionnel.",
                "العربية": "أجب باللغة العربية فقط. كن مباشراً ومهنياً.",
                "English": "Respond only in English. Be direct and professional."
            }
            # 1. Prepare structured history for the AI
            audit_log = ""
            for i, ans in enumerate(st.session_state.diag_answers):
                audit_log += f"[{i+1}] Q: {ans['q']} | A: {ans['a']}\n"

            # 2. Define the "Master Plan" categories for the AI to fulfill
            # This ensures the answers are coordinated for the future planning algorithm
            strategic_goals = """
            - DOMAIN 1: Cognitive Load (How much can they study before burnout?)
            - DOMAIN 2: Environment & Friction (Phone distractions, noise, tools)
            - DOMAIN 3: Subject Hierarchy (Specific weak points in their section)
            - DOMAIN 4: Chronotype (When is their brain most 'lethal' for math vs. memorization?)
            - DOMAIN 5: Motivation/Psychology (Why do they want this? Fear or Ambition?)
            """

            context_prompt = [
                {
                    "role": "system", 
                    "content": (
                        f"You are the Elite Academic Architect for LyceeAI. "
                        f"User Level: {st.session_state.temp_user_profile_data['level']} | Section: {st.session_state.temp_user_profile_data['section']}. "
                        f"Language: {st.session_state.user_lang}. {lang_instruction.get(st.session_state.user_lang)} "
                        "\n--- MISSION ---"
                        "Interrogates the student directly to build their 40-day revision plan. "
                        "You are talking TO the student, not ABOUT the student. Use 'Tu' (French), 'You' (English), or direct address (Arabic)."
                        "\n--- STRATEGIC DOMAINS ---"
                        f"{strategic_goals}"
                        "\n--- AUDIT RULES ---"
                        "1. DIRECT ADDRESS: Always use second-person phrasing (e.g., 'How many hours can YOU study?' NOT 'How many hours can the student study?'). "
                        "2. ANTI-HYPERFIXATION: If the last 2 questions were about the same subject (e.g., Math), you MUST pivot to a different Domain (e.g., Environment, Chronotype, Psychology, or anything that helps you build a superb plan). "
                        "3. NO REPETITION: Check the Audit Log. If you already know about their environment, move to Chronotype. "
                        "4. DRILL DOWN: If the last answer was vague, ask a follow-up to get COORDINATED data. "
                        "5. NO FLUFF: No greetings. Just the question. "
                        "6. FORMAT: Short, sharp, and high-impact. "
                        f"\n--- AUDIT LOG (PAST DATA) ---\n{audit_log}"
                    )
                },
                {
                    "role": "user",
                    "content": "Based on the log, what is the next most critical piece of data needed to build their 40-day plan?"
                }
            ]
            
            # Generate question
            raw_q = ask_openrouter(context_prompt)
            clean_q = raw_q.replace("Question:", "").replace("Audit:", "").strip()
            st.session_state[f"q_{st.session_state.diag_step}"] = clean_q

        # --- UI DISPLAY (Remains mostly the same) ---
        with st.container(border=True):
            st.subheader(st.session_state[f"q_{st.session_state.diag_step}"])
            user_ans = st.text_area("Réponse...", key=f"ans_{st.session_state.diag_step}", placeholder="Tapez votre réponse ici...")

        if st.button("Suivant ➡️", use_container_width=True):
            if user_ans:
                st.session_state.diag_answers.append({
                    "q": st.session_state[f"q_{st.session_state.diag_step}"], 
                    "a": user_ans
                })
                st.session_state.diag_step += 1
                st.rerun()
            else:
                st.warning("Une réponse est nécessaire pour calibrer votre IA.")
# --- ONBOARDING --- 
def onboarding(): 
    st.markdown("<h2 style='text-align: center;'>🎯 Personnalisez votre expérience</h2>", unsafe_allow_html=True) 
    
    # Creating a centered layout
    _, onboard_col, _ = st.columns([1, 1.5, 1])
    
    with onboard_col:
        level = st.selectbox("Choisissez votre niveau", ["1ère année secondaire", "4ème année (Baccalauréat)"]) 
        
        if "1ère" in level: 
            section = st.radio("Section", ["Générale", "Sport"])
            optional_subject = "Aucune" # No option for 1st year
        else: 
            section = st.radio("Section", ["Mathématiques", "Sciences Exp", "Économie", "Technique", "Lettre", "Sport", "Informatique"]) 
            # New dropdown for Bac students
            optional_subject = st.selectbox("Matière optionnelle", [
                "Italien", "Espagnol", "Allemand", "Chinois", "Turc",
                "Russe", "Portugais", "Arts Plastiques", "Musique",
                "Théâtre", "Éducation Physique"
            ])
        st.write("Décrivez votre méthode d'apprentissage (80-150 caractères)") 
        method = st.text_area("Ex: Je veux des résumés courts suivis d'exercices d'application directs.", help="Soyez précis.") 
        
        char_count = len(method) 
        st.caption(f"Caractères: {char_count}/150") 

        if st.button("Finaliser l'inscription", use_container_width=True):
            if 80 <= char_count <= 150:
                st.session_state.temp_user_profile_data = {
                    "username": st.session_state.temp_user["username"],
                    "password": st.session_state.temp_user["password"],
                    "level": level,
                    "section": section,
                    "optional_subject": optional_subject,
                    "teaching_method": method
                }
                st.session_state.step = "diagnostic"
                st.rerun()
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
                if text and len(text.strip()) > 100: 
                    vector = embed_model.encode(text).tolist() 
                    supabase.table("documents").insert({ 
                        "content": text, 
                        "metadata": {"level": up_level, "section": up_sec, "subject": up_subj}, 
                        "embedding": vector 
                    }).execute() 
            st.success("Terminé !") 

# --- AUTH UI --- 
def auth_screen():
    # Initialize a local state to track which form to show
    if "auth_view" not in st.session_state:
        st.session_state.auth_view = "landing"

    # 1. LANDING VIEW (The two buttons)
    if st.session_state.auth_view == "landing":
        st.markdown("<h1 style='text-align: center; color: white; font-size: 80px; margin-bottom: 0px;'>LyceeAI</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: grey; font-size: 20px;'>L'excellence académique à portée de clic.</p>", unsafe_allow_html=True)
        
        st.write("") # Spacer
        
        # Centering the buttons vertically by using a narrower column layout or just stacking them
        _, center_col, _ = st.columns([1, 2, 1])
        with center_col:
            if st.button("✨ S'inscrire", use_container_width=True):
                st.session_state.auth_view = "signup"
                st.rerun()
            
            if st.button("🔑 Se connecter", use_container_width=True):
                st.session_state.auth_view = "login"
                st.rerun()

    # 2. LOGIN VIEW
    elif st.session_state.auth_view == "login":
        st.markdown("<h3 style='text-align: center;'>Connexion</h3>", unsafe_allow_html=True)
        
        # Creating a centered layout for a compact look
        _, login_col, _ = st.columns([1, 1.5, 1])
        
        with login_col:
            u = st.text_input("Utilisateur", key="l_u") 
            p = st.text_input("Password", type="password", key="l_p") 
            
            st.write("") # Small spacer
            col_btn1, col_btn2 = st.columns([1, 1])
            with col_btn1:
                if st.button("Entrer", use_container_width=True): 
                    res = supabase.table("users_profile").select("*").eq("username", u).eq("password", p).execute() 
                    if res.data: 
                        st.session_state.user = res.data[0] 
                        st.session_state.messages = [] 
                        st.session_state.current_session_id = None
                        st.session_state.page = "dashboard" # Ensure page is set to dashboard
                        st.session_state.step = "main" # Move to main app logic 
                        st.rerun() 
                    else: 
                        st.error("Inconnu.") 
            with col_btn2:
                if st.button("🔙 Retour", use_container_width=True):
                    st.session_state.auth_view = "landing"
                    st.rerun()

    # 3. SIGNUP VIEW
    elif st.session_state.auth_view == "signup":
        st.markdown("<h3 style='text-align: center;'>Lbideya tebda min taw !</h3>", unsafe_allow_html=True)
        
        # Creating a centered layout for smaller boxes
        _, signup_col, _ = st.columns([1, 1.5, 1])
        
        with signup_col:
            nu = st.text_input("E5tar esm", key="s_u") 
            np = st.text_input("mot de passe 3ala kifik", type="password", key="s_p") 
            cp = st.text_input("Confirmi lmot de pasee mte3ek", type="password", key="s_c") 
            
            st.write("") # Small spacer
            col_btn3, col_btn4 = st.columns([1, 1])
            with col_btn3:
                if st.button("Suivant", use_container_width=True): 
                    if 3<=len(nu)<=15 and len(np)>=8 and np==cp: 
                        st.session_state.temp_user = {"username": nu, "password": np} 
                        st.session_state.step = "onboarding" 
                        st.rerun() 
                    else: st.error("Invalide (Nom: 3-15 chars, Pass: 8+ chars).")
            with col_btn4:
                if st.button("🔙 Retour", use_container_width=True):
                    st.session_state.auth_view = "landing"
                    st.rerun() 

# --- MAIN APP LOGIC --- 
if st.session_state.step == "auth": 
    auth_screen() 
elif st.session_state.step == "onboarding": 
    onboarding() 
elif st.session_state.step == "diagnostic": # ADD THIS PART
    diagnostic_survey()
else:
    # Initialize session tracking
    if "current_session_id" not in st.session_state:
        st.session_state.current_session_id = None
    # --- SIDEBAR LOGIC --- 
    with st.sidebar:
        # CASE 1: The OstedhiAI Specific Sidebar
        if st.session_state.page == "chat":
            st.markdown("<h1 style='color: white; text-align: left; font-size: 33px; '>🇹🇳 LyceeAI</h1>", unsafe_allow_html=True)
            
            if st.button("⬅️ Retour", use_container_width=True):
                st.session_state.page = "dashboard"
                st.rerun()
            
            # --- LINES REMOVED HERE ---
            if st.button("➕ Nouvelle Session De Chat", use_container_width=True):
                st.session_state.messages = []
                st.session_state.current_session_id = None
                st.rerun()
                
            if st.button("🗑️ Supprimer Toutes Les Sessions", use_container_width=True):
                # Filter by username so they only delete THEIR OWN stuff
                supabase.table("chat_history").delete().eq("username", st.session_state.user["username"]).execute()
                st.session_state.messages = []
                st.session_state.current_session_id = None
                st.success("Historique supprimé !")
                st.rerun()
            # --- LINES REMOVED HERE ---
            
            st.divider()
            st.subheader("📜 Historique")
            
            history_res = supabase.rpc("get_user_sessions", {"u_name": st.session_state.user["username"]}).execute()
            if history_res.data:
                # REVERSE the list here so the newest sessions are at the top
                sorted_sessions = sorted(history_res.data, key=lambda x: x['created_at'], reverse=True)
                
                for chat in sorted_sessions:
                    # Display the first few words of the first message
                    label = f"💬 {chat['first_msg'][:25]}..."
                    if st.button(label, key=chat['session_id'], use_container_width=True):
                        # Load specific session
                        msgs = supabase.table("chat_history").select("*").eq("session_id", chat['session_id']).order("created_at").execute()
                        st.session_state.messages = [{"role": m["role"], "content": m["content"]} for m in msgs.data]
                        st.session_state.current_session_id = chat['session_id']
                        st.rerun()
            else:
                st.caption("Aucune session trouvée.")
        # CASE 2: The "Lovely" Global Sidebar
        else:
            st.markdown("<h1 style='color: white; text-align: left; font-size: 33px; '>🇹🇳 LyceeAI</h1>", unsafe_allow_html=True)
            st.markdown(f"### 🌶️ Aslema **{st.session_state.user['username']}** !") 
            
            if st.button("📊 Dashboard", use_container_width=True):
                st.session_state.page = "dashboard"
            if st.button("👨🏻‍🏫 OstedhiAI", use_container_width=True):
                st.session_state.page = "chat"
                st.rerun() 
            if st.button("📝 Fichet", use_container_width=True):
                st.session_state.page = "fichet"
            if st.button("✍️ Exercices", use_container_width=True):
                st.session_state.page = "exercices"
            if st.button("🔄 Répétition Espacée", use_container_width=True):
                st.session_state.page = "repetition"
            if st.button("📅 Planning", use_container_width=True):
                st.session_state.page = "planning"

            if st.session_state.user['username'] == "elyes": 
                st.divider() 
                st.header("🛠 Founder Tools") 
                admin_uploader() 

            for _ in range(8): st.write("")
            st.divider()
            
            if st.button("💰 Abonnements", use_container_width=True):
                st.session_state.page = "abonnements"
            if st.button("🚪 Déconnexion", use_container_width=True): 
                st.session_state.user = None
                st.session_state.auth_view = "landing"
                st.session_state.step = "auth" 
                st.rerun() 
            st.caption("LyceeAI v1.0")
    # --- PAGE ROUTING ---
    if st.session_state.page == "dashboard":
        st.title("📊 Dashboard")
        st.header("Coming soon...⌛")

    elif st.session_state.page == "fichet":
        st.title("📝 Fichet")
        st.header("Coming soon...⌛")

    elif st.session_state.page == "exercices":
        st.title("✍️ Exercices")
        st.header("Coming soon...⌛")

    elif st.session_state.page == "repetition":
        st.title("🔄 Répétition Espacée")
        st.header("Coming soon...⌛")

    elif st.session_state.page == "planning":
        st.title("📅 Planning")
        st.header("Coming soon...⌛")

    elif st.session_state.page == "abonnements":
        st.title("💰 Abonnements")
        # 1. Creating 3 columns (side-by-side spaces)
        col1, col2, col3 = st.columns(3)
        # 2. Putting a rounded empty box in the first column
        with col1:
            # Adding a title in the first empty rounded box
            with st.container(border=True):
                st.markdown("### <span style='font-weight: normal; color: grey;'>LyceeAI</span> **LITE**", unsafe_allow_html=True)
                st.write("OstedhiAI yefhem fil program el tounsi")
                st.markdown("<span style='font-size: 32px; font-weight: bold;'>8dt</span> <span style='font-size: 18px; color: grey;'>/mois</span>", unsafe_allow_html=True)
                st.markdown("• Le chatbot d'OstedhiAI répondre à vitesse moyennee")
                st.markdown("• OstedhiAI entraîné à répondre conformément au programme tunisien officiel")
                st.markdown("• Accès très basique aux outils de productivité")
        # 3. Putting a rounded empty box in the second column
        with col2:
            # Adding a title in the second empty rounded box
            with st.container(border=True):
                st.markdown("### <span style='font-weight: normal; color: grey;'>LyceeAI</span> **PLUS**", unsafe_allow_html=True)
                st.write("LITE + OstedhiAI yjewbek asra3 + historique akber")
                st.markdown("<span style='font-size: 32px; font-weight: bold;'>26dt</span> <span style='font-size: 18px; color: grey;'>/mois</span>", unsafe_allow_html=True)
                st.markdown("• Le chatbot d'OsedhiAI répond plus rapidement")
                st.markdown("• OstedhiAI entraîné à répondre conformément au programme tunisien officiel")
                st.markdown("• Accès à des outils de productivité rapides")
                st.markdown("• Écosystème LyceeAI")
                st.markdown("• mémoire étendue et expérience personnalisée")
        # 4. Putting a rounded empty box in the third column
        with col3:
            # Adding a title in the third empty rounded box
            with st.container(border=True):
                st.markdown("### <span style='font-weight: normal; color: grey;'>LyceeAI</span> **PRO**", unsafe_allow_html=True)
                st.write("LITE + PLUS + Accès kemel lmizet LyceeAI lkol + AI a9wa (mémoire et vitesse)")
                st.markdown("<span style='font-size: 32px; font-weight: bold;'>125dt</span> <span style='font-size: 18px; color: grey;'>/mois</span>", unsafe_allow_html=True)
                st.markdown("• OstedhiAI répond de manière plus détaillée et plus rapide que tous les autres forfaits.")
                st.markdown("• OstedhiAI entraîné à répondre conformément au programme tunisien officiel")
                st.markdown("• Accès à de nombreux outils de productivité avancés et rapides")
                st.markdown("• Mémoire étendue liée à l'écosystème LyceeAI")
                st.markdown("• Un écosystème personnalisé, adapté à vos besoins")
                st.markdown("• Des ressources riches et mises à jour chaque semaine")
    elif st.session_state.page == "chat":
        st.title("👨🏻‍🏫 OstedhiAI") 
        if "messages" not in st.session_state: st.session_state.messages = [] 
        
        for m in st.session_state.messages: 
            with st.chat_message(m["role"]): st.markdown(m["content"]) 

        if prompt := st.chat_input("Posez une question..."): 
            # 1. GENERATE SESSION ID IF NEW CHAT
            if st.session_state.current_session_id is None:
                st.session_state.current_session_id = str(uuid.uuid4())

            # 2. SAVE USER MESSAGE WITH SESSION_ID
            st.session_state.messages.append({"role": "user", "content": prompt}) 
            with st.chat_message("user"): st.markdown(prompt) 
            
            supabase.table("chat_history").insert({
                "username": st.session_state.user["username"], 
                "session_id": st.session_state.current_session_id,
                "role": "user", 
                "content": prompt
            }).execute() 

            with st.chat_message("assistant"): 
                with st.spinner("Recherche..."): 
                    try: 
                        # --- VECTOR SEARCH LOGIC ---
                        q_vec = load_embed().encode(prompt).tolist() 
                        
                        # DEFINING THE MISSING VARIABLE HERE
                        rpc_params = { 
                            "query_embedding": q_vec, 
                            "match_threshold": 0.1, 
                            "match_count": 5, 
                            "filter_level": str(st.session_state.user['level']), 
                            "filter_section": str(st.session_state.user['section']) 
                        } 
                        
                        result = supabase.rpc("match_documents", rpc_params).execute() 
                        context = "\n".join([item['retrieved_content'] for item in result.data]) if result.data else "Pas de contexte." 
                        
                        # --- AI RESPONSE LOGIC ---
                        sys_msg = f"Tu es LyceeAI. Élève: {st.session_state.user['level']}. Méthode: {st.session_state.user['teaching_method']}. Contexte: {context}" 
                        history = [{"role": "system", "content": sys_msg}] + st.session_state.messages[-4:] 
                        
                        res_text = ask_openrouter(history) 
                        st.markdown(res_text) 

                        # 3. SAVE ASSISTANT MESSAGE WITH SESSION_ID
                        st.session_state.messages.append({"role": "assistant", "content": res_text}) 
                        supabase.table("chat_history").insert({
                            "username": st.session_state.user["username"], 
                            "session_id": st.session_state.current_session_id,
                            "role": "assistant", 
                            "content": res_text
                        }).execute() 
                        
                    except Exception as e: 
                        st.error(f"Erreur: {e}")

import streamlit as st
import sqlite3
import hashlib
import os
import json
import re
from datetime import datetime
import pandas as pd 
import plotly.express as px # Import Plotly for better charts

# ==============================================================================
# DATABASE & KNOWLEDGE BASE PATHS
# ==============================================================================
KNOWLEDGE_BASE_PATH = os.path.join(os.path.dirname(__file__), "knowledge_base.json")
USER_DB_PATH = os.path.join(os.path.dirname(__file__), "user_management.db")
FEEDBACK_DB_PATH = os.path.join(os.path.dirname(__file__), "feedback_data.db")
CHAT_DB_PATH = os.path.join(os.path.dirname(__file__), "knowledge_base.db") 

# ==============================================================================
# FALLBACK IMPORTS (Ensuring app runs even if external files are missing)
# ==============================================================================
try:
    from knowledge_base import (save_chat_to_db, get_chat_history, get_response_from_db, load_kb, format_health_info)
    from dialogue_manager import (get_bot_reply, detect_rule_based_intent, detect_input_language)
    KNOWLEDGE_BASE = load_kb()
    IMPORT_SUCCESS = True

except ImportError as e:
    # --- Dummy Definitions for Missing Imports (to prevent crashes) ---
    def get_bot_reply(user, msg, intent=None, language="English"): 
        if "hello" in msg.lower(): return "Hello! (Fallback mode). How can I help you today?"
        return "General fallback reply. Check your dialogue_manager.py file."
    def detect_rule_based_intent(msg): 
        if any(keyword in msg.lower() for keyword in ["cold", "fever", "flu", "sickness"]): return "Illness"
        elif any(keyword in msg.lower() for keyword in ["tip", "advise", "prevention", "health"]): return "Prevention"
        return "General"
    def detect_input_language(text): return 'English'
    def save_chat_to_db(user, msg, intent, reply): pass # Does nothing in fallback
    
    # Dummy chat history retrieval to populate charts if DB access fails
    def get_chat_history(user=None): 
        try:
            conn = sqlite3.connect(CHAT_DB_PATH); c = conn.cursor()
            c.execute('''CREATE TABLE IF NOT EXISTS chat_history (timestamp DATETIME, username TEXT, user_message TEXT, bot_reply TEXT, detected_intent TEXT)''')
            conn.commit()
            query = "SELECT timestamp, username, user_message, bot_reply, detected_intent FROM chat_history"
            data = c.execute(query).fetchall()
            conn.close(); columns = ['timestamp', 'username', 'user_message', 'bot_reply', 'detected_intent']
            return [dict(zip(columns, row)) for row in data]
        except Exception:
            return [{'timestamp': (datetime.now() - pd.Timedelta(days=i)).strftime('%Y-%m-%d %H:%M:%S'), 'username': f'user{i%3}', 'user_message': f'query {i}', 'bot_reply': 'reply', 'detected_intent': detect_rule_based_intent(f"query {i}")} for i in range(30)]

    def get_response_from_db(query): return []
    def format_health_info(info, topic=None, illness=None, language="English"): return "Information not available (check knowledge_base.py)."
    
    try:
        with open(KNOWLEDGE_BASE_PATH, 'r', encoding='utf-8') as f: KNOWLEDGE_BASE = json.load(f)
    except Exception: 
        KNOWLEDGE_BASE = {"Fever": {"description": "Elevated body temperature.", "symptoms": ["headache", "chills"], "treatment": ["rest", "hydration"], "warning": "Consult a doctor."}, "Cold": {"description": "Common viral infection.", "symptoms": ["sneeze", "sore throat"], "treatment": ["vitamin C", "tea"], "warning": "Avoid sharing utensils."}}
    IMPORT_SUCCESS = False


# ==============================================================================
# DATABASE INITIALIZATION
# ==============================================================================
def init_user_db():
    conn = sqlite3.connect(USER_DB_PATH); c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL, password TEXT NOT NULL, email TEXT NOT NULL, full_name TEXT NOT NULL, age INTEGER NOT NULL, gender TEXT NOT NULL, language TEXT NOT NULL, created_at DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit(); conn.close()

def init_feedback_db():
    conn = sqlite3.connect(FEEDBACK_DB_PATH); c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS feedback (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT NOT NULL, user_query TEXT NOT NULL, bot_reply TEXT NOT NULL, is_positive INTEGER NOT NULL, comment TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit(); conn.close()
    
def init_chat_db():
    conn = sqlite3.connect(CHAT_DB_PATH); c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS chat_history (timestamp DATETIME, username TEXT, user_message TEXT, bot_reply TEXT, detected_intent TEXT)''')
    conn.commit(); conn.close()

init_user_db(); init_feedback_db(); init_chat_db()


# ==============================================================================
# SESSION STATE & TRANSLATIONS 
# ==============================================================================
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'username' not in st.session_state: st.session_state.username = None
if 'language' not in st.session_state: st.session_state.language = 'English'
if 'chat_history' not in st.session_state: st.session_state.chat_history = []
if 'page' not in st.session_state: st.session_state.page = 'Login'
if 'last_bot_reply' not in st.session_state: st.session_state.last_bot_reply = None
if 'last_user_query' not in st.session_state: st.session_state.last_user_query = None
if 'show_feedback_form' not in st.session_state: st.session_state.show_feedback_form = False
if 'feedback_prompted' not in st.session_state: st.session_state.feedback_prompted = False

translations = {
    'English': {'register': 'Register', 'login': 'Login', 'profile_update': 'Profile Update', 'chat': 'Chat', 'username': 'Username', 'password': 'Password', 'email': 'Email', 'full_name': 'Full Name', 'age': 'Age', 'gender': 'Gender', 'male': 'Male', 'female': 'Female', 'other': 'Other', 'submit': 'Submit', 'logout': 'Logout', 'welcome': 'Welcome', 'type_message': 'Type your message...', 'send': 'Send', 'login_success': 'Login successful!', 'register_success': 'Registration successful! Please login.', 'profile_update_success': 'Profile updated successfully!', 'select_language': 'Select Language', 'view_chat_history': 'View Chat History', 'view_database': 'View Database', 'admin_panel': 'Admin Panel', 'access_denied': 'Access Denied. You must be logged in as an Admin.'},
    'Telugu': {'register': 'నమోదు', 'login': 'లాగిన్', 'profile_update': 'ప్రొఫైల్ నవీకరణ', 'chat': 'చాట్', 'username': 'వినియోగదారు పేరు', 'password': 'పాస్వర్డ్', 'email': 'ఇమెయిల్', 'full_name': 'పూర్తి పేరు', 'age': 'వయస్సు', 'gender': 'లింగం', 'male': 'పురుషుడు', 'female': 'స్త్రీ', 'other': 'ఇతర', 'submit': 'సమర్పించండి', 'logout': 'లాగ్అవుట్', 'welcome': 'స్వాగతం', 'type_message': 'మీ సందేశాన్ని టైప్ చేయండి...', 'send': 'పంపండి', 'login_success': 'లాగిన్ విజయవంతమైనది!', 'register_success': 'నమోదు విజయవంతమైనది! దయచేసి లాగిన్ చేయండి.', 'profile_update_success': 'ప్రొఫైల్ విజయవంతంగా నవీకరించబడింది!', 'select_language': 'భాషను ఎంచుకోండి', 'view_chat_history': 'చాట్ చరిత్రను వీక్షించండి', 'view_database': 'డేటాబేస్ వీక్షించండి', 'admin_panel': 'అడ్మిన్ ప్యానెల్', 'access_denied': 'యాక్సెస్ నిరాకరించబడింది. మీరు అడ్మిన్‌గా లాగిన్ అయి ఉండాలి।'},
    'Hindi': {'register': 'पंजीकरण', 'login': 'लॉगिन', 'profile_update': 'प्रोफाइल अद्यतन', 'chat': 'चैट', 'username': 'उपयोगकर्ता नाम', 'password': 'पास्सवर्ड', 'email': 'ईमेल', 'full_name': 'पूरा नाम', 'age': 'उम्र', 'gender': 'लिंग', 'male': 'पुरुष', 'female': 'महिला', 'other': 'अन्य', 'submit': 'जमा करें', 'logout': 'लॉगआउट', 'welcome': 'स्वागत है', 'type_message': 'अपना संदेश टाइप करें...', 'send': 'भेजें', 'login_success': 'लॉगिन सफल!', 'register_success': 'पंजीकरण सफल! कृपया लॉगिन करें।', 'profile_update_success': 'प्रोफाइल सफलतापूर्वक अपडेट की गई!', 'select_language': 'भाषा चुनें', 'view_chat_history': 'चैट इतिहास देखें', 'view_database': 'डेटाबेस देखें', 'admin_panel': 'एडमिन पैनल', 'access_denied': 'पहुंच अस्वीकृत। आपको व्यवस्थापक के रूप में लॉग इन होना चाहिए।'}
}

def translate(key): return translations.get(st.session_state.language, translations['English']).get(key, key)
def navigate_to(page): st.session_state.page = page

# ==============================================================================
# USER MANAGEMENT & DATA RETRIEVAL 
# ==============================================================================
def hash_password(password): return hashlib.sha256(password.encode()).hexdigest()
def login_user(username, password):
    conn = sqlite3.connect(USER_DB_PATH); c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username=?", (username,)); user = c.fetchone(); conn.close()
    if user and user[2] == hash_password(password):
        st.session_state.logged_in = True; st.session_state.username = username; st.session_state.language = user[7]; navigate_to('Chat'); return True
    return False

def register_user(username, password, email, full_name, age, gender, language):
    conn = sqlite3.connect(USER_DB_PATH); c = conn.cursor()
    try:
        c.execute('''INSERT INTO users (username, password, email, full_name, age, gender, language) VALUES (?, ?, ?, ?, ?, ?, ?)''', (username, hash_password(password), email, full_name, age, gender, language))
        conn.commit(); conn.close(); return True
    except sqlite3.IntegrityError: conn.close(); return False
    except Exception as e: conn.close(); st.error(f"Registration error: {e}"); return False

def get_all_users():
    conn = sqlite3.connect(USER_DB_PATH); c = conn.cursor()
    users = c.execute("SELECT username, email, full_name, age, gender, language, created_at FROM users").fetchall(); conn.close(); return users

def get_all_feedback_data():
    conn = sqlite3.connect(FEEDBACK_DB_PATH); c = conn.cursor()
    feedback = c.execute("SELECT id, username, user_query, bot_reply, is_positive, comment, timestamp FROM feedback ORDER BY timestamp DESC").fetchall(); conn.close(); return feedback

def get_user_conversations(username): return get_chat_history(username)
def get_all_chats(): return get_chat_history(username=None)
def save_feedback_to_db(username, user_query, bot_reply, is_positive, comment):
    try:
        conn = sqlite3.connect(FEEDBACK_DB_PATH); c = conn.cursor()
        c.execute('''INSERT INTO feedback (username, user_query, bot_reply, is_positive, comment) VALUES (?, ?, ?, ?, ?)''', (username, user_query, bot_reply, is_positive, comment))
        conn.commit(); conn.close(); return True
    except Exception as e: st.error(f"Error saving feedback: {e}"); return False

# ==============================================================================
# KNOWLEDGE BASE MANAGEMENT FUNCTIONS 
# ==============================================================================
def save_kb_to_file(kb_data):
    try:
        with open(KNOWLEDGE_BASE_PATH, 'w', encoding='utf-8') as f:
            json.dump(kb_data, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        st.error(f"Error saving knowledge base: {e}"); return False

def add_kb_entry(name, desc_en, symptoms_en, treatment_en):
    global KNOWLEDGE_BASE 
    new_entry = {"description": desc_en, "symptoms": [s.strip() for s in symptoms_en.split(',')], "treatment": [t.strip() for t in treatment_en.split(',')], "warning": "Always consult a doctor.", "description_hi": "", "symptoms_hi": [], "treatment_hi": [], "warning_hi": "", "description_te": "", "symptoms_te": [], "treatment_te": [], "warning_te": ""}
    key = name.strip() 
    if key in KNOWLEDGE_BASE:
        st.error(f"Entry '{key}' already exists in the Knowledge Base.")
        return False
    KNOWLEDGE_BASE[key] = new_entry
    return save_kb_to_file(KNOWLEDGE_BASE)

def update_kb_entry(original_name, new_data):
    global KNOWLEDGE_BASE 
    key = original_name.strip()
    if key in KNOWLEDGE_BASE:
        KNOWLEDGE_BASE[key]['description'] = new_data['description']
        KNOWLEDGE_BASE[key]['symptoms'] = [s.strip() for s in new_data['symptoms'].split(',')]
        KNOWLEDGE_BASE[key]['treatment'] = [t.strip() for t in new_data['treatment'].split(',')]
        # Preserve other language translations if they exist
        return save_kb_to_file(KNOWLEDGE_BASE)
    return False

def delete_kb_entry(name):
    global KNOWLEDGE_BASE 
    key = name.strip()
    if key in KNOWLEDGE_BASE:
        del KNOWLEDGE_BASE[key]
        return save_kb_to_file(KNOWLEDGE_BASE)
    return False


# ==============================================================================
# PAGE RENDERING FUNCTIONS 
# ==============================================================================
def render_login(): 
    st.title(translate('login')); 
    with st.form("login_form"):
        username = st.text_input(translate('username')); password = st.text_input(translate('password'), type="password"); submitted = st.form_submit_button(translate('login'))
        if submitted:
            if login_user(username, password): st.success(translate('login_success')); st.rerun()
            else: st.error("Invalid username or password.")

def render_register(): 
    st.title(translate('register')); 
    with st.form("register_form"):
        username = st.text_input(translate('username')); password = st.text_input(translate('password'), type="password"); email = st.text_input(translate('email')); full_name = st.text_input(translate('full_name')); age = st.number_input(translate('age'), min_value=1, max_value=120, value=25); gender = st.selectbox(translate('gender'), options=[translate('male'), translate('female'), translate('other')]); language = st.selectbox(translate('select_language'), options=list(translations.keys()), index=0)
        submitted = st.form_submit_button(translate('register'))
        if submitted:
            if register_user(username, password, email, full_name, age, gender, language): st.success(translate('register_success')); navigate_to('Login'); st.rerun()
            else: st.error("Username already exists. Please choose a different one.")
                
def render_profile_update(): 
    st.title(translate('profile_update')); st.info("Profile Update functionality needs user data retrieval logic which is simplified here."); st.button("Back to Chat", on_click=lambda: navigate_to('Chat'))

def render_chat(): 
    st.title(translate('chat')); 
    
    # 💥 FIX: Separating the loop and the with statement
    for chat in st.session_state.chat_history: 
        with st.chat_message(chat['role']): 
            st.markdown(chat['content'])
            
    if prompt := st.chat_input(translate('type_message')):
        st.session_state.show_feedback_form = False; st.session_state.feedback_prompted = False; user_message = prompt
        st.session_state.chat_history.append({"role": "user", "content": user_message}); st.session_state.last_user_query = user_message
        with st.chat_message("user"): st.markdown(user_message)
        intent = detect_rule_based_intent(user_message); language = st.session_state.language
        bot_reply = get_bot_reply(user_id=st.session_state.username, user_message=user_message, intent=intent, language=language)
        st.session_state.chat_history.append({"role": "assistant", "content": bot_reply}); st.session_state.last_bot_reply = bot_reply
        with st.chat_message("assistant"): st.markdown(bot_reply)
        save_chat_to_db(st.session_state.username, user_message, intent, bot_reply)
        st.session_state.feedback_prompted = True; st.rerun()
    if st.session_state.get('feedback_prompted', False) and st.session_state.last_bot_reply:
        st.markdown("---"); st.subheader("Was this response helpful? (Feedback needed after every chat)"); col_feedback = st.columns([1, 1, 3])
        if col_feedback[0].button("👍 Yes", key="fb_yes"): st.session_state.feedback_type = True; st.session_state.show_feedback_form = True; st.session_state.feedback_prompted = False; st.rerun() 
        if col_feedback[1].button("👎 No", key="fb_no"): st.session_state.feedback_type = False; st.session_state.show_feedback_form = True; st.session_state.feedback_prompted = False; st.rerun() 
    if st.session_state.get('show_feedback_form', False):
        feedback_type_text = "Positive" if st.session_state.feedback_type else "Negative"; st.info(f"You selected **{feedback_type_text}** feedback.")
        with st.form("feedback_form"):
            comment = st.text_area("Optional Comment (for improvement):", "")
            if st.form_submit_button("Submit Feedback"):
                success = save_feedback_to_db(username=st.session_state.username, user_query=st.session_state.last_user_query, bot_reply=st.session_state.last_bot_reply, is_positive=1 if st.session_state.feedback_type else 0, comment=comment)
                if success: st.success("Thank you for your feedback!")
                else: st.error("Failed to save feedback.")
                st.session_state.show_feedback_form = False; st.session_state.last_bot_reply = None; st.rerun()

def render_history(): 
    st.title(translate('view_chat_history')); history_data = get_user_conversations(st.session_state.username)
    if history_data:
        df = pd.DataFrame(history_data); df = df[['timestamp', 'user_message', 'bot_reply', 'detected_intent']]; df.columns = ['Timestamp', 'User Message', 'Bot Reply', 'Intent']
        st.dataframe(df, use_container_width=True)
    else: st.info("No chat history found for this user.")

def render_navigation(): 
    cols = st.columns([1, 1, 1, 1, 1, 1])
    with cols[0]:
        if st.session_state.page != 'Register' and not st.session_state.logged_in:
            if st.button(translate('register'), use_container_width=True): navigate_to('Register')
    with cols[1]:
        if st.session_state.logged_in:
            if st.button(translate('profile_update'), use_container_width=True): navigate_to('Profile')
        elif st.session_state.page != 'Login':
            if st.button(translate('login'), use_container_width=True): navigate_to('Login')
    with cols[2]:
        if st.session_state.logged_in and st.session_state.page != 'Chat':
            if st.button(translate('chat'), use_container_width=True): navigate_to('Chat')
    with cols[3]:
        if st.session_state.logged_in and st.session_state.page != 'History':
            if st.button(translate('view_chat_history'), use_container_width=True): navigate_to('History')
    with cols[4]:
        is_admin = st.session_state.logged_in and st.session_state.username.lower() in ["admin", "admin_user"]
        if is_admin: 
            if st.button(translate('admin_panel'), use_container_width=True): navigate_to('Admin')
    with cols[5]:
        if st.session_state.logged_in:
            if st.button(translate('logout'), use_container_width=True):
                st.session_state.logged_in = False; st.session_state.username = None; st.session_state.last_bot_reply = None; st.session_state.show_feedback_form = False
                st.success(f"{translate('logout')} successful!"); st.rerun()
    st.sidebar.selectbox(translate('select_language'), options=list(translations.keys()), index=list(translations.keys()).index(st.session_state.language), key='language_selector', on_change=lambda: setattr(st.session_state, 'language', st.session_state.language_selector))
    if st.session_state.logged_in: st.sidebar.markdown(f"**{translate('welcome')}, {st.session_state.username}!**")


# ==============================================================================
# ADMIN PANEL (Full Implementation)
# ==============================================================================
def render_admin():
    if st.session_state.username.lower() not in ["admin", "admin_user"]:
        st.error(translate('access_denied')); return

    st.title(translate('admin_panel'))
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["Dashboard", "Knowledge Base", "User Analytics", "Chat History", "Feedback"])

    # ----------------------------------------------------
    # TAB 1: DASHBOARD (Includes Charts and KPIs)
    # ----------------------------------------------------
    with tab1:
        st.header("System Overview")
        all_users = get_all_users(); all_chats_raw = get_all_chats(); all_feedback = get_all_feedback_data()
        chat_df = pd.DataFrame(all_chats_raw) if all_chats_raw else pd.DataFrame(columns=['timestamp', 'detected_intent'])
        
        # KPI Calculations
        total_users = len(all_users); total_queries = len(chat_df); total_kb_entries = len(KNOWLEDGE_BASE); total_feedback_count = len(all_feedback)
        positive_feedback_count = sum(1 for _, _, _, _, is_positive, _, _ in all_feedback if is_positive == 1)
        feedback_percent = positive_feedback_count * 100 // (total_feedback_count or 1)
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Users", total_users); col2.metric("Total Queries", total_queries); col3.metric("KB Entries", total_kb_entries)
        col4.metric("Positive Feedback", f"{positive_feedback_count}/{total_feedback_count} ({feedback_percent}%)")

        st.markdown("---")
        chart_col1, chart_col2 = st.columns(2)

        # CHART 1: QUERY TRENDS OVER TIME
        with chart_col1:
            st.subheader("Query Trends Over Time")
            if not chat_df.empty and 'timestamp' in chat_df.columns:
                chat_df['timestamp'] = pd.to_datetime(chat_df['timestamp'])
                query_counts = chat_df.set_index('timestamp').resample('D').size().rename("Queries")
                fig = px.line(query_counts.reset_index(), x='timestamp', y='Queries', title="Queries per Day")
                st.plotly_chart(fig, use_container_width=True)
            else: st.info("No sufficient chat history data to plot query trends.")

        # CHART 2: TOP QUERY CATEGORIES
        with chart_col2:
            st.subheader("Top Query Categories")
            if not chat_df.empty and 'detected_intent' in chat_df.columns:
                intent_counts = chat_df['detected_intent'].value_counts().reset_index()
                intent_counts.columns = ['Intent', 'Count']
                fig = px.pie(intent_counts, values='Count', names='Intent', title='Distribution of Query Intents', hole=.3)
                st.plotly_chart(fig, use_container_width=True)
            else: st.info("No intent data available for Top Query Categories chart.")
                
        st.markdown("---")
        
        st.subheader("Recent Feedback")
        if all_feedback:
            feedback_df = pd.DataFrame(all_feedback, columns=['ID', 'Username', 'Query', 'Reply', 'Positive', 'Comment', 'Timestamp'])
            feedback_df['Positive'] = feedback_df['Positive'].apply(lambda x: '👍 Positive' if x == 1 else '👎 Negative')
            st.dataframe(feedback_df[['Timestamp', 'Username', 'Query', 'Positive', 'Comment']].head(5), use_container_width=True)
        else: st.info("No feedback yet.")


    # ----------------------------------------------------
    # TAB 2: KNOWLEDGE BASE MANAGEMENT 
    # ----------------------------------------------------
    with tab2:
        st.header("Knowledge Base (KB) Management")
        
        kb_tab1, kb_tab2, kb_tab3 = st.tabs(["View/Edit Entries", "Add New Entry", "Delete Entry"])
        
        # VIEW / EDIT
        with kb_tab1:
            st.subheader("View and Edit Existing Entries")
            kb_names = list(KNOWLEDGE_BASE.keys())
            if not kb_names:
                st.warning("The knowledge base is empty.")
            else:
                selected_name = st.selectbox("Select Entry to View/Edit:", kb_names)
                entry = KNOWLEDGE_BASE.get(selected_name, {})
                
                with st.form(f"edit_form_{selected_name}", clear_on_submit=False):
                    new_description = st.text_area("Description (English)", entry.get('description', ''))
                    new_symptoms = st.text_area("Symptoms (Comma Separated, English)", ", ".join(entry.get('symptoms', [])))
                    new_treatment = st.text_area("Treatment/Tips (Comma Separated, English)", ", ".join(entry.get('treatment', [])))
                    
                    if st.form_submit_button("Save Changes"):
                        new_data = {'description': new_description, 'symptoms': new_symptoms, 'treatment': new_treatment}
                        if update_kb_entry(selected_name, new_data):
                            st.success(f"Entry '{selected_name}' updated successfully!")
                            st.rerun()
                        else: st.error("Failed to update entry.")
        
        # ADD NEW
        with kb_tab2:
            st.subheader("Add a New Knowledge Base Entry")
            with st.form("add_new_form", clear_on_submit=True):
                new_name = st.text_input("New Entry Name (e.g., Dengue Fever)")
                new_description = st.text_area("Description (English)")
                new_symptoms = st.text_area("Symptoms (Comma Separated, English)")
                new_treatment = st.text_area("Treatment/Tips (Comma Separated, English)")
                
                if st.form_submit_button("Add New Entry"):
                    if new_name and new_description and new_symptoms and new_treatment:
                        if add_kb_entry(new_name, new_description, new_symptoms, new_treatment):
                            st.success(f"New entry '{new_name}' added successfully! Reloading...")
                            st.rerun()
                        # Error handled in add_kb_entry function
                    else: st.error("Please fill in all fields.")

        # DELETE
        with kb_tab3:
            st.subheader("Delete Knowledge Base Entry")
            kb_names = list(KNOWLEDGE_BASE.keys())
            if kb_names:
                delete_name = st.selectbox("Select Entry to Delete:", kb_names, key="delete_kb_select")
                if st.button(f"Permanently Delete '{delete_name}'", type="primary"):
                    if delete_kb_entry(delete_name):
                        st.success(f"Entry '{delete_name}' deleted successfully! Reloading...")
                        st.rerun()
                    else: st.error("Failed to delete entry.")
            else:
                st.info("No entries available to delete.")


    # ----------------------------------------------------
    # TAB 3: USER ANALYTICS 
    # ----------------------------------------------------
    with tab3:
        st.header("Registered User Analytics")
        user_data = get_all_users()
        
        if user_data:
            df = pd.DataFrame(user_data, columns=['Username', 'Email', 'Full Name', 'Age', 'Gender', 'Language', 'Created At'])
            
            st.subheader("User Table")
            st.dataframe(df, use_container_width=True)

            st.markdown("---")

            col_chart1, col_chart2 = st.columns(2)
            
            # Chart 1: Gender Distribution
            with col_chart1:
                st.subheader("Gender Distribution")
                gender_counts = df['Gender'].value_counts().reset_index()
                gender_counts.columns = ['Gender', 'Count']
                fig_gender = px.pie(gender_counts, values='Count', names='Gender', title='Registered User Gender Split', hole=.3)
                st.plotly_chart(fig_gender, use_container_width=True)
                
            # Chart 2: Language Preference
            with col_chart2:
                st.subheader("Language Preference")
                lang_counts = df['Language'].value_counts().reset_index()
                lang_counts.columns = ['Language', 'Count']
                fig_lang = px.bar(lang_counts, x='Language', y='Count', title='Primary Language Preference')
                st.plotly_chart(fig_lang, use_container_width=True)
                
        else:
            st.info("No user data available for analytics.")


    # ----------------------------------------------------
    # TAB 4: CHAT HISTORY (ALL USERS) 
    # ----------------------------------------------------
    with tab4:
        st.header("All User Chat History")
        all_chat_data = get_all_chats()
        if all_chat_data:
            df = pd.DataFrame(all_chat_data)
            df = df[['timestamp', 'username', 'user_message', 'bot_reply', 'detected_intent']]
            df.columns = ['Timestamp', 'Username', 'User Message', 'Bot Reply', 'Intent']
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No chat history recorded in the database.")


    # ----------------------------------------------------
    # TAB 5: FEEDBACK DATA
    # ----------------------------------------------------
    with tab5:
        st.header("User Feedback Log")
        feedback_data = get_all_feedback_data()
        if feedback_data:
            df = pd.DataFrame(feedback_data, columns=['ID', 'Username', 'User Query', 'Bot Reply', 'Is Positive', 'Comment', 'Timestamp'])
            df['Is Positive'] = df['Is Positive'].apply(lambda x: '👍 Positive' if x == 1 else '👎 Negative')
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No feedback has been submitted yet.")

# ==============================================================================
# MAIN APP LOGIC
# ==============================================================================
st.set_page_config(page_title="Global Wellness Chatbot", layout="wide", initial_sidebar_state="auto")
st.title("Global Wellness Chatbot 🌍💬")

render_navigation()

if st.session_state.logged_in:
    if st.session_state.page == 'Chat': render_chat()
    elif st.session_state.page == 'Profile': render_profile_update()
    elif st.session_state.page == 'History': render_history()
    elif st.session_state.page == 'Admin': render_admin()
    else: render_chat()
else:
    if st.session_state.page == 'Register': render_register()
    else: render_login()
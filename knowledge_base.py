import sqlite3
import os
import random
import json
from datetime import datetime

# --- Paths ---
DB_PATH = os.path.join(os.path.dirname(__file__), "knowledge_base.db")
JSON_PATH = os.path.join(os.path.dirname(__file__), "knowledge_base.json")

# --- SQLite DB initialization ---
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Create tables with correct structure
    c.execute('''CREATE TABLE IF NOT EXISTS kb_responses
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                 intent TEXT NOT NULL,
                 response TEXT NOT NULL)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS chat_history
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                 username TEXT NOT NULL,
                 user_message TEXT NOT NULL,
                 detected_intent TEXT,
                 bot_reply TEXT NOT NULL,
                 timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    
    # Check if we need to insert sample data
    c.execute("SELECT COUNT(*) FROM kb_responses")
    if c.fetchone()[0] == 0:
        sample_data = [
            ('greet', '👋 Hello! I\'m WellBot. How are you feeling today?'),
            ('greet', 'Hi there! 😊 How are you doing today?'),
            ('positive_mood', '😊 That\'s wonderful to hear!'),
            ('thanks', 'You\'re welcome! 💙'),
            ('goodbye', 'Goodbye! 👋 Take care!'),
        ]
        c.executemany("INSERT INTO kb_responses (intent, response) VALUES (?, ?)", sample_data)
    
    conn.commit()
    conn.close()
    print("✅ Database initialized successfully")

# --- SQLite helper functions ---
def get_response_from_db(intent):
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT response FROM kb_responses WHERE intent=?", (intent,))
        rows = c.fetchall()
        conn.close()
        if not rows:
            return None
        return random.choice([r[0] for r in rows])
    except Exception as e:
        print(f"Error getting response from DB: {e}")
        return None

def add_response(intent, response):
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("INSERT INTO kb_responses (intent, response) VALUES (?, ?)", (intent, response))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error adding response: {e}")
        return False

def save_chat_to_db(username, user_message, detected_intent, bot_reply):
    """Save user chat and bot reply to database"""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('''INSERT INTO chat_history 
                     (username, user_message, detected_intent, bot_reply) 
                     VALUES (?, ?, ?, ?)''',
                  (username, user_message, detected_intent, bot_reply))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error saving chat to DB: {e}")
        return False

def get_chat_history(username=None):
    """Retrieve chat history from database"""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        if username:
            c.execute('''SELECT username, user_message, detected_intent, bot_reply, timestamp 
                         FROM chat_history WHERE username=? ORDER BY timestamp''', (username,))
        else:
            c.execute('''SELECT username, user_message, detected_intent, bot_reply, timestamp 
                         FROM chat_history ORDER BY timestamp''')
        
        rows = c.fetchall()
        conn.close()
        
        # Convert to list of dictionaries
        history = []
        for row in rows:
            history.append({
                "username": row[0],
                "user_message": row[1],
                "detected_intent": row[2],
                "bot_reply": row[3],
                "timestamp": row[4]
            })
        return history
    except Exception as e:
        print(f"Error getting chat history: {e}")
        return []

# --- Load JSON KB for dialogue manager ---
def load_kb():
    """Load knowledge base from JSON file. Converts list to dict if needed."""
    if not os.path.exists(JSON_PATH):
        return {}
    try:
        with open(JSON_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            kb_dict = {}
            for item in data:
                if "name" in item:
                    kb_dict[item["name"]] = item
            return kb_dict
        return data
    except Exception as e:
        print(f"Error loading knowledge base: {e}")
        return {}

def format_health_info(info, topic=None, illness=None, language="English"):
    """Format a response for the chatbot with multilingual support."""
    if not info:
        if language == 'Hindi':
            return "मेरे पास इसके बारे में अभी तक जानकारी नहीं है।"
        elif language == 'Telugu':
            return "దీని గురించి ఇంకా నాకు సమాచారం లేదు."
        else:
            return "I don't have information about that yet."
    
    # Language mapping
    lang_map = {
        'English': {'desc': 'description', 'treatment': 'treatment', 'warning': 'warning'},
        'Hindi': {'desc': 'description_hi', 'treatment': 'treatment_hi', 'warning': 'warning_hi'},
        'Telugu': {'desc': 'description_te', 'treatment': 'treatment_te', 'warning': 'warning_te'}
    }
    
    current_lang = lang_map.get(language, lang_map['English'])
    
    if topic:
        desc = info.get(current_lang['desc'], info.get('description', ''))
        tips = info.get("tips", [])
        return desc + ("\n" + "\n".join(tips) if tips else "")
    
    if illness:
        parts = [f"{illness}"]
        
        # Get description in current language
        desc = info.get(current_lang['desc'], info.get('description', ''))
        if desc:
            parts.append(desc)
        
        # Get treatment in current language
        treatment = info.get(current_lang['treatment'], info.get('treatment', []))
        if treatment:
            if language == 'English':
                parts.append("💊 Treatment:")
            elif language == 'Hindi':
                parts.append("💊 उपचार:")
            elif language == 'Telugu':
                parts.append("💊 చికిత్స:")
            
            for treat in treatment:
                parts.append(f"• {treat}")
        
        # Get warning in current language
        warning = info.get(current_lang['warning'], info.get('warning', ''))
        if warning:
            if language == 'English':
                parts.append(f"⚠ Important: {warning}")
            elif language == 'Hindi':
                parts.append(f"⚠ महत्वपूर्ण: {warning}")
            elif language == 'Telugu':
                parts.append(f"⚠ ముఖ్యమైన: {warning}")
        
        return "\n".join(parts)
    
    if language == 'Hindi':
        return "मेरे पास इसके बारे में जानकारी नहीं है।"
    elif language == 'Telugu':
        return "దీని గురించి నాకు సమాచారం లేదు."
    else:
        return "I don't have info about that yet."

# Initialize database only when this file is run directly
if __name__ == "__main__":
    init_db()
else:
    # For imports, initialize database but handle errors gracefully
    try:
        init_db()
    except Exception as e:
        print(f"Warning: Could not initialize database: {e}")
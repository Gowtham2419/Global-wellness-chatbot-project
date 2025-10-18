import random
import re
import json
import os
from typing import List, Dict, Tuple

# Import from knowledge_base - FIXED to avoid circular imports
try:
    from knowledge_base import load_kb, format_health_info
except ImportError as e:
    # Fallback definitions
    def load_kb(): return {}
    def format_health_info(info, topic=None, illness=None, language="English"): 
        return "Information not available"
    print(f"Warning: Could not import from knowledge_base: {e}")

# ✅ ADD SESSIONS FILE PATH
SESSIONS_FILE = os.path.join(os.path.dirname(__file__), "user_sessions.json")

# Load knowledge base
try:
    KB = load_kb()
except Exception as e:
    print(f"Warning: Could not load knowledge base: {e}")
    KB = {}

# ✅ IMPROVED SYMPTOM MAPPING - includes all languages
SYMPTOM_TO_ILLNESSES = {}

# Build comprehensive symptom mapping from all languages
for illness, info in KB.items():
    # English symptoms
    for sym in info.get("symptoms", []):
        SYMPTOM_TO_ILLNESSES.setdefault(sym.lower(), set()).add(illness)
    
    # Hindi symptoms
    for sym in info.get("symptoms_hi", []):
        SYMPTOM_TO_ILLNESSES.setdefault(sym.lower(), set()).add(illness)
    
    # Telugu symptoms
    for sym in info.get("symptoms_te", []):
        SYMPTOM_TO_ILLNESSES.setdefault(sym.lower(), set()).add(illness)

# ✅ LANGUAGE DETECTION FUNCTION
def detect_input_language(text):
    """
    Detect the language of user input based on character patterns
    """
    # Hindi character range
    hindi_pattern = re.compile(r'[\u0900-\u097F]')
    # Telugu character range  
    telugu_pattern = re.compile(r'[\u0C00-\u0C7F]')
    
    if hindi_pattern.search(text):
        return 'Hindi'
    elif telugu_pattern.search(text):
        return 'Telugu'
    else:
        return 'English'

# ✅ MODIFIED: Load sessions from JSON file instead of memory
def load_sessions():
    """Load user sessions from JSON file"""
    if os.path.exists(SESSIONS_FILE):
        try:
            with open(SESSIONS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                # Convert lists back to sets for symptoms
                for user_id, session in data.items():
                    if "symptoms" in session:
                        session["symptoms"] = set(session["symptoms"])
                return data
        except Exception as e:
            print(f"Warning: Could not load sessions: {e}")
            return {}
    return {}

def save_sessions():
    """Save user sessions to JSON file"""
    try:
        # Convert sets to lists for JSON serialization
        save_data = {}
        for user_id, session in user_sessions.items():
            save_data[user_id] = {
                "symptoms": list(session["symptoms"]),
                "entities": session["entities"]
            }
        with open(SESSIONS_FILE, "w", encoding="utf-8") as f:
            json.dump(save_data, f, indent=2)
    except Exception as e:
        print(f"Warning: Could not save sessions: {e}")

# ✅ MODIFIED: Load sessions from file at startup
user_sessions = load_sessions()

# Conversation phrases with multilingual support
GREETINGS = {
    'English': ["Hello! How are you feeling today?", "Hi there! Tell me your symptoms.", "Hey! How can I help you today?"],
    'Hindi': ["नमस्ते! आज आप कैसा महसूस कर रहे हैं?", "हाय! मुझे अपने लक्षण बताएं।", "नमस्ते! आज मैं आपकी कैसे मदद कर सकता हूं?"],
    'Telugu': ["హలో! మీరు ఈరోజు ఎలా భావిస్తున్నారు?", "హాయ్! మీ లక్షణాలు చెప్పండి.", "హే! నేను ఈరోజు మీకు ఎలా సహాయపడగలను?"]
}

GOODBYES = {
    'English': ["Goodbye! Take care!", "See you soon — stay safe!", "Bye! Wishing you good health."],
    'Hindi': ["अलविदा! अपना ख्याल रखना!", "जल्द मिलते हैं - सुरक्षित रहें!", "अलविदा! आपके अच्छे स्वास्थ्य की कामना करता हूं।"],
    'Telugu': ["వీడ్కోలు! జాగ్రత్తగా ఉండండి!", "త్వరలో కలుద్దాం - సురక్షితంగా ఉండండి!", "బై! మీ మంచి ఆరోగ్యానికి శుభాకాంక్షలు."]
}

MORE_SYMPTOMS = {
    'English': ["Can you tell me more symptoms?", "Any other symptoms?", "What else do you feel?"],
    'Hindi': ["क्या आप और लक्षण बता सकते हैं?", "कोई अन्य लक्षण?", "आप और क्या महसूस कर रहे हैं?"],
    'Telugu': ["మీరు మరిన్ని లక్షణాలు చెప్పగలరా?", "ఇతర లక్షణాలు ఏమైనా ఉన్నాయా?", "మీరు మరేమి అనుభవిస్తున్నారు?"]
}

DISCLAIMER = {
    'English': "Note: I'm not a medical professional. I can suggest possible conditions based on symptoms, but please consult a healthcare provider for a proper diagnosis.",
    'Hindi': "नोट: मैं एक चिकित्सा पेशेवर नहीं हूं। मैं लक्षणों के आधार पर संभावित स्थितियों का सुझाव दे सकता हूं, लेकिन कृपया उचित निदान के लिए स्वास्थ्य सेवा प्रदाता से सलाह लें।",
    'Telugu': "గమనిక: నేను వైద్య పరిజ్ఞానం కలిగిన వ్యక్తి కాదు. నేను లక్షణాల ఆధారంగా సంభావ్య పరిస్థితులను సూచించగలను, కానీ దయచేసి సరైన నిర్ధారణ కోసం హెల్త్కేర్ ప్రొవైడర్ను సంప్రదించండి."
}

# Regex patterns
duration_pattern = re.compile(r"\bfor\s+(\d+)\s+days?\b")
severity_pattern = re.compile(r"\b(mild|moderate|severe)\b")

# --- Helper functions ---
def extract_entities(text: str) -> Dict[str, str]:
    entities = {}
    d = duration_pattern.search(text)
    s = severity_pattern.search(text)
    if d:
        entities["duration"] = f"{d.group(1)} days"
    if s:
        entities["severity"] = s.group(1)
    return entities

def extract_symptoms(text: str) -> List[str]:
    found = []
    lower_text = text.lower().strip()
    
    # Check for exact matches and partial matches
    for symptom in SYMPTOM_TO_ILLNESSES.keys():
        symptom_lower = symptom.lower()
        # Check for exact match or word boundary match
        if (symptom_lower in lower_text and 
            (symptom_lower == lower_text or 
             f" {symptom_lower} " in f" {lower_text} " or
             lower_text.startswith(symptom_lower + " ") or
             lower_text.endswith(" " + symptom_lower))):
            if symptom not in found:
                found.append(symptom)
    
    return found

def add_symptoms(user_id: str, symptoms: List[str], entities: Dict[str, str]):
    session = user_sessions.setdefault(user_id, {"symptoms": set(), "entities": {}})
    for s in symptoms:
        session["symptoms"].add(s)
    for k, v in entities.items():
        if k not in session["entities"]:
            session["entities"][k] = v
    # ✅ ADDED: Save to file after updating
    save_sessions()

def detect_possible_illnesses(symptoms: List[str]) -> List[Tuple[str, int]]:
    matches = []
    sym_set = set(s.lower() for s in symptoms)
    for illness, info in KB.items():
        # Check symptoms in all languages
        all_symptoms = set()
        for key in ['symptoms', 'symptoms_hi', 'symptoms_te']:
            for symptom in info.get(key, []):
                all_symptoms.add(symptom.lower())
        
        common = sym_set & all_symptoms
        if len(common) > 0:
            matches.append((illness, len(common)))
    matches.sort(key=lambda x: x[1], reverse=True)
    return matches

def suggest_more_symptoms(current: List[str], language: str = "English") -> str:
    all_syms = set(SYMPTOM_TO_ILLNESSES.keys())
    remaining = list(all_syms - set(s.lower() for s in current))
    random.shuffle(remaining)
    
    if remaining:
        symptom_suggestion = remaining[0]
        if language == 'Hindi':
            return f"क्या आपको {symptom_suggestion} भी है?"
        elif language == 'Telugu':
            return f"మీకు {symptom_suggestion} కూడా ఉందా?"
        else:
            return f"Do you also have {symptom_suggestion}?"
    return ""

# --- Rule-based intent detection ---
def detect_rule_based_intent(msg: str) -> str:
    m = msg.lower()
    if any(w in m for w in ["hi", "hello", "hey", "namaste", "halo", "नमस्ते", "హలో"]):
        return "greet"
    if any(w in m for w in ["bye", "goodbye", "see you", "alvida", "vīḍkōlu", "अलविदा", "వీడ్కోలు"]):
        return "goodbye"
    if "stress" in m or "anxious" in m or "तनाव" in m or "ఒత్తిడి" in m:
        return "stress"
    if "sleep" in m or "tired" in m or "नींद" in m or "నిద్ర" in m:
        return "sleep"
    if "exercise" in m or "workout" in m or "व्यायाम" in m or "వ్యాయామం" in m:
        return "exercise"
    if any(p in m for p in ["what do i have", "diagnose", "so what do i have", "मुझे क्या है", "నాకు ఏమి ఉంది"]):
        return "diagnosis_query"
    return "unknown"

# --- Main bot logic ---
def get_bot_reply(user_id: str, user_message: str, intent: str = None, language: str = "English") -> str:
    # Auto-detect language from user message if not specified
    if language == "English":
        language = detect_input_language(user_message)
    
    if intent is None:
        intent = detect_rule_based_intent(user_message)

    # Greeting / Goodbye
    if intent == "greet":
        return random.choice(GREETINGS.get(language, GREETINGS['English']))
    if intent == "goodbye":
        if user_id in user_sessions:
            user_sessions.pop(user_id)
            save_sessions()
        return random.choice(GOODBYES.get(language, GOODBYES['English']))

    # Wellness tips
    if intent in ["stress", "sleep", "exercise"]:
        return format_health_info(KB.get(intent, {}), topic=intent, language=language)

    # Diagnosis query
    if intent == "diagnosis_query":
        sess = user_sessions.get(user_id, {"symptoms": set()})
        if not sess["symptoms"]:
            if language == 'Hindi':
                return "मेरे पास अभी तक पर्याप्त लक्षण नहीं हैं। कृपया मुझे बताएं कि आप क्या महसूस कर रहे हैं।"
            elif language == 'Telugu':
                return "నా వద్ద ఇంకా తగినంత లక్షణాలు లేవు. దయచేసి మీరు ఏమి అనుభవిస్తున్నారో చెప్పండి."
            else:
                return "I don't have enough symptoms yet. Please tell me what you're feeling."
        
        matches = detect_possible_illnesses(list(sess["symptoms"]))
        if not matches:
            if language == 'Hindi':
                return "मुझे सुझाव देने के लिए कुछ और लक्षण चाहिए।"
            elif language == 'Telugu':
                return "సూచించడానికి మరికొన్ని లక్షణాలు అవసరం."
            else:
                return "I need a few more symptoms to make a suggestion."
        return build_diagnosis_and_reset(user_id, matches, language)

    # Symptom handling
    new_syms = extract_symptoms(user_message)
    ents = extract_entities(user_message)
    if new_syms or ents:
        add_symptoms(user_id, new_syms, ents)

    sess = user_sessions.get(user_id, {"symptoms": set()})
    all_syms = list(sess["symptoms"])

    if len(all_syms) < 2:
        return random.choice(MORE_SYMPTOMS.get(language, MORE_SYMPTOMS['English']))

    matches = detect_possible_illnesses(all_syms)
    if matches and matches[0][1] >= 2:
        return build_diagnosis_and_reset(user_id, matches, language)

    more_symptoms_msg = suggest_more_symptoms(all_syms, language)
    if more_symptoms_msg:
        return more_symptoms_msg

    if language == 'Hindi':
        return "मुझे थोड़ी और जानकारी चाहिए। " + random.choice(MORE_SYMPTOMS.get(language, MORE_SYMPTOMS['English']))
    elif language == 'Telugu':
        return "కొంచెం మరింత సమాచారం కావాలి. " + random.choice(MORE_SYMPTOMS.get(language, MORE_SYMPTOMS['English']))
    else:
        return "I need a bit more information. " + random.choice(MORE_SYMPTOMS.get(language, MORE_SYMPTOMS['English']))

def build_diagnosis_and_reset(user_id: str, matches: List[Tuple[str, int]], language: str) -> str:
    top_matches = [m[0] for m in matches[:3]]
    
    parts = [DISCLAIMER.get(language, DISCLAIMER['English']), ""]
    
    for ill in top_matches:
        illness_info = KB.get(ill, {})
        formatted_info = format_health_info(illness_info, illness=ill, language=language)
        parts.append(formatted_info)
        parts.append("")
    
    # Add possible conditions summary
    if language == 'Hindi':
        parts.append(f"संभावित स्थितियां: {', '.join(top_matches)}")
    elif language == 'Telugu':
        parts.append(f"సాధ్యమయ్యే పరిస్థితులు: {', '.join(top_matches)}")
    else:
        parts.append(f"Possible conditions: {', '.join(top_matches)}")
    
    # Clear session after diagnosis
    if user_id in user_sessions:
        user_sessions.pop(user_id)
        save_sessions()

    return "\n".join(parts)
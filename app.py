import streamlit as st
import requests
import json
from datetime import datetime
from typing import Optional, Dict, List
import uuid

# ==========================================
# Configuration
# ==========================================
API_BASE_URL = st.secrets.get("API_BASE_URL", "http://localhost:8000")

# ==========================================
# API Client Functions
# ==========================================

class LuvvTappAPI:
    def __init__(self, base_url: str):
        self.base_url = base_url
    
    def health_check(self):
        try:
            response = requests.get(f"{self.base_url}/health")
            return response.json()
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def create_user(self, user_id: str, name: str, email: str, 
                   self_assessment: Optional[dict] = None):
        data = {
            "user_id": user_id,
            "name": name,
            "email": email
        }
        if self_assessment:
            data["self_assessment"] = self_assessment
        
        response = requests.post(f"{self.base_url}/api/users", json=data)
        return response.json()
    
    def get_user(self, user_id: str):
        response = requests.get(f"{self.base_url}/api/users/{user_id}")
        if response.status_code == 404:
            return None
        return response.json()
    
    def update_assessment(self, user_id: str, assessment: dict):
        response = requests.put(
            f"{self.base_url}/api/users/{user_id}/assessment",
            json=assessment
        )
        return response.json()
    
    def create_relationship(self, user_id: str, relationship_type: str,
                          partner_profile: dict):
        data = {
            "user_id": user_id,
            "relationship_type": relationship_type,
            "partner_profile": partner_profile
        }
        response = requests.post(f"{self.base_url}/api/relationships", json=data)
        return response.json()
    
    def get_relationships(self, user_id: str):
        response = requests.get(f"{self.base_url}/api/relationships/{user_id}")
        return response.json()
    
    def chat(self, user_id: str, message: str, 
             relationship_type: str = "general",
             partner_profile: Optional[dict] = None,
             self_assessment: Optional[dict] = None,
             session_id: Optional[str] = None):
        data = {
            "user_id": user_id,
            "message": message,
            "relationship_type": relationship_type
        }
        if partner_profile:
            data["partner_profile"] = partner_profile
        if self_assessment:
            data["self_assessment"] = self_assessment
        if session_id:
            data["session_id"] = session_id
        
        response = requests.post(f"{self.base_url}/api/chat", json=data)
        return response.json()
    
    def get_sessions(self, user_id: str):
        response = requests.get(f"{self.base_url}/api/sessions/{user_id}")
        return response.json()
    
    def get_session_history(self, session_id: str):
        response = requests.get(
            f"{self.base_url}/api/sessions/{session_id}/history"
        )
        return response.json()
    
    def delete_session(self, session_id: str):
        response = requests.delete(f"{self.base_url}/api/sessions/{session_id}")
        return response.json()

# ==========================================
# Initialize Session State
# ==========================================

def init_session_state():
    if 'user_id' not in st.session_state:
        st.session_state.user_id = str(uuid.uuid4())
    if 'user_profile' not in st.session_state:
        st.session_state.user_profile = None
    if 'current_session_id' not in st.session_state:
        st.session_state.current_session_id = None
    if 'messages' not in st.session_state:
        st.session_state.messages = []
    if 'api_client' not in st.session_state:
        st.session_state.api_client = LuvvTappAPI(API_BASE_URL)
    if 'selected_relationship' not in st.session_state:
        st.session_state.selected_relationship = None

# ==========================================
# Page Configuration
# ==========================================

st.set_page_config(
    page_title="LuvvTapp - Relationship Coach",
    page_icon="💙",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #FF6B9D;
        text-align: center;
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #666;
        text-align: center;
        margin-bottom: 2rem;
    }
    .chat-message {
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
    }
    .user-message {
        background-color: #E3F2FD;
        border-left: 4px solid #2196F3;
    }
    .assistant-message {
        background-color: #FCE4EC;
        border-left: 4px solid #FF6B9D;
    }
    .profile-card {
        background-color: #F5F5F5;
        padding: 1.5rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
    }
    .stButton>button {
        width: 100%;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# Initialize
# ==========================================
init_session_state()
api = st.session_state.api_client

# ==========================================
# Sidebar - User Profile & Settings
# ==========================================

with st.sidebar:
    st.markdown("### 👤 Your Profile")
    
    # Check if user exists
    user = api.get_user(st.session_state.user_id)
    
    if user is None:
        st.info("👋 Welcome! Let's create your profile.")
        
        with st.form("user_profile_form"):
            name = st.text_input("Your Name", placeholder="e.g., Alex")
            email = st.text_input("Email", placeholder="your@email.com")
            
            st.markdown("#### 🧠 Self-Assessment")
            personality_type = st.selectbox(
                "Personality Type (MBTI)",
                ["Not sure", "INTJ", "INTP", "ENTJ", "ENTP", "INFJ", "INFP", 
                 "ENFJ", "ENFP", "ISTJ", "ISFJ", "ESTJ", "ESFJ", 
                 "ISTP", "ISFP", "ESTP", "ESFP"]
            )
            
            love_language = st.selectbox(
                "Your Love Language",
                ["Not sure", "Words of Affirmation", "Quality Time", 
                 "Receiving Gifts", "Acts of Service", "Physical Touch"]
            )
            
            communication_style = st.text_input(
                "Communication Style",
                placeholder="e.g., Direct and honest"
            )
            
            submitted = st.form_submit_button("Create Profile")
            
            if submitted and name and email:
                assessment = {}
                if personality_type != "Not sure":
                    assessment["personality_type"] = personality_type
                if love_language != "Not sure":
                    assessment["love_language"] = love_language
                if communication_style:
                    assessment["communication_style"] = communication_style
                
                try:
                    result = api.create_user(
                        st.session_state.user_id,
                        name,
                        email,
                        assessment if assessment else None
                    )
                    st.success("✅ Profile created!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")
    else:
        st.session_state.user_profile = user
        st.markdown(f"**Name:** {user.get('name', 'N/A')}")
        st.markdown(f"**Email:** {user.get('email', 'N/A')}")
        
        if 'self_assessment' in user and user['self_assessment']:
            assessment = user['self_assessment']
            st.markdown("**Your Profile:**")
            if 'personality_type' in assessment:
                st.markdown(f"🧠 {assessment['personality_type']}")
            if 'love_language' in assessment:
                st.markdown(f"💙 {assessment['love_language']}")
        
        if st.button("✏️ Edit Profile"):
            st.session_state.edit_profile = True
    
    st.divider()
    
    # Relationships
    st.markdown("### 💑 Relationships")
    
    if user:
        relationships = api.get_relationships(st.session_state.user_id)
        
        if relationships and 'relationships' in relationships:
            for rel in relationships['relationships']:
                partner_name = rel.get('partner_profile', {}).get('name', 'Unknown')
                rel_type = rel.get('relationship_type', 'general')
                
                col1, col2 = st.columns([3, 1])
                with col1:
                    if st.button(f"💕 {partner_name}", key=f"rel_{rel_type}"):
                        st.session_state.selected_relationship = rel
                        st.session_state.current_session_id = None
                        st.session_state.messages = []
        
        if st.button("➕ Add Relationship"):
            st.session_state.add_relationship = True
    
    st.divider()
    
    # Settings
    st.markdown("### ⚙️ Settings")
    
    if st.button("🗑️ Clear Chat History"):
        st.session_state.messages = []
        st.session_state.current_session_id = None
        st.success("Chat cleared!")
    
    if st.button("🔄 New Session"):
        st.session_state.current_session_id = None
        st.session_state.messages = []
        st.session_state.selected_relationship = None
        st.rerun()
    
    # API Status
    st.divider()
    health = api.health_check()
    if health.get('status') == 'healthy':
        st.success("🟢 API Connected")
    else:
        st.error("🔴 API Disconnected")

# ==========================================
# Modal for Adding Relationship
# ==========================================

if st.session_state.get('add_relationship'):
    with st.form("add_relationship_form"):
        st.markdown("### Add a Relationship")
        
        relationship_type = st.selectbox(
            "Relationship Type",
            ["romantic", "friendship", "family", "self-growth"]
        )
        
        partner_name = st.text_input("Their Name", placeholder="e.g., Jordan")
        
        partner_personality = st.selectbox(
            "Their Personality Type",
            ["Not sure", "INTJ", "INTP", "ENTJ", "ENTP", "INFJ", "INFP", 
             "ENFJ", "ENFP", "ISTJ", "ISFJ", "ESTJ", "ESFJ", 
             "ISTP", "ISFP", "ESTP", "ESFP"]
        )
        
        partner_love_language = st.selectbox(
            "Their Love Language",
            ["Not sure", "Words of Affirmation", "Quality Time", 
             "Receiving Gifts", "Acts of Service", "Physical Touch"]
        )
        
        interests = st.text_input(
            "Their Interests (comma-separated)",
            placeholder="e.g., hiking, cooking, music"
        )
        
        col1, col2 = st.columns(2)
        with col1:
            submitted = st.form_submit_button("Add Relationship")
        with col2:
            cancelled = st.form_submit_button("Cancel")
        
        if submitted and partner_name:
            partner_profile = {"name": partner_name}
            
            if partner_personality != "Not sure":
                partner_profile["personality_type"] = partner_personality
            if partner_love_language != "Not sure":
                partner_profile["love_language"] = partner_love_language
            if interests:
                partner_profile["interests"] = [i.strip() for i in interests.split(",")]
            
            try:
                api.create_relationship(
                    st.session_state.user_id,
                    relationship_type,
                    partner_profile
                )
                st.success(f"✅ Added {partner_name}!")
                st.session_state.add_relationship = False
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")
        
        if cancelled:
            st.session_state.add_relationship = False
            st.rerun()

# ==========================================
# Main Content Area
# ==========================================

# Header
st.markdown('<div class="main-header">💙 LuvvTapp</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="sub-header">Your Virtual Relationship Coach</div>', 
    unsafe_allow_html=True
)

# Check if user profile exists
if not st.session_state.user_profile:
    st.info("👈 Please create your profile in the sidebar to get started!")
    st.stop()

# Display selected relationship context
if st.session_state.selected_relationship:
    rel = st.session_state.selected_relationship
    partner = rel.get('partner_profile', {})
    rel_type = rel.get('relationship_type', 'general')
    
    st.markdown(f"""
    <div class="profile-card">
        <h4>💕 Current Context: {partner.get('name', 'Unknown')} ({rel_type.title()})</h4>
        {f"<p>🧠 Personality: {partner.get('personality_type', 'N/A')}</p>" if partner.get('personality_type') else ""}
        {f"<p>💙 Love Language: {partner.get('love_language', 'N/A')}</p>" if partner.get('love_language') else ""}
    </div>
    """, unsafe_allow_html=True)

# Chat Interface
st.markdown("### 💬 Chat with Your Coach")

# Display chat messages
for message in st.session_state.messages:
    role = message["role"]
    content = message["content"]
    
    if role == "user":
        st.markdown(
            f'<div class="chat-message user-message"><b>You:</b><br>{content}</div>',
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            f'<div class="chat-message assistant-message"><b>🤖 Coach:</b><br>{content}</div>',
            unsafe_allow_html=True
        )

# Chat input
user_input = st.chat_input("Ask your relationship coach anything...")

if user_input:
    # Add user message to display
    st.session_state.messages.append({
        "role": "user",
        "content": user_input
    })
    
    # Prepare API request
    relationship_type = "general"
    partner_profile = None
    
    if st.session_state.selected_relationship:
        rel = st.session_state.selected_relationship
        relationship_type = rel.get('relationship_type', 'general')
        partner_profile = rel.get('partner_profile')
    
    self_assessment = None
    if st.session_state.user_profile and 'self_assessment' in st.session_state.user_profile:
        self_assessment = st.session_state.user_profile['self_assessment']
    
    # Show loading spinner
    with st.spinner("🤔 Coach is thinking..."):
        try:
            response = api.chat(
                user_id=st.session_state.user_id,
                message=user_input,
                relationship_type=relationship_type,
                partner_profile=partner_profile,
                self_assessment=self_assessment,
                session_id=st.session_state.current_session_id
            )
            
            # Update session ID
            if not st.session_state.current_session_id:
                st.session_state.current_session_id = response['session_id']
            
            # Add assistant response
            st.session_state.messages.append({
                "role": "assistant",
                "content": response['response']
            })
            
            st.rerun()
            
        except Exception as e:
            st.error(f"Error communicating with coach: {e}")

# ==========================================
# Quick Actions
# ==========================================

if not st.session_state.messages:
    st.markdown("### 💡 Need some inspiration?")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("💬 Communication Tips"):
            st.session_state.messages.append({
                "role": "user",
                "content": "Can you give me some tips for better communication in my relationship?"
            })
            st.rerun()
    
    with col2:
        if st.button("💝 Date Ideas"):
            st.session_state.messages.append({
                "role": "user",
                "content": "What are some creative date ideas for us?"
            })
            st.rerun()
    
    with col3:
        if st.button("🤝 Conflict Resolution"):
            st.session_state.messages.append({
                "role": "user",
                "content": "How can we resolve conflicts in a healthy way?"
            })
            st.rerun()

# ==========================================
# Footer
# ==========================================

st.divider()
st.markdown(
    """
    <div style="text-align: center; color: #999; font-size: 0.9rem;">
        💙 LuvvTapp - Building stronger relationships through AI-powered guidance<br>
        Remember: I'm an AI coach, not a licensed therapist. For serious concerns, please seek professional help.
    </div>
    """,
    unsafe_allow_html=True
)
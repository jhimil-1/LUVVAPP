# config.py
# Advanced configuration and utilities for LuvvTapp

from pydantic_settings import BaseSettings
from typing import Optional, List
from functools import lru_cache
import os

class Settings(BaseSettings):
    """Application settings"""
    
    # API Settings
    app_name: str = "LuvvTapp Virtual Relationship Coach"
    app_version: str = "1.0.0"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    debug: bool = False
    
    # OpenAI Settings
    openai_api_key: str
    openai_model: str = "gpt-4o-mini"
    openai_temperature: float = 0.8
    openai_max_tokens: int = 500
    
    # MongoDB Settings
    mongodb_url: str
    database_name: str = "luvvtapp_db"
    
    # CORS Settings
    cors_origins: List[str] = ["*"]
    
    # Rate Limiting (messages per hour)
    rate_limit_per_hour: int = 100
    
    # Session Settings
    max_conversation_history: int = 10  # Keep last N messages
    session_timeout_hours: int = 24
    
    # Feature Flags
    enable_web_search: bool = False  # For future OpenAI web search integration
    enable_analytics: bool = True
    
    class Config:
        env_file = ".env"
        case_sensitive = False

@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


# ==========================================
# Prompt Templates
# ==========================================

RELATIONSHIP_TYPE_CONTEXTS = {
    "romantic": """
You're helping with a romantic relationship. Focus on:
- Emotional intimacy and connection
- Communication between partners
- Conflict resolution and compromise
- Quality time and shared experiences
- Physical and emotional needs
- Trust and vulnerability
""",
    "friendship": """
You're helping with a friendship. Focus on:
- Maintaining healthy boundaries
- Mutual support and understanding
- Shared interests and activities
- Communication and honesty
- Handling conflicts respectfully
- Growing together while respecting differences
""",
    "family": """
You're helping with a family relationship. Focus on:
- Understanding generational differences
- Setting healthy boundaries
- Managing expectations
- Improving communication
- Respecting individual needs
- Building stronger family bonds
""",
    "self-growth": """
You're helping with personal development and self-relationship. Focus on:
- Self-awareness and reflection
- Emotional intelligence
- Setting personal boundaries
- Self-compassion and care
- Personal values and goals
- Building confidence and self-worth
"""
}

LOVE_LANGUAGE_TIPS = {
    "Words of Affirmation": """
Your partner values verbal encouragement and appreciation. Remember to:
- Express your feelings verbally
- Give genuine compliments
- Write thoughtful notes or messages
- Acknowledge their efforts
- Say "I love you" and explain why
""",
    "Quality Time": """
Your partner values undivided attention. Remember to:
- Plan regular one-on-one time
- Be fully present (put phones away)
- Engage in meaningful conversations
- Share activities you both enjoy
- Make eye contact and actively listen
""",
    "Receiving Gifts": """
Your partner values thoughtful gestures. Remember to:
- Give meaningful, personal gifts
- Remember important dates
- The thought matters more than cost
- Small surprises show you care
- Keep mementos that remind you of them
""",
    "Acts of Service": """
Your partner values helpful actions. Remember to:
- Help with tasks or chores
- Anticipate their needs
- Follow through on promises
- Take initiative without being asked
- Make their day easier
""",
    "Physical Touch": """
Your partner values physical connection. Remember to:
- Offer hugs, kisses, and cuddles
- Hold hands when walking
- Sit close together
- Give massages or back rubs
- Be affectionate in appropriate ways
"""
}

PERSONALITY_TYPE_INSIGHTS = {
    "INTJ": "Strategic, independent, values logic and planning",
    "INTP": "Analytical, curious, values knowledge and understanding",
    "ENTJ": "Decisive, assertive, values efficiency and achievement",
    "ENTP": "Innovative, debater, values intellectual challenge",
    "INFJ": "Insightful, empathetic, values meaningful connections",
    "INFP": "Idealistic, creative, values authenticity and harmony",
    "ENFJ": "Charismatic, supportive, values helping others grow",
    "ENFP": "Enthusiastic, creative, values freedom and authenticity",
    "ISTJ": "Responsible, organized, values tradition and stability",
    "ISFJ": "Caring, detail-oriented, values loyalty and support",
    "ESTJ": "Practical, organized, values order and results",
    "ESFJ": "Warm, cooperative, values harmony and helping others",
    "ISTP": "Practical, flexible, values freedom and hands-on work",
    "ISFP": "Artistic, sensitive, values self-expression and peace",
    "ESTP": "Energetic, pragmatic, values action and adventure",
    "ESFP": "Spontaneous, fun-loving, values experience and connection"
}


# ==========================================
# Response Templates
# ==========================================

CRISIS_RESPONSE = """
I notice you might be going through something difficult. While I'm here to support you with relationship guidance, I want to make sure you have access to professional help if you need it.

If you're experiencing a crisis, please reach out to:
- National Suicide Prevention Lifeline: 988 (US)
- Crisis Text Line: Text HOME to 741741
- International Association for Suicide Prevention: https://www.iasp.info/resources/Crisis_Centres/

Would you like to talk about what's going on, or would you prefer some gentle conversation instead?
"""

DISCLAIMER = """
💙 Remember: I'm an AI relationship coach — I can guide and support you, but I'm not a licensed therapist. For serious mental health concerns, please reach out to a qualified professional.
"""


# ==========================================
# Utility Functions
# ==========================================

def build_enhanced_prompt(
    relationship_type: str,
    partner_profile: Optional[dict] = None,
    self_assessment: Optional[dict] = None,
    conversation_context: str = ""
) -> str:
    """Build enhanced system prompt with detailed context"""
    
    base = """You are LuvvTapp's Virtual Relationship Coach, an intelligent, empathetic AI. 
Your purpose is to help users build, strengthen, and maintain meaningful personal relationships.

Core Principles:
- Tone: Empathetic, supportive, positive, non-judgmental
- Voice: Wise, understanding, approachable yet insightful
- Guide with kindness and reflection, not authority
- Speak naturally and authentically, avoid clichés
- Use affirmations and practical examples
- Keep responses conversational (2-4 paragraphs)
- Ask clarifying questions when helpful

Boundaries:
- Avoid explicit, sexual, or harmful content
- Don't diagnose or provide therapy
- Encourage positive communication and personal agency
- Suggest professional help for serious concerns
"""
    
    # Add relationship type context
    if relationship_type in RELATIONSHIP_TYPE_CONTEXTS:
        base += "\n" + RELATIONSHIP_TYPE_CONTEXTS[relationship_type]
    
    # Add love language tips
    if partner_profile and "love_language" in partner_profile:
        lang = partner_profile["love_language"]
        if lang in LOVE_LANGUAGE_TIPS:
            base += f"\n\nPartner's Love Language ({lang}):\n{LOVE_LANGUAGE_TIPS[lang]}"
    
    # Add personality insights
    if partner_profile and "personality_type" in partner_profile:
        ptype = partner_profile["personality_type"]
        if ptype in PERSONALITY_TYPE_INSIGHTS:
            base += f"\n\nPartner's Personality ({ptype}): {PERSONALITY_TYPE_INSIGHTS[ptype]}"
    
    if self_assessment and "personality_type" in self_assessment:
        ptype = self_assessment["personality_type"]
        if ptype in PERSONALITY_TYPE_INSIGHTS:
            base += f"\n\nUser's Personality ({ptype}): {PERSONALITY_TYPE_INSIGHTS[ptype]}"
    
    # Add conversation context
    if conversation_context:
        base += f"\n\nConversation Context:\n{conversation_context}"
    
    base += f"\n\n{DISCLAIMER}"
    
    return base


def detect_crisis_keywords(message: str) -> bool:
    """Detect if message contains crisis keywords"""
    crisis_keywords = [
        "suicide", "kill myself", "want to die", "end it all",
        "no reason to live", "better off dead", "harm myself",
        "can't go on", "no way out"
    ]
    message_lower = message.lower()
    return any(keyword in message_lower for keyword in crisis_keywords)


# ==========================================
# Export all
# ==========================================
__all__ = [
    'Settings',
    'get_settings',
    'RELATIONSHIP_TYPE_CONTEXTS',
    'LOVE_LANGUAGE_TIPS',
    'PERSONALITY_TYPE_INSIGHTS',
    'CRISIS_RESPONSE',
    'DISCLAIMER',
    'build_enhanced_prompt',
    'detect_crisis_keywords'
]
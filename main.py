# main.py
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient
from openai import AsyncOpenAI
import os
from bson import ObjectId
from contextlib import asynccontextmanager

# ======================
# Configuration
# ======================
MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DATABASE_NAME = "luvvtapp_db"

# Global clients
mongo_client: Optional[AsyncIOMotorClient] = None
openai_client: Optional[AsyncOpenAI] = None

# ======================
# Lifespan Management
# ======================
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    global mongo_client, openai_client
    mongo_client = AsyncIOMotorClient(MONGODB_URL)
    if OPENAI_API_KEY:
        openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None
    else:
        # Defer validation to request time; this allows the app to start even if the key isn't set
        openai_client = AsyncOpenAI()
    
    # Test connections
    try:
        await mongo_client.admin.command('ping')
        print("✅ MongoDB connected successfully")
    except Exception as e:
        print(f"❌ MongoDB connection failed: {e}")
    
    yield
    
    # Shutdown
    if mongo_client:
        mongo_client.close()
        print("✅ MongoDB connection closed")

# ======================
# FastAPI App
# ======================
app = FastAPI(
    title="LuvvTapp Virtual Relationship Coach",
    description="AI-powered relationship coaching API",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ======================
# Database Helper
# ======================
def get_database():
    return mongo_client[DATABASE_NAME]

# ======================
# Pydantic Models
# ======================
class PartnerProfile(BaseModel):
    name: Optional[str] = None
    personality_type: Optional[str] = None
    love_language: Optional[str] = None
    communication_style: Optional[str] = None
    interests: Optional[List[str]] = []
    preferences: Optional[Dict[str, Any]] = {}

class SelfAssessment(BaseModel):
    personality_type: Optional[str] = None
    love_language: Optional[str] = None
    emotional_patterns: Optional[List[str]] = []
    communication_style: Optional[str] = None
    strengths: Optional[List[str]] = []
    growth_areas: Optional[List[str]] = []

class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class ChatRequest(BaseModel):
    user_id: str
    message: str
    relationship_type: Optional[str] = "general"  # romantic, friendship, family, self-growth
    partner_profile: Optional[PartnerProfile] = None
    self_assessment: Optional[SelfAssessment] = None
    session_id: Optional[str] = None

class ChatResponse(BaseModel):
    session_id: str
    response: str
    timestamp: datetime
    tokens_used: Optional[int] = None

class UserProfile(BaseModel):
    user_id: str
    name: str
    email: str
    self_assessment: Optional[SelfAssessment] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class RelationshipProfile(BaseModel):
    user_id: str
    relationship_type: str
    partner_profile: PartnerProfile
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

# ======================
# System Prompt Builder
# ======================
def build_system_prompt(
    relationship_type: str,
    partner_profile: Optional[PartnerProfile] = None,
    self_assessment: Optional[SelfAssessment] = None
) -> str:
    base_prompt = """You are LuvvTapp's Virtual Relationship Coach, an intelligent, empathetic AI. Your purpose is to help users build, strengthen, and maintain meaningful personal relationships of any kind — romantic, family, friendship, or self-development.

Core Principles:
- Tone: Empathetic, supportive, positive, non-judgmental
- Voice: Wise, understanding human relationship coach — approachable but insightful
- Guide with kindness and reflection, not authority
- Avoid clichés; speak naturally and authentically
- Use affirmations and practical examples

Boundaries:
- Avoid explicit, sexual, or harmful content
- Avoid therapy, diagnosis, or mental health claims
- Always encourage positive communication and personal agency
- Suggest seeking professional help if user expresses severe emotional distress

Include this disclaimer at least once per session:
"I'm an AI relationship coach — I can guide and support you, but I'm not a licensed therapist."
"""
    
    context_parts = [base_prompt]
    
    # Add relationship type context
    context_parts.append(f"\nCurrent Relationship Context: {relationship_type}")
    
    # Add partner profile if available
    if partner_profile:
        profile_info = []
        if partner_profile.name:
            profile_info.append(f"Partner's name: {partner_profile.name}")
        if partner_profile.personality_type:
            profile_info.append(f"Personality type: {partner_profile.personality_type}")
        if partner_profile.love_language:
            profile_info.append(f"Love language: {partner_profile.love_language}")
        if partner_profile.communication_style:
            profile_info.append(f"Communication style: {partner_profile.communication_style}")
        if partner_profile.interests:
            profile_info.append(f"Interests: {', '.join(partner_profile.interests)}")
        
        if profile_info:
            context_parts.append("\nPartner Profile:\n" + "\n".join(profile_info))
    
    # Add self-assessment if available
    if self_assessment:
        assessment_info = []
        if self_assessment.personality_type:
            assessment_info.append(f"Your personality type: {self_assessment.personality_type}")
        if self_assessment.love_language:
            assessment_info.append(f"Your love language: {self_assessment.love_language}")
        if self_assessment.communication_style:
            assessment_info.append(f"Your communication style: {self_assessment.communication_style}")
        if self_assessment.strengths:
            assessment_info.append(f"Your strengths: {', '.join(self_assessment.strengths)}")
        if self_assessment.growth_areas:
            assessment_info.append(f"Areas for growth: {', '.join(self_assessment.growth_areas)}")
        
        if assessment_info:
            context_parts.append("\nYour Self-Assessment:\n" + "\n".join(assessment_info))
    
    return "\n".join(context_parts)

# ======================
# API Endpoints
# ======================

@app.get("/")
async def root():
    return {
        "message": "LuvvTapp Virtual Relationship Coach API",
        "status": "running",
        "version": "1.0.0"
    }

@app.get("/health")
async def health_check():
    db_status = "connected"
    try:
        await mongo_client.admin.command('ping')
    except:
        db_status = "disconnected"
    
    return {
        "status": "healthy",
        "database": db_status,
        "openai": "configured" if os.getenv("OPENAI_API_KEY") else "not configured"
    }

@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, db=Depends(get_database)):
    """
    Main chat endpoint - handles conversation with the AI coach
    """
    api_key = os.getenv("OPENAI_API_KEY") or OPENAI_API_KEY
    if not api_key:
        raise HTTPException(status_code=503, detail="OpenAI API key not configured. Set the OPENAI_API_KEY environment variable and restart the server.")
    client = AsyncOpenAI(api_key=api_key)
    try:
        # Get or create session
        sessions_collection = db.chat_sessions
        
        if request.session_id:
            session = await sessions_collection.find_one({"session_id": request.session_id})
        else:
            # Create new session
            session_id = str(ObjectId())
            context_type = "partner" if (request.partner_profile is not None and request.relationship_type != "general") else "general"
            session = {
                "session_id": session_id,
                "user_id": request.user_id,
                "relationship_type": request.relationship_type,
                "context_type": context_type,
                "partner_profile": request.partner_profile.dict() if request.partner_profile else None,
                "messages": [],
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            request.session_id = session_id
        
        # Build conversation history
        messages = []
        
        # Add system prompt
        system_prompt = build_system_prompt(
            request.relationship_type,
            request.partner_profile,
            request.self_assessment
        )
        messages.append({"role": "system", "content": system_prompt})
        
        # Add conversation history (last 10 messages to manage context)
        if session and "messages" in session:
            for msg in session["messages"][-10:]:
                messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
        
        # Add current user message
        messages.append({"role": "user", "content": request.message})
        
        # Call OpenAI API
        response = await client.chat.completions.create(
            model="gpt-4o-mini",  # Use gpt-4o for better quality or gpt-3.5-turbo for cost efficiency
            messages=messages,
            temperature=0.8,
            max_tokens=500,
            presence_penalty=0.6,
            frequency_penalty=0.3
        )
        
        assistant_message = response.choices[0].message.content
        tokens_used = response.usage.total_tokens
        
        # Update session in database
        if "messages" not in session:
            session["messages"] = []
        # Keep relationship/context fresh
        session["relationship_type"] = request.relationship_type
        session["context_type"] = "partner" if (request.partner_profile is not None and request.relationship_type != "general") else session.get("context_type", "general")
        if request.partner_profile:
            session["partner_profile"] = request.partner_profile.dict()
        
        session["messages"].append({
            "role": "user",
            "content": request.message,
            "timestamp": datetime.utcnow()
        })
        session["messages"].append({
            "role": "assistant",
            "content": assistant_message,
            "timestamp": datetime.utcnow()
        })
        session["updated_at"] = datetime.utcnow()
        
        # Upsert session
        await sessions_collection.update_one(
            {"session_id": request.session_id},
            {"$set": session},
            upsert=True
        )
        
        return ChatResponse(
            session_id=request.session_id,
            response=assistant_message,
            timestamp=datetime.utcnow(),
            tokens_used=tokens_used
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat error: {str(e)}")

@app.post("/api/users", status_code=201)
async def create_user(profile: UserProfile, db=Depends(get_database)):
    """
    Create a new user profile
    """
    users_collection = db.users
    
    # Check if user exists
    existing = await users_collection.find_one({"user_id": profile.user_id})
    if existing:
        raise HTTPException(status_code=400, detail="User already exists")
    
    user_dict = profile.dict()
    await users_collection.insert_one(user_dict)
    
    return {"message": "User created successfully", "user_id": profile.user_id}

@app.get("/api/users/{user_id}")
async def get_user(user_id: str, db=Depends(get_database)):
    """
    Get user profile
    """
    users_collection = db.users
    user = await users_collection.find_one({"user_id": user_id}, {"_id": 0})
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return user

@app.put("/api/users/{user_id}/assessment")
async def update_self_assessment(
    user_id: str,
    assessment: SelfAssessment,
    db=Depends(get_database)
):
    """
    Update user's self-assessment
    """
    users_collection = db.users
    
    result = await users_collection.update_one(
        {"user_id": user_id},
        {"$set": {"self_assessment": assessment.dict()}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {"message": "Self-assessment updated successfully"}

@app.post("/api/relationships", status_code=201)
async def create_relationship(
    relationship: RelationshipProfile,
    db=Depends(get_database)
):
    """
    Create or update a relationship profile
    """
    relationships_collection = db.relationships
    
    relationship_dict = relationship.dict()
    relationship_dict["updated_at"] = datetime.utcnow()
    
    await relationships_collection.update_one(
        {
            "user_id": relationship.user_id,
            "relationship_type": relationship.relationship_type
        },
        {"$set": relationship_dict},
        upsert=True
    )
    
    return {"message": "Relationship profile saved successfully"}

@app.get("/api/relationships/{user_id}")
async def get_relationships(user_id: str, db=Depends(get_database)):
    """
    Get all relationship profiles for a user
    """
    relationships_collection = db.relationships
    relationships = await relationships_collection.find(
        {"user_id": user_id},
        {"_id": 0}
    ).to_list(length=100)
    
    return {"relationships": relationships}

@app.get("/api/sessions/{user_id}")
async def get_user_sessions(user_id: str, db=Depends(get_database)):
    """
    Get all chat sessions for a user
    """
    sessions_collection = db.chat_sessions
    sessions = await sessions_collection.find(
        {"user_id": user_id},
        {"_id": 0, "messages": 0}  # Exclude messages for list view
    ).sort("updated_at", -1).to_list(length=50)
    
    return {"sessions": sessions}

@app.get("/api/sessions/{session_id}/history")
async def get_session_history(session_id: str, db=Depends(get_database)):
    """
    Get full conversation history for a session
    """
    sessions_collection = db.chat_sessions
    session = await sessions_collection.find_one(
        {"session_id": session_id},
        {"_id": 0}
    )
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return session

@app.delete("/api/sessions/{session_id}")
async def delete_session(session_id: str, db=Depends(get_database)):
    """
    Delete a chat session
    """
    sessions_collection = db.chat_sessions
    result = await sessions_collection.delete_one({"session_id": session_id})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {"message": "Session deleted successfully"}

# ======================
# Run with: uvicorn main:app --reload
# ======================
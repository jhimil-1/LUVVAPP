# main.py
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient
from openai import AsyncOpenAI, APIConnectionError, APIStatusError, RateLimitError, AuthenticationError
import os
from bson import ObjectId
from contextlib import asynccontextmanager
from dotenv import load_dotenv
import logging
import httpx
import bcrypt

# Load variables from .env if present
load_dotenv()
# Basic logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

# ======================
# Configuration
# ======================
MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DATABASE_NAME = os.getenv("DATABASE_NAME", "luvvtapp_db")
SESSIONS_COLLECTION = os.getenv("COLLECTION_NAME", "session")

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
    api_key = (os.getenv("OPENAI_API_KEY") or OPENAI_API_KEY or "").strip()
    if api_key:
        if any(ch.isspace() for ch in api_key):
            raise Exception("OPENAI_API_KEY contains whitespace/newlines. Fix your .env so the key is a single line with no trailing spaces.")
        openai_client = AsyncOpenAI(api_key=api_key) if api_key else None
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
    relationship_values: Optional[List[str]] = []

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

class AdviceRequest(BaseModel):
    user_id: str
    topic: str
    situation: str
    partner_profile: Optional[PartnerProfile] = None
    self_assessment: Optional[SelfAssessment] = None

class AdviceResponse(BaseModel):
    advice_id: str
    topic: str
    content: str
    created_at: datetime

class CreateOrLoginRequest(BaseModel):
    name: str
    email: str
    self_assessment: Optional[SelfAssessment] = None

class SignupRequest(BaseModel):
    name: str
    email: str
    password: str
    self_assessment: Optional[SelfAssessment] = None

class LoginRequest(BaseModel):
    email: str
    password: str

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
        if getattr(self_assessment, 'relationship_values', None):
            assessment_info.append(f"What matters most in relationships: {', '.join(self_assessment.relationship_values)}")
        
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
    api_key = (os.getenv("OPENAI_API_KEY") or OPENAI_API_KEY or "").strip()
    key_env = api_key
    key_present = bool(key_env)
    if key_present and any(ch.isspace() for ch in api_key):
        key_present = False
    return {
        "status": "healthy",
        "database": db_status,
        "openai": "configured" if key_present else "not configured"
    }

@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, db=Depends(get_database)):
    """
    Main chat endpoint - handles conversation with the AI coach
    """
    try:
        # Get or create session
        sessions_collection = db[SESSIONS_COLLECTION]
        
        if request.session_id:
            session = await sessions_collection.find_one({"session_id": request.session_id})
            if not session:
                # Provided session_id doesn't exist; create a new session
                session_id = request.session_id
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

        # Ensure session exists in DB and append the user message before calling OpenAI
        await sessions_collection.update_one(
            {"session_id": request.session_id},
            {
                "$setOnInsert": {
                    "session_id": request.session_id,
                    "user_id": request.user_id,
                    "created_at": session.get("created_at", datetime.utcnow()),
                },
                "$set": {
                    "relationship_type": request.relationship_type,
                    "context_type": ("partner" if (request.partner_profile is not None and request.relationship_type != "general") else session.get("context_type", "general")),
                    "partner_profile": (request.partner_profile.dict() if request.partner_profile else session.get("partner_profile")),
                    "updated_at": datetime.utcnow(),
                },
                "$push": {
                    "messages": {
                        "role": "user",
                        "content": request.message,
                        "timestamp": datetime.utcnow(),
                    }
                }
            },
            upsert=True,
        )
        
        # Prepare OpenAI client (after persisting user message)
        api_key = (os.getenv("OPENAI_API_KEY") or OPENAI_API_KEY or "").strip()
        if not api_key:
            raise HTTPException(status_code=503, detail="OpenAI API key not configured. Set the OPENAI_API_KEY environment variable and restart the server.")
        if any(ch.isspace() for ch in api_key):
            raise HTTPException(status_code=401, detail="Chat error: OPENAI_API_KEY contains whitespace/newlines. Fix your .env so the key is a single line with no trailing spaces.")
        client = AsyncOpenAI(api_key=api_key, timeout=httpx.Timeout(20.0, read=60.0))
        # Call OpenAI API
        completion = await client.chat.completions.create(
            model="gpt-4o-mini",  # Use gpt-4o for better quality or gpt-3.5-turbo for cost efficiency
            messages=messages,
            temperature=0.8,
            max_tokens=500,
            presence_penalty=0.6,
            frequency_penalty=0.3
        )
        assistant_message = (completion.choices[0].message.content or "").strip()
        tokens_used = getattr(getattr(completion, "usage", None), "total_tokens", None)
        
        # Append assistant message and update timestamps in database
        await sessions_collection.update_one(
            {"session_id": request.session_id},
            {
                "$push": {
                    "messages": {
                        "role": "assistant",
                        "content": assistant_message,
                        "timestamp": datetime.utcnow(),
                    }
                },
                "$set": {
                    "relationship_type": request.relationship_type,
                    "context_type": ("partner" if (request.partner_profile is not None and request.relationship_type != "general") else "general"),
                    "partner_profile": (request.partner_profile.dict() if request.partner_profile else None),
                    "updated_at": datetime.utcnow(),
                },
            },
            upsert=True,
        )
        
        return ChatResponse(
            session_id=request.session_id,
            response=assistant_message,
            timestamp=datetime.utcnow(),
            tokens_used=tokens_used
        )
        
    except AuthenticationError as e:
        logging.exception("OpenAI auth error (check OPENAI_API_KEY)")
        raise HTTPException(status_code=401, detail="Chat error: OpenAI authentication failed. Check OPENAI_API_KEY.")
    except (APIConnectionError, httpx.ConnectError, httpx.ConnectTimeout) as e:
        logging.exception("OpenAI connection error in chat")
        raise HTTPException(status_code=503, detail="Chat error: Connection to OpenAI failed.")
    except httpx.ReadTimeout as e:
        logging.exception("OpenAI read timeout in chat")
        raise HTTPException(status_code=504, detail="Chat error: OpenAI read timeout.")
    except RateLimitError as e:
        logging.exception("OpenAI rate limit in chat")
        raise HTTPException(status_code=429, detail="Chat error: OpenAI rate limit exceeded.")
    except APIStatusError as e:
        logging.exception("OpenAI API status error in chat")
        raise HTTPException(status_code=502, detail=f"Chat error: OpenAI API error {getattr(e, 'status_code', '')}.")
    except Exception as e:
        logging.exception("Unhandled chat error")
        raise HTTPException(status_code=500, detail=f"Chat error: {str(e)}")

@app.post("/api/users")
async def create_or_login_user(payload: CreateOrLoginRequest, db=Depends(get_database)):
    users_collection = db.users
    normalized_email = (payload.email or "").strip().lower()
    existing = await users_collection.find_one({"email": normalized_email}, {"_id": 0})
    if existing:
        return {"message": "User exists", "user_id": existing["user_id"], "profile": existing}
    user_id = str(ObjectId())
    doc = {
        "user_id": user_id,
        "name": payload.name,
        "email": normalized_email,
        "self_assessment": payload.self_assessment.dict() if payload.self_assessment else None,
        "created_at": datetime.utcnow(),
    }
    await users_collection.insert_one(doc)
    profile = await users_collection.find_one({"user_id": user_id}, {"_id": 0, "password_hash": 0})
    return {"message": "User created successfully", "user_id": user_id, "profile": profile}

@app.post("/api/auth/signup")
async def signup(payload: SignupRequest, db=Depends(get_database)):
    users = db.users
    normalized_email = (payload.email or "").strip().lower()
    existing = await users.find_one({"email": normalized_email})
    password_hash = bcrypt.hashpw(payload.password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    if existing:
        # Allow legacy users (no password_hash) to set a password on signup
        if not existing.get("password_hash"):
            await users.update_one(
                {"email": normalized_email},
                {"$set": {
                    "name": payload.name or existing.get("name"),
                    "password_hash": password_hash,
                    "self_assessment": payload.self_assessment.dict() if payload.self_assessment else existing.get("self_assessment"),
                }}
            )
            profile = await users.find_one({"user_id": existing["user_id"]}, {"_id": 0, "password_hash": 0})
            return {"message": "Signup successful", "user_id": existing["user_id"], "profile": profile}
        # Otherwise block duplicate signup
        raise HTTPException(status_code=400, detail="Email already registered")
    user_id = str(ObjectId())
    doc = {
        "user_id": user_id,
        "name": payload.name,
        "email": normalized_email,
        "password_hash": password_hash,
        "self_assessment": payload.self_assessment.dict() if payload.self_assessment else None,
        "created_at": datetime.utcnow(),
    }
    await users.insert_one(doc)
    profile = await users.find_one({"user_id": user_id}, {"_id": 0, "password_hash": 0})
    return {"message": "Signup successful", "user_id": user_id, "profile": profile}

@app.post("/api/auth/login")
async def login(payload: LoginRequest, db=Depends(get_database)):
    users = db.users
    normalized_email = (payload.email or "").strip().lower()
    user = await users.find_one({"email": normalized_email})
    if not user or not user.get("password_hash"):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    try:
        ok = bcrypt.checkpw(payload.password.encode("utf-8"), user["password_hash"].encode("utf-8"))
    except Exception:
        ok = False
    if not ok:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    profile = await users.find_one({"user_id": user["user_id"]}, {"_id": 0, "password_hash": 0})
    return {"message": "Login successful", "user_id": user["user_id"], "profile": profile}

@app.get("/api/users/{user_id}")
async def get_user(user_id: str, db=Depends(get_database)):
    """
    Get user profile
    """
    users_collection = db.users
    user = await users_collection.find_one({"user_id": user_id}, {"_id": 0, "password_hash": 0})
    
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
    Create a new relationship profile - allows multiple partners per relationship type
    """
    relationships_collection = db.relationships
    
    # Generate a unique relationship ID
    relationship_id = str(ObjectId())
    relationship_dict = relationship.dict()
    relationship_dict["relationship_id"] = relationship_id
    relationship_dict["created_at"] = datetime.utcnow()
    relationship_dict["updated_at"] = datetime.utcnow()
    
    # Insert as a new relationship (no upsert)
    await relationships_collection.insert_one(relationship_dict)
    
    return {"message": "Relationship profile saved successfully", "relationship_id": relationship_id}

@app.put("/api/relationships/{relationship_id}", status_code=200)
async def update_relationship(
    relationship_id: str,
    relationship: RelationshipProfile,
    db=Depends(get_database)
):
    """
    Update an existing relationship profile
    """
    relationships_collection = db.relationships
    
    relationship_dict = relationship.dict()
    relationship_dict["updated_at"] = datetime.utcnow()
    
    result = await relationships_collection.update_one(
        {
            "relationship_id": relationship_id,
            "user_id": relationship.user_id
        },
        {"$set": relationship_dict}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Relationship not found")
    
    return {"message": "Relationship profile updated successfully"}

@app.delete("/api/relationships/{relationship_id}", status_code=200)
async def delete_relationship(
    relationship_id: str,
    user_id: str,
    db=Depends(get_database)
):
    """
    Delete a relationship profile
    """
    relationships_collection = db.relationships
    
    result = await relationships_collection.delete_one({
        "relationship_id": relationship_id,
        "user_id": user_id
    })
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Relationship not found")
    
    return {"message": "Relationship profile deleted successfully"}

@app.get("/api/sessions/{user_id}")
async def get_user_sessions(user_id: str, db=Depends(get_database)):
    """
    Get all chat sessions for a user
    """
    sessions_collection = db[SESSIONS_COLLECTION]
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
    sessions_collection = db[SESSIONS_COLLECTION]
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
    sessions_collection = db[SESSIONS_COLLECTION]
    result = await sessions_collection.delete_one({"session_id": session_id})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {"message": "Session deleted successfully"}

@app.post("/api/advice", response_model=AdviceResponse)
async def create_advice(request: AdviceRequest, db=Depends(get_database)):
    api_key = (os.getenv("OPENAI_API_KEY") or OPENAI_API_KEY or "").strip()
    if not api_key:
        raise HTTPException(status_code=503, detail="OpenAI API key not configured. Set the OPENAI_API_KEY environment variable and restart the server.")
    if any(ch.isspace() for ch in api_key):
        raise HTTPException(status_code=401, detail="Advice error: OPENAI_API_KEY contains whitespace/newlines. Fix your .env so the key is a single line with no trailing spaces.")
    client = AsyncOpenAI(api_key=api_key, timeout=httpx.Timeout(20.0, read=60.0))
    advice_collection = db.advice

    system = build_system_prompt(
        relationship_type=("general" if request.partner_profile is None else "partner"),
        partner_profile=request.partner_profile,
        self_assessment=request.self_assessment
    )
    user = (
        f"Topic: {request.topic}\n\n"
        f"Situation: {request.situation}\n\n"
        "Provide a concise, step-by-step, actionable plan the user can apply now. "
        "Structure the response with short sections: Summary, Why it helps, 3-6 Action Steps, Gentle Check-ins, and Conversation Prompts. "
        "Keep it supportive and specific."
    )

    try:
        completion = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.7,
            max_tokens=600,
        )
        content = (completion.choices[0].message.content or "").strip()
    except AuthenticationError as e:
        logging.exception("OpenAI auth error (check OPENAI_API_KEY)")
        raise HTTPException(status_code=401, detail="Advice generation failed: OpenAI authentication failed. Check OPENAI_API_KEY.")
    except (APIConnectionError, httpx.ConnectError, httpx.ConnectTimeout) as e:
        logging.exception("OpenAI connection error in advice")
        raise HTTPException(status_code=503, detail="Advice generation failed: Connection to OpenAI failed.")
    except httpx.ReadTimeout as e:
        logging.exception("OpenAI read timeout in advice")
        raise HTTPException(status_code=504, detail="Advice generation failed: OpenAI read timeout.")
    except RateLimitError as e:
        logging.exception("OpenAI rate limit in advice")
        raise HTTPException(status_code=429, detail="Advice generation failed: OpenAI rate limit exceeded.")
    except APIStatusError as e:
        logging.exception("OpenAI API status error in advice")
        raise HTTPException(status_code=502, detail=f"Advice generation failed: OpenAI API error {getattr(e, 'status_code', '')}.")
    except Exception as e:
        logging.exception("Unhandled advice error")
        raise HTTPException(status_code=500, detail=f"Advice generation failed: {str(e)}")

    advice_id = str(ObjectId())
    record = {
        "advice_id": advice_id,
        "user_id": request.user_id,
        "topic": request.topic,
        "situation": request.situation,
        "content": content,
        "partner_profile": request.partner_profile.dict() if request.partner_profile else None,
        "created_at": datetime.utcnow(),
    }
    await advice_collection.insert_one(record)

    return AdviceResponse(
        advice_id=advice_id,
        topic=request.topic,
        content=content,
        created_at=record["created_at"],
    )


@app.get("/api/advice/{user_id}")
async def list_advice(user_id: str, db=Depends(get_database)):
    advice_collection = db.advice
    items = await advice_collection.find(
        {"user_id": user_id},
        {"_id": 0}
    ).sort("created_at", -1).to_list(length=100)
    for it in items:
        text = it.get("content", "") or ""
        it["preview"] = (text[:180] + ("…" if len(text) > 180 else ""))
    return {"advice": items}


@app.get("/api/advice/item/{advice_id}")
async def get_advice(advice_id: str, db=Depends(get_database)):
    advice_collection = db.advice
    item = await advice_collection.find_one({"advice_id": advice_id}, {"_id": 0})
    if not item:
        raise HTTPException(status_code=404, detail="Advice not found")
    return item


@app.delete("/api/advice/{advice_id}")
async def delete_advice(advice_id: str, db=Depends(get_database)):
    advice_collection = db.advice
    res = await advice_collection.delete_one({"advice_id": advice_id})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Advice not found")
    return {"message": "Advice deleted"}

# ======================
# Run with: uvicorn main:app --reload
# ======================
from pydantic import BaseModel, EmailStr, Field
from typing import List, Dict, Any, Optional
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, Index, func
from .db import Base
import datetime

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True) # Assuming index=True is okay
    role = Column(String(50), nullable=False)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    knowledge_level = Column(String(50), nullable=False)
    program_interest = Column(String(100), nullable=True)
    preferred_locations = Column(Text, nullable=True)
    college_name = Column(String(255), nullable=True)
    major = Column(String(255), nullable=True)
    year_of_study = Column(String(50), nullable=True)
    interests = Column(Text, nullable=True)
    primary_goal = Column(String(100), nullable=True)
    years_experience = Column(String(20), nullable=True)
    certifications = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_login = Column(DateTime(timezone=True), nullable=True)
    reset_token = Column(String(255), nullable=True)
    reset_token_expiry = Column(DateTime(timezone=True), nullable=True)
    is_bot = Column(Boolean, default=False)
    has_seen_intro = Column(Boolean, default=True) # Default based on your schema output

    # Explicitly define indexes shown in your \d output if needed
    __table_args__ = (
        Index('idx_users_email', 'email'), # Already indexed by unique constraint? Redundant ok.
        Index('idx_users_knowledge_level', 'knowledge_level'),
        Index('idx_users_role', 'role'),
    )

class UserLoginRequest(BaseModel): # If using JSON body for login instead of form
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str

class StartSimulationRequest(BaseModel):
    scenario: str
    intensity: str
    duration: int = Field(default=30, gt=0)

class StartSimulationResponse(BaseModel):
    message: str
    simulation_id: str # ID for guest or logged-in user's sim session

class SimulationActionRequest(BaseModel):
    action: str
    # simulation_id is passed in URL path usually, not body

class SubmitBriefingRequest(BaseModel):
    talking_points: str
    # simulation_id passed in URL path

class ActionResponse(BaseModel):
    status: str # e.g., "processing", "invalid_action"

class EventModel(BaseModel): # For WebSocket events later
    type: str
    payload: Dict[str, Any]


class UserRatingRequest(BaseModel):
    simulation_id: str
    rating: int = Field(..., ge=1, le=5) # Assuming 1-5 stars (adjust if your UI uses a different scale)
    feedback: Optional[str] = None
# (Add other request/response models as needed)

class LlmAndUserSimulationRating(Base): # Renamed for clarity, or keep as LlmSimulationRating
    __tablename__ = "simulation_ratings" # Consider a more general table name

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    simulation_id_str = Column(String(255), nullable=False, index=True, unique=True) # Made unique if one entry per sim
    user_id_str = Column(String(255), nullable=True) # User who played the sim
    scenario_key = Column(String(100), nullable=True)

    # LLM Performance Rating fields
    llm_overall_score = Column(Integer, nullable=True)
    llm_timeliness_score = Column(Integer, nullable=True)
    llm_contact_strategy_score = Column(Integer, nullable=True)
    llm_decision_quality_score = Column(Integer, nullable=True)
    llm_efficiency_score = Column(Integer, nullable=True)
    llm_qualitative_feedback = Column(Text, nullable=True)
    llm_rating_at = Column(DateTime(timezone=True), nullable=True) # When LLM rating was generated

    # User's Star Rating & Feedback fields
    user_rating_stars = Column(Integer, nullable=True) # The star rating (1-5)
    user_feedback_text = Column(Text, nullable=True)   # The textual feedback
    user_rated_at = Column(DateTime(timezone=True), nullable=True) # When the user submitted their rating

    created_at = Column(DateTime(timezone=True), server_default=func.now()) # Initial record creation

    def __repr__(self):
        return f"<SimulationRating(id={self.id}, sim_id='{self.simulation_id_str}')>"
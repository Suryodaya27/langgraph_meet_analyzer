"""
Pydantic models for fact-first architecture
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Literal
from datetime import datetime


# ============================================================================
# FACT EXTRACTION MODELS
# ============================================================================

class ExtractedFact(BaseModel):
    """A single fact extracted from the transcript"""
    fact_type: Literal["decision", "action_item", "open_question", "deadline", "metric"]
    content: str
    source_quote: str  # Exact quote from transcript
    confidence: Literal["high", "medium", "low"] = "high"
    context: Optional[str] = None  # Additional context if needed


class ExtractedFacts(BaseModel):
    """All facts extracted from transcript"""
    decisions: List[ExtractedFact] = Field(default_factory=list)
    action_items: List[ExtractedFact] = Field(default_factory=list)
    open_questions: List[ExtractedFact] = Field(default_factory=list)
    deadlines: List[ExtractedFact] = Field(default_factory=list)
    metrics: List[ExtractedFact] = Field(default_factory=list)


# ============================================================================
# VALIDATED FACT MODELS
# ============================================================================

class ValidatedFact(BaseModel):
    """A fact that passed validation"""
    fact_type: str
    content: str
    source_quote: str
    confidence: str
    is_valid: bool = True
    validation_notes: Optional[str] = None


class ValidatedFacts(BaseModel):
    """All validated facts"""
    facts: List[ValidatedFact] = Field(default_factory=list)
    discarded_count: int = 0
    discarded_reasons: List[str] = Field(default_factory=list)


# ============================================================================
# OUTPUT MODELS (reuse from src)
# ============================================================================

class ActionPoint(BaseModel):
    """Strategic action point (derived from validated facts)"""
    description: str
    priority: Literal["High", "Medium", "Low"] = "Medium"
    source_facts: List[str] = Field(default_factory=list)  # Track which facts this came from


class ToDo(BaseModel):
    """Tactical to-do item (derived from validated facts)"""
    task: str
    deadline: Optional[str] = None  # Only include if explicitly stated
    priority: Literal["High", "Medium", "Low"] = "Medium"
    source_facts: List[str] = Field(default_factory=list)


class FollowUpEmail(BaseModel):
    """Follow-up email (derived from validated facts)"""
    subject: str
    body: str
    source_facts: List[str] = Field(default_factory=list)


class MeetingOutputs(BaseModel):
    """Final meeting outputs"""
    summary: str
    action_points: List[ActionPoint] = Field(default_factory=list)
    todos: List[ToDo] = Field(default_factory=list)
    follow_up_emails: List[FollowUpEmail] = Field(default_factory=list)
    
    # Metadata for auditability
    total_facts_extracted: int = 0
    total_facts_validated: int = 0
    facts_discarded: int = 0


# ============================================================================
# LANGGRAPH STATE
# ============================================================================

class MeetingState(BaseModel):
    """State object for LangGraph workflow"""
    
    # Input
    raw_transcript: str
    
    # Step 1: Normalization
    normalized_transcript: Optional[str] = None
    
    # Step 2: Fact Extraction
    extracted_facts: Optional[ExtractedFacts] = None
    
    # Step 3: Fact Validation
    validated_facts: Optional[ValidatedFacts] = None
    
    # Step 4: Output Generation
    outputs: Optional[MeetingOutputs] = None
    
    # Step 5: Compliance Check
    compliance_passed: bool = False
    compliance_issues: List[str] = Field(default_factory=list)
    
    # Metadata
    processing_started: Optional[datetime] = None
    processing_completed: Optional[datetime] = None
    
    class Config:
        arbitrary_types_allowed = True

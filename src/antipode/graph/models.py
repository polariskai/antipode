"""
Data models for graph entities and relationships
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum


class EntityType(str, Enum):
    """Types of entities in the graph"""
    COMPANY = "Company"
    PERSON = "Person"
    ADDRESS = "Address"
    FILING = "Filing"
    EVENT = "Event"


class RelationshipType(str, Enum):
    """Types of relationships in the graph"""
    OWNS = "OWNS"
    CONTROLS = "CONTROLS"
    DIRECTOR_OF = "DIRECTOR_OF"
    OFFICER_OF = "OFFICER_OF"  # New: For officers (CEO, CFO, etc.)
    REGISTERED_AT = "REGISTERED_AT"
    OPERATES_IN = "OPERATES_IN"  # New: For foreign operations
    ASSOCIATED_WITH = "ASSOCIATED_WITH"
    SUBJECT_OF = "SUBJECT_OF"
    SHARES_ADDRESS_WITH = "SHARES_ADDRESS_WITH"
    RELATED_TO = "RELATED_TO"
    FAMILY_OF = "FAMILY_OF"  # New: For family relationships (PEP RCA)
    ASSOCIATE_OF = "ASSOCIATE_OF"  # New: For close associates (PEP RCA)


class Entity(BaseModel):
    """Base entity model"""
    id: str = Field(..., description="Unique identifier")
    entity_type: EntityType
    name: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        use_enum_values = True


class Company(Entity):
    """Company entity"""
    entity_type: EntityType = EntityType.COMPANY
    registration_number: Optional[str] = None
    jurisdiction: Optional[str] = None  # e.g., "US", "IN"
    incorporation_date: Optional[datetime] = None
    status: Optional[str] = None  # e.g., "Active", "Dissolved"
    industry: Optional[str] = None


class Person(Entity):
    """Person entity"""
    entity_type: EntityType = EntityType.PERSON
    date_of_birth: Optional[datetime] = None
    nationality: Optional[str] = None
    identifiers: Dict[str, str] = Field(default_factory=dict)  # e.g., {"SSN": "xxx-xx-xxxx"}


class Address(Entity):
    """Address entity"""
    entity_type: EntityType = EntityType.ADDRESS
    street: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    postal_code: Optional[str] = None
    full_address: Optional[str] = None


class Filing(Entity):
    """Regulatory filing entity"""
    entity_type: EntityType = EntityType.FILING
    filing_type: Optional[str] = None  # e.g., "10-K", "8-K"
    filing_date: Optional[datetime] = None
    source: Optional[str] = None  # e.g., "SEC EDGAR", "MCA"
    url: Optional[str] = None


class Event(Entity):
    """Adverse event entity"""
    entity_type: EntityType = EntityType.EVENT
    event_type: Optional[str] = None  # e.g., "Enforcement", "Media", "Regulatory"
    event_date: Optional[datetime] = None
    severity: Optional[str] = None  # e.g., "High", "Medium", "Low"
    source: Optional[str] = None
    description: Optional[str] = None


class Relationship(BaseModel):
    """Relationship between entities"""
    from_id: str
    to_id: str
    relationship_type: RelationshipType
    properties: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        use_enum_values = True


class OwnershipRelationship(Relationship):
    """Ownership relationship with percentage"""
    relationship_type: RelationshipType = RelationshipType.OWNS
    properties: Dict[str, Any] = Field(default_factory=lambda: {"percent": None, "direct": True})


class EntityContext(BaseModel):
    """Full context of an entity including relationships"""
    entity: Entity
    relationships: List[Relationship] = Field(default_factory=list)
    related_entities: List[Entity] = Field(default_factory=list)
    risk_signals: List[Dict[str, Any]] = Field(default_factory=list)
    intelligence_summary: Optional[str] = None




from datetime import datetime, timezone, date
from sqlalchemy.dialects import postgresql as pg_dialect
from sqlalchemy.dialects import sqlite as sqlite_dialect

from sqlalchemy import Column, Integer, String, DateTime, Date, Enum, JSON, ForeignKey, Table, Boolean, Numeric, Time, Float, TypeDecorator, CHAR, Text, text
from sqlalchemy.orm import relationship
from app.core.config import settings
from sqlalchemy.dialects.postgresql import BIGINT, UUID, JSONB, ARRAY as PG_ARRAY
from sqlalchemy import func
import pydantic
from pydantic import BaseModel
from typing import Optional, List
from enum import Enum as PydanticEnum
from app.db.session import Base
import uuid


class GUID(TypeDecorator):
    """Platform-independent GUID type.
    Uses PostgreSQL's UUID type, otherwise uses CHAR(36) for SQLite.
    """
    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(UUID())
        else:
            return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        elif dialect.name == 'postgresql':
            return str(value)
        else:
            if not isinstance(value, uuid.UUID):
                return str(uuid.UUID(value))
            return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        else:
            if not isinstance(value, uuid.UUID):
                return uuid.UUID(value)
            return value


class JSONB(TypeDecorator):
    """Platform-independent JSONB type.
    Uses PostgreSQL's JSONB type, otherwise falls back to JSON for SQLite.
    """
    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            # Use pg_dialect.JSONB which is the actual PostgreSQL JSONB type
            from sqlalchemy.dialects import postgresql as pg_dialect
            return dialect.type_descriptor(pg_dialect.JSONB())
        else:
            return dialect.type_descriptor(JSON())

    def process_bind_param(self, value, dialect):
        return value

    def process_result_value(self, value, dialect):
        return value


class ARRAY(TypeDecorator):
    """Platform-independent ARRAY type.
    Uses PostgreSQL's ARRAY type, otherwise falls back to JSON for SQLite.

    Element types should be SQLAlchemy column types like Text, UUID(), etc.
    """
    impl = JSON
    cache_ok = True

    def __init__(self, element_type, **kwargs):
        super().__init__(**kwargs)
        self._element_type = element_type

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(PG_ARRAY(self._element_type))
        else:
            return dialect.type_descriptor(JSON())

    def process_bind_param(self, value, dialect):
        if dialect.name == 'postgresql':
            return value
        else:
            # Convert list to JSON for SQLite
            if value is None:
                return None
            return value

    def process_result_value(self, value, dialect):
        if dialect.name == 'postgresql':
            return value
        else:
            # Return as-is for SQLite (stored as JSON)
            return value if value is None else list(value) if not isinstance(value, list) else value

class TripStatus(str, PydanticEnum):
    draft = "draft"
    generating = "generating"
    planned = "planned"
    active = "active"
    completed = "completed"
    archived = "archived"

class PaceType(str, PydanticEnum):
    relaxed = "relaxed"
    balanced = "balanced"
    packed = "packed"

class ItemType(str, PydanticEnum):
    sightseeing = "sightseeing"
    food = "food"
    culture = "culture"
    nature = "nature"
    nightlife = "nightlife"
    shopping = "shopping"
    adventure = "adventure"
    transport = "transport"
    stay = "stay"
    other = "other"

class SettingType(str, PydanticEnum):
    indoor = "indoor"
    outdoor = "outdoor"
    mixed = "mixed"

class TransportMode(str, PydanticEnum):
    walk = "walk"
    taxi = "taxi"
    bus = "bus"
    train = "train"
    metro = "metro"
    bike = "bike"
    car = "car"

class DisruptionType(str, PydanticEnum):
    weather = "weather"
    closure = "closure"
    hours_conflict = "hours_conflict"
    delay = "delay"
    budget_overrun = "budget_overrun"
    user_request = "user_request"

class SeverityType(str, PydanticEnum):
    low = "low"
    medium = "medium"
    high = "high"

class ProposalStatus(str, PydanticEnum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    expired = "expired"
    superseded = "superseded"

class RunType(str, PydanticEnum):
    plan = "plan"
    replan = "replan"
    chat = "chat"

class RunStatus(str, PydanticEnum):
    queued = "queued"
    running = "running"
    awaiting_user = "awaiting_user"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"

class ExpenseCategory(str, PydanticEnum):
    stay = "stay"
    food = "food"
    transport = "transport"
    activities = "activities"
    shopping = "shopping"
    other = "other"

class User(Base):
    __tablename__ = 'users'
    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    email = Column(String, nullable=False, unique=True)
    password_hash = Column(String, nullable=True)
    display_name = Column(String, nullable=False)
    google_sub = Column(String, nullable=True, unique=True)
    home_currency = Column(String, nullable=False, server_default='INR')
    units = Column(String, nullable=False, server_default='metric')
    is_active = Column(Boolean, nullable=False, server_default=text('true'))
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    trips = relationship('Trip', foreign_keys='Trip.user_id', back_populates='user', cascade="all, delete", passive_deletes=True)
    agent_runs = relationship('AgentRun', foreign_keys='AgentRun.user_id', back_populates='user', cascade="all, delete", passive_deletes=True)
    expenses = relationship('Expense', foreign_keys='Expense.user_id', back_populates='user', cascade="all, delete", passive_deletes=True)
    refresh_tokens = relationship('RefreshToken', foreign_keys='RefreshToken.user_id', back_populates='user', cascade="all, delete", passive_deletes=True)


class RefreshToken(Base):
    __tablename__ = 'refresh_tokens'
    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    user_id = Column(GUID(), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    token_hash = Column(String, nullable=False, unique=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    user = relationship('User', back_populates='refresh_tokens')


class Trip(Base):
    __tablename__ = 'trips'
    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    user_id = Column(GUID(), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    title = Column(String, nullable=False)
    destination = Column(String, nullable=False)
    dest_lat = Column(Float, nullable=True)
    dest_lng = Column(Float, nullable=True)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    group_size = Column(Integer, nullable=False, server_default='1')
    budget_total = Column(Numeric(12, 2), nullable=False, server_default='0')
    budget_per_day_cap = Column(Numeric(12, 2), nullable=True)
    currency = Column(String, nullable=False, server_default='INR')
    pace = Column(Enum(PaceType, name='pace_type'), nullable=False, server_default='balanced')
    vibe_tags = Column(ARRAY(Text), nullable=False, default=lambda: [])
    notes = Column(String, nullable=True)
    status = Column(Enum(TripStatus, name='trip_status'), nullable=False, server_default='draft')
    current_version_id = Column(GUID(), nullable=True)
    last_checked_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    user = relationship('User', foreign_keys='Trip.user_id', back_populates='trips')
    itinerary_versions = relationship('ItineraryVersion', foreign_keys='ItineraryVersion.trip_id', back_populates='trip', cascade="all, delete", passive_deletes=True)
    agent_runs = relationship('AgentRun', foreign_keys='AgentRun.trip_id', back_populates='trip', cascade="all, delete", passive_deletes=True)
    replan_proposals = relationship('ReplanProposal', foreign_keys='ReplanProposal.trip_id', back_populates='trip', cascade="all, delete", passive_deletes=True)
    disruption_events = relationship('DisruptionEvent', foreign_keys='DisruptionEvent.trip_id', back_populates='trip', cascade="all, delete", passive_deletes=True)
    expenses = relationship('Expense', foreign_keys='Expense.trip_id', back_populates='trip', cascade="all, delete", passive_deletes=True)

    # Back-populate for expenses (plural)
    __table_args__ = (
        # Constraints
    )


class ItineraryVersion(Base):
    __tablename__ = 'itinerary_versions'
    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    trip_id = Column(GUID(), ForeignKey('trips.id', ondelete='CASCADE'), nullable=False)
    version_no = Column(Integer, nullable=False)
    parent_version_id = Column(GUID(), ForeignKey('itinerary_versions.id'), nullable=True)
    reason = Column(String, nullable=False)
    created_by = Column(String, nullable=False)
    proposal_id = Column(GUID(), ForeignKey('replan_proposals.id', use_alter=True, name='fk_itinerary_versions_proposal_id'), nullable=True)
    run_id = Column(GUID(), ForeignKey('agent_runs.id'), nullable=True)
    total_cost = Column(Numeric(12, 2), nullable=False, server_default='0')
    summary = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    trip = relationship('Trip', foreign_keys='ItineraryVersion.trip_id', back_populates='itinerary_versions')
    items = relationship('ItineraryItem', foreign_keys='ItineraryItem.version_id', back_populates='version', cascade="all, delete", passive_deletes=True)
    replan_proposals = relationship('ReplanProposal', foreign_keys='ReplanProposal.base_version_id', back_populates='base_version')


class ItineraryItem(Base):
    __tablename__ = 'itinerary_items'
    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    version_id = Column(GUID(), ForeignKey('itinerary_versions.id', ondelete='CASCADE'), nullable=False)
    stable_key = Column(GUID(), nullable=False, default=uuid.uuid4)
    day_index = Column(Integer, nullable=False)
    position = Column(Integer, nullable=False)
    place_id = Column(GUID(), ForeignKey('places.id'), nullable=True)
    title = Column(String, nullable=False)
    category = Column(Enum(ItemType, name='item_category'), nullable=False)
    setting = Column(Enum(SettingType, name='setting_type'), nullable=False, server_default='mixed')
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    est_cost = Column(Numeric(12, 2), nullable=False, server_default='0')
    lat = Column(Float, nullable=True)
    lng = Column(Float, nullable=True)
    is_locked = Column(Boolean, nullable=False, server_default=text('false'))
    travel_mode = Column(Enum(TransportMode, name='transport_mode'), nullable=True)
    travel_minutes = Column(Integer, nullable=True)
    travel_distance_m = Column(Integer, nullable=True)
    flags = Column(ARRAY(Text), nullable=False, default=lambda: [])
    notes = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    version = relationship('ItineraryVersion', foreign_keys='ItineraryItem.version_id', back_populates='items')
    place = relationship('Place', foreign_keys='ItineraryItem.place_id', back_populates='items')
    expenses = relationship('Expense', foreign_keys='Expense.item_stable_key', back_populates='item')


class Place(Base):
    __tablename__ = 'places'
    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    external_id = Column(String, nullable=True)
    source = Column(String, nullable=False, server_default='seed')
    name = Column(String, nullable=False)
    city = Column(String, nullable=False)
    country = Column(String, nullable=False, server_default='IN')
    lat = Column(Float, nullable=False)
    lng = Column(Float, nullable=False)
    category = Column(Enum(ItemType, name='item_category'), nullable=False)
    setting = Column(Enum(SettingType, name='setting_type'), nullable=False, server_default='mixed')
    avg_cost = Column(Numeric(12, 2), nullable=True)
    currency = Column(String, nullable=False, server_default='INR')
    avg_duration_min = Column(Integer, nullable=True)
    opening_hours = Column(JSONB, nullable=True)
    hours_confidence = Column(String, nullable=False, server_default='unknown')
    rating = Column(Float, nullable=True)
    tags = Column(ARRAY(Text), nullable=False, default=lambda: [])
    description = Column(String, nullable=True)
    image_url = Column(String, nullable=True)
    raw = Column(JSONB, nullable=True)
    fetched_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    items = relationship('ItineraryItem', foreign_keys='ItineraryItem.place_id', back_populates='place')

    __table_args__ = (
        # Constraints
    )


class AgentRun(Base):
    __tablename__ = 'agent_runs'
    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    trip_id = Column(GUID(), ForeignKey('trips.id', ondelete='CASCADE'), nullable=False)
    user_id = Column(GUID(), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    type = Column(Enum(RunType, name='run_type'), nullable=False)
    status = Column(Enum(RunStatus, name='run_status'), nullable=False, server_default='queued')
    trigger = Column(String, nullable=False, server_default='user')
    idempotency_key = Column(String, nullable=True)
    input = Column(JSONB, nullable=False, default=lambda: {})
    output = Column(JSONB, nullable=True)
    error = Column(String, nullable=True)
    model_used = Column(String, nullable=True)
    tokens_in = Column(Integer, nullable=False, server_default='0')
    tokens_out = Column(Integer, nullable=False, server_default='0')
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    trip = relationship('Trip', foreign_keys='AgentRun.trip_id', back_populates='agent_runs')
    user = relationship('User', foreign_keys='AgentRun.user_id', back_populates='agent_runs')
    events = relationship('AgentRunEvent', foreign_keys='AgentRunEvent.run_id', back_populates='run', cascade="all, delete", passive_deletes=True)
    replan_proposals = relationship('ReplanProposal', foreign_keys='ReplanProposal.run_id', back_populates='run')
    disruption_events = relationship('DisruptionEvent', foreign_keys='DisruptionEvent.run_id', back_populates='run')


class AgentRunEvent(Base):
    __tablename__ = 'agent_run_events'
    id = Column(BIGINT().with_variant(Integer, 'sqlite'), primary_key=True, autoincrement=True)
    run_id = Column(GUID(), ForeignKey('agent_runs.id', ondelete='CASCADE'), nullable=False)
    seq = Column(Integer, nullable=False)
    type = Column(String, nullable=False)
    node = Column(String, nullable=True)
    message = Column(String, nullable=True)
    status = Column(String, nullable=True)
    payload = Column(JSONB, nullable=False, default=lambda: {})
    latency_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    run = relationship('AgentRun', foreign_keys='AgentRunEvent.run_id', back_populates='events')


class DisruptionEvent(Base):
    __tablename__ = 'disruption_events'
    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    trip_id = Column(GUID(), ForeignKey('trips.id', ondelete='CASCADE'), nullable=False)
    run_id = Column(GUID(), ForeignKey('agent_runs.id', ondelete='SET NULL'), nullable=True)
    type = Column(Enum(DisruptionType, name='disruption_type'), nullable=False)
    severity = Column(Enum(SeverityType, name='severity_type'), nullable=False, server_default='medium')
    day_index = Column(Integer, nullable=True)
    window_start = Column(DateTime(timezone=True), nullable=True)
    window_end = Column(DateTime(timezone=True), nullable=True)
    affected_stable_keys = Column(ARRAY(UUID()), nullable=False, default=lambda: [])
    summary = Column(String, nullable=False)
    source = Column(String, nullable=False)
    data = Column(JSONB, nullable=False, default=lambda: {})
    fingerprint = Column(String, nullable=False)
    is_simulated = Column(Boolean, nullable=False, server_default=text('false'))
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    trip = relationship('Trip', foreign_keys='DisruptionEvent.trip_id', back_populates='disruption_events')
    run = relationship('AgentRun', foreign_keys='DisruptionEvent.run_id', back_populates='disruption_events')


class ReplanProposal(Base):
    __tablename__ = 'replan_proposals'
    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    trip_id = Column(GUID(), ForeignKey('trips.id', ondelete='CASCADE'), nullable=False)
    run_id = Column(GUID(), ForeignKey('agent_runs.id', ondelete='CASCADE'), nullable=False)
    base_version_id = Column(GUID(), ForeignKey('itinerary_versions.id'), nullable=False)
    status = Column(Enum(ProposalStatus, name='proposal_status'), nullable=False, server_default='pending')
    reason = Column(String, nullable=False)
    explanation = Column(String, nullable=True)
    disruption_ids = Column(ARRAY(UUID()), nullable=False, default=lambda: [])
    diff = Column(JSONB, nullable=False, default=lambda: {})
    proposed_items = Column(JSONB, nullable=False, default=lambda: {})
    cost_delta = Column(Numeric(12, 2), nullable=False, server_default='0')
    time_delta_min = Column(Integer, nullable=False, server_default='0')
    items_changed = Column(Integer, nullable=False, server_default='0')
    alternatives_of = Column(GUID(), ForeignKey('replan_proposals.id'), nullable=True)
    resulting_version_id = Column(GUID(), ForeignKey('itinerary_versions.id', use_alter=True, name='fk_replan_proposals_resulting_version_id'), nullable=True)
    decided_at = Column(DateTime(timezone=True), nullable=True)
    decision_note = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    trip = relationship('Trip', foreign_keys='ReplanProposal.trip_id', back_populates='replan_proposals')
    run = relationship('AgentRun', foreign_keys='ReplanProposal.run_id', back_populates='replan_proposals')
    base_version = relationship('ItineraryVersion', foreign_keys='ReplanProposal.base_version_id', back_populates='replan_proposals')


class Expense(Base):
    __tablename__ = 'expenses'
    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    trip_id = Column(GUID(), ForeignKey('trips.id', ondelete='CASCADE'), nullable=False)
    user_id = Column(GUID(), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    item_stable_key = Column(GUID(), ForeignKey('itinerary_items.stable_key'), nullable=True)
    category = Column(Enum(ExpenseCategory, name='expense_category'), nullable=False)
    amount = Column(Numeric(12, 2), nullable=False)
    currency = Column(String, nullable=False, server_default='INR')
    amount_in_trip_currency = Column(Numeric(12, 2), nullable=False)
    description = Column(String, nullable=True)
    spent_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    trip = relationship('Trip', foreign_keys='Expense.trip_id', back_populates='expenses')
    user = relationship('User', foreign_keys='Expense.user_id', back_populates='expenses')
    item = relationship('ItineraryItem', foreign_keys='Expense.item_stable_key', back_populates='expenses')


class ChatMessage(Base):
    __tablename__ = 'chat_messages'
    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    trip_id = Column(GUID(), ForeignKey('trips.id', ondelete='CASCADE'), nullable=False)
    run_id = Column(GUID(), ForeignKey('agent_runs.id', ondelete='SET NULL'), nullable=True)
    role = Column(String, nullable=False)
    content = Column(String, nullable=False)
    message_metadata = Column("metadata", JSONB, nullable=False, default=lambda: {})
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    trip = relationship('Trip')


class ApiCache(Base):
    __tablename__ = 'api_cache'
    cache_key = Column(String, primary_key=True)
    provider = Column(String, nullable=False)
    response = Column(JSONB, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
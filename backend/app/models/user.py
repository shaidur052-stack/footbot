"""Database tables.

One file for all models so relationships resolve without import order
problems. Split later if it grows past a few hundred lines.
"""

from datetime import datetime

from sqlalchemy import (Column, Integer, String, Float, Boolean,
                        DateTime, ForeignKey, Text)
from sqlalchemy.orm import relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)     # never the password itself
    created_at = Column(DateTime, default=datetime.utcnow)

    profile = relationship("Profile", back_populates="user", uselist=False,
                           cascade="all, delete-orphan")
    conversations = relationship("Conversation", back_populates="user",
                                 cascade="all, delete-orphan")


class Profile(Base):
    """Raw inputs only. BMI and calorie targets are computed on read by
    profile_service, so changing the formula never leaves stale numbers
    sitting in the database."""

    __tablename__ = "profiles"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)

    age = Column(Integer, nullable=False)
    gender = Column(String, nullable=False)
    weight_kg = Column(Float, nullable=False)
    height_cm = Column(Float, nullable=False)
    activity = Column(String, default="sedentary")
    goal = Column(String, default="maintain")
    condition = Column(String, default="none")

    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="profile")


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String, default="New chat")
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation",
                            cascade="all, delete-orphan",
                            order_by="Message.created_at")


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False)

    role = Column(String, nullable=False)              # "user" | "assistant"
    content = Column(Text, nullable=False)
    sources_json = Column(Text, default="[]")          # citations, as JSON

    created_at = Column(DateTime, default=datetime.utcnow)

    conversation = relationship("Conversation", back_populates="messages")
    feedback = relationship("Feedback", back_populates="message",
                            uselist=False, cascade="all, delete-orphan")


class Feedback(Base):
    """Thumbs up/down. Becomes a real evaluation metric in Week 7."""

    __tablename__ = "feedback"

    id = Column(Integer, primary_key=True)
    message_id = Column(Integer, ForeignKey("messages.id"), unique=True, nullable=False)
    is_positive = Column(Boolean, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    message = relationship("Message", back_populates="feedback")
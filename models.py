#!/usr/bin/env python3
"""
@file models.py
@brief SQLAlchemy models for job application tracking.

@details
This module defines the database schema using SQLAlchemy ORM.
Tables: companies, applications, contacts, stages
"""

from __future__ import annotations

from typing import Optional
from sqlalchemy import Column, Integer, String, ForeignKey, create_engine
from sqlalchemy.orm import declarative_base, relationship, Session
from sqlalchemy.pool import StaticPool

Base = declarative_base()

class Company(Base):
    """Company model"""
    __tablename__ = "companies"
    
    company_id = Column(String, primary_key=True)
    name = Column(String, nullable=False, unique=True)
    location = Column(String, default="")
    industry = Column(String, default="")
    website = Column(String, default="")
    source = Column(String, default="")
    rating = Column(String, default="")
    created_at = Column(Integer, nullable=False)
    
    # Relationships
    applications = relationship("Application", back_populates="company", cascade="all, delete-orphan")
    contacts = relationship("Contact", back_populates="company", cascade="all, delete-orphan")
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            "company_id": self.company_id,
            "name": self.name,
            "location": self.location,
            "industry": self.industry,
            "website": self.website,
            "source": self.source,
            "rating": self.rating,
            "created_at": self.created_at,
        }

class Application(Base):
    """Application model"""
    __tablename__ = "applications"
    
    application_id = Column(String, primary_key=True)
    company_id = Column(String, ForeignKey("companies.company_id"), nullable=False)
    position = Column(String, nullable=False)
    status = Column(String, default="new")
    employment_type = Column(String, default="")
    salary_min = Column(Integer, nullable=True)
    salary_max = Column(Integer, nullable=True)
    currency = Column(String, default="USD")
    job_url = Column(String, default="")
    applied_at = Column(Integer, nullable=False)
    last_update = Column(Integer, nullable=False)
    notes = Column(String, default="")
    
    # Relationships
    company = relationship("Company", back_populates="applications")
    stages = relationship("Stage", back_populates="application", cascade="all, delete-orphan")
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            "application_id": self.application_id,
            "company_id": self.company_id,
            "position": self.position,
            "status": self.status,
            "employment_type": self.employment_type,
            "salary_min": self.salary_min,
            "salary_max": self.salary_max,
            "currency": self.currency,
            "job_url": self.job_url,
            "applied_at": self.applied_at,
            "last_update": self.last_update,
            "notes": self.notes,
        }

class Contact(Base):
    """Contact model"""
    __tablename__ = "contacts"
    
    contact_id = Column(String, primary_key=True)
    company_id = Column(String, ForeignKey("companies.company_id"), nullable=False)
    name = Column(String, nullable=False)
    title = Column(String, default="")
    email = Column(String, default="")
    phone = Column(String, default="")
    notes = Column(String, default="")
    last_contacted = Column(String, default="")
    
    # Relationships
    company = relationship("Company", back_populates="contacts")
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            "contact_id": self.contact_id,
            "company_id": self.company_id,
            "name": self.name,
            "title": self.title,
            "email": self.email,
            "phone": self.phone,
            "notes": self.notes,
            "last_contacted": self.last_contacted,
        }

class Stage(Base):
    """Stage model"""
    __tablename__ = "stages"
    
    stage_id = Column(String, primary_key=True)
    application_id = Column(String, ForeignKey("applications.application_id"), nullable=False)
    stage = Column(String, nullable=False)
    date = Column(String, default="")
    outcome = Column(String, default="")
    notes = Column(String, default="")
    
    # Relationships
    application = relationship("Application", back_populates="stages")
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            "stage_id": self.stage_id,
            "application_id": self.application_id,
            "stage": self.stage,
            "date": self.date,
            "outcome": self.outcome,
            "notes": self.notes,
        }

# Database setup function
def get_engine(database_url: str = "sqlite:///./job_tracker.db"):
    """Create and return database engine"""
    # Use StaticPool for SQLite to avoid issues with multiple threads
    if database_url.startswith("sqlite"):
        return create_engine(
            database_url,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool
        )
    return create_engine(database_url)

def init_db(database_url: str = "sqlite:///./job_tracker.db"):
    """Initialize database schema"""
    engine = get_engine(database_url)
    Base.metadata.create_all(bind=engine)
    return engine

#!/usr/bin/env python3
"""
@file api.py
@brief FastAPI backend for job application tracker with full CRUD endpoints.

@details
This module provides a REST API for managing job applications, companies, contacts, and stages.
- GET/POST/PUT/DELETE /applications for CRUD operations
- GET/POST/PUT/DELETE /companies for CRUD operations
- GET/POST /contacts for contact management
- GET/POST /stages for stage management
- SQLite database using SQLAlchemy ORM
"""

from __future__ import annotations

from typing import List, Optional
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from models import (
    Base, Company, Application, Contact, Stage,
    get_engine, init_db
)
from tracker_core import (
    _new_id, _now_s, TABLES,
    CompanyService, ApplicationService, ContactService, StageService
)

# =============================================================================
# FastAPI App Initialization
# =============================================================================
app = FastAPI(
    title="Job Application Tracker API",
    description="REST API for tracking job applications with full CRUD support",
    version="1.0.0"
)

# CORS middleware to allow React frontend to communicate
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],  # React dev servers
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database initialization
DATABASE_URL = "sqlite:///./job_tracker.db"
engine = init_db(DATABASE_URL)

# =============================================================================
# Database Dependency
# =============================================================================
def get_db():
    """Dependency to get database session"""
    from sqlalchemy.orm import sessionmaker
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# =============================================================================
# Pydantic Models (Request/Response Schemas)
# =============================================================================
class CompanyCreate(BaseModel):
    name: str
    location: str = ""
    industry: str = ""
    website: str = ""
    source: str = ""
    rating: str = ""

class CompanyResponse(BaseModel):
    company_id: str
    name: str
    location: str
    industry: str
    website: str
    source: str
    rating: str
    created_at: int

    class Config:
        from_attributes = True

class ApplicationCreate(BaseModel):
    company_id: str
    position: str
    status: str = "new"
    employment_type: str = ""
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    currency: str = "USD"
    job_url: str = ""
    notes: str = ""

class ApplicationUpdate(BaseModel):
    position: Optional[str] = None
    status: Optional[str] = None
    employment_type: Optional[str] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    currency: Optional[str] = None
    job_url: Optional[str] = None
    notes: Optional[str] = None

class ApplicationResponse(BaseModel):
    application_id: str
    company_id: str
    position: str
    status: str
    employment_type: str
    salary_min: Optional[int]
    salary_max: Optional[int]
    currency: str
    job_url: str
    applied_at: int
    last_update: int
    notes: str

    class Config:
        from_attributes = True

class ContactCreate(BaseModel):
    company_id: str
    name: str
    title: str = ""
    email: str = ""
    phone: str = ""
    notes: str = ""

class ContactResponse(BaseModel):
    contact_id: str
    company_id: str
    name: str
    title: str
    email: str
    phone: str
    notes: str
    last_contacted: str

    class Config:
        from_attributes = True

class StageCreate(BaseModel):
    application_id: str
    stage: str
    date: str = ""
    outcome: str = ""
    notes: str = ""

class StageResponse(BaseModel):
    stage_id: str
    application_id: str
    stage: str
    date: str
    outcome: str
    notes: str

    class Config:
        from_attributes = True

class AnalyticsSummary(BaseModel):
    total_applications: int
    total_companies: int
    status_breakdown: dict
    recent_activity: int

# =============================================================================
# Health Check Endpoint
# =============================================================================
@app.get("/")
def root():
    """Health check endpoint"""
    return {"message": "Job Application Tracker API is running", "version": "1.0.0"}

@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

# =============================================================================
# Company Endpoints
# =============================================================================
@app.get("/companies", response_model=List[CompanyResponse])
def get_companies(db: Session = Depends(get_db)):
    """Get all companies"""
    companies = db.query(Company).all()
    return companies

@app.get("/companies/{company_id}", response_model=CompanyResponse)
def get_company(company_id: str, db: Session = Depends(get_db)):
    """Get a specific company by ID"""
    company = db.query(Company).filter(Company.company_id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    return company

@app.post("/companies", response_model=CompanyResponse, status_code=201)
def create_company(company_data: CompanyCreate, db: Session = Depends(get_db)):
    """Create a new company"""
    # Check if company already exists
    existing = db.query(Company).filter(Company.name == company_data.name).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Company '{company_data.name}' already exists")
    
    # Create new company
    company_id = _new_id(TABLES["companies"]["id_prefix"])
    company = Company(
        company_id=company_id,
        name=company_data.name,
        location=company_data.location,
        industry=company_data.industry,
        website=company_data.website,
        source=company_data.source,
        rating=company_data.rating,
        created_at=_now_s()
    )
    db.add(company)
    db.commit()
    db.refresh(company)
    return company

@app.delete("/companies/{company_id}")
def delete_company(company_id: str, cascade: bool = True, db: Session = Depends(get_db)):
    """Delete a company (with optional cascade to delete related records)"""
    company = db.query(Company).filter(Company.company_id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    # SQLAlchemy handles cascade delete automatically if configured in models
    db.delete(company)
    db.commit()
    return {"message": f"Company {company_id} deleted successfully"}

# =============================================================================
# Application Endpoints
# =============================================================================
@app.get("/applications", response_model=List[ApplicationResponse])
def get_applications(db: Session = Depends(get_db)):
    """Get all applications"""
    applications = db.query(Application).all()
    return applications

@app.get("/applications/{application_id}", response_model=ApplicationResponse)
def get_application(application_id: str, db: Session = Depends(get_db)):
    """Get a specific application by ID"""
    application = db.query(Application).filter(Application.application_id == application_id).first()
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
    return application

@app.post("/applications", response_model=ApplicationResponse, status_code=201)
def create_application(app_data: ApplicationCreate, db: Session = Depends(get_db)):
    """Create a new application"""
    # Verify company exists
    company = db.query(Company).filter(Company.company_id == app_data.company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail=f"Company {app_data.company_id} not found")
    
    # Create new application
    app_id = _new_id(TABLES["applications"]["id_prefix"])
    now = _now_s()
    application = Application(
        application_id=app_id,
        company_id=app_data.company_id,
        position=app_data.position,
        status=app_data.status,
        employment_type=app_data.employment_type,
        salary_min=app_data.salary_min,
        salary_max=app_data.salary_max,
        currency=app_data.currency,
        job_url=app_data.job_url,
        applied_at=now,
        last_update=now,
        notes=app_data.notes
    )
    db.add(application)
    db.commit()
    db.refresh(application)
    return application

@app.put("/applications/{application_id}", response_model=ApplicationResponse)
def update_application(application_id: str, app_data: ApplicationUpdate, db: Session = Depends(get_db)):
    """Update an existing application"""
    application = db.query(Application).filter(Application.application_id == application_id).first()
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
    
    # Update fields if provided
    update_data = app_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(application, field, value)
    
    application.last_update = _now_s()
    db.commit()
    db.refresh(application)
    return application

@app.delete("/applications/{application_id}")
def delete_application(application_id: str, db: Session = Depends(get_db)):
    """Delete an application"""
    application = db.query(Application).filter(Application.application_id == application_id).first()
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
    
    db.delete(application)
    db.commit()
    return {"message": f"Application {application_id} deleted successfully"}

# =============================================================================
# Contact Endpoints
# =============================================================================
@app.get("/contacts", response_model=List[ContactResponse])
def get_contacts(db: Session = Depends(get_db)):
    """Get all contacts"""
    contacts = db.query(Contact).all()
    return contacts

@app.post("/contacts", response_model=ContactResponse, status_code=201)
def create_contact(contact_data: ContactCreate, db: Session = Depends(get_db)):
    """Create a new contact"""
    # Verify company exists
    company = db.query(Company).filter(Company.company_id == contact_data.company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail=f"Company {contact_data.company_id} not found")
    
    # Create new contact
    contact_id = _new_id(TABLES["contacts"]["id_prefix"])
    contact = Contact(
        contact_id=contact_id,
        company_id=contact_data.company_id,
        name=contact_data.name,
        title=contact_data.title,
        email=contact_data.email,
        phone=contact_data.phone,
        notes=contact_data.notes,
        last_contacted=""
    )
    db.add(contact)
    db.commit()
    db.refresh(contact)
    return contact

# =============================================================================
# Stage Endpoints
# =============================================================================
@app.get("/stages", response_model=List[StageResponse])
def get_stages(db: Session = Depends(get_db)):
    """Get all stages"""
    stages = db.query(Stage).all()
    return stages

@app.post("/stages", response_model=StageResponse, status_code=201)
def create_stage(stage_data: StageCreate, db: Session = Depends(get_db)):
    """Create a new stage"""
    # Verify application exists
    application = db.query(Application).filter(Application.application_id == stage_data.application_id).first()
    if not application:
        raise HTTPException(status_code=404, detail=f"Application {stage_data.application_id} not found")
    
    # Create new stage
    stage_id = _new_id(TABLES["stages"]["id_prefix"])
    stage = Stage(
        stage_id=stage_id,
        application_id=stage_data.application_id,
        stage=stage_data.stage,
        date=stage_data.date,
        outcome=stage_data.outcome,
        notes=stage_data.notes
    )
    db.add(stage)
    
    # Update application last_update
    application.last_update = _now_s()
    
    db.commit()
    db.refresh(stage)
    return stage

# =============================================================================
# Analytics Endpoint
# =============================================================================
@app.get("/analytics", response_model=AnalyticsSummary)
def get_analytics(db: Session = Depends(get_db)):
    """Get analytics summary"""
    from sqlalchemy import func
    from datetime import datetime, timedelta
    
    total_applications = db.query(Application).count()
    total_companies = db.query(Company).count()
    
    # Status breakdown
    status_counts = db.query(
        Application.status,
        func.count(Application.application_id)
    ).group_by(Application.status).all()
    
    status_breakdown = {status: count for status, count in status_counts}
    
    # Recent activity (last 7 days)
    week_ago = _now_s() - (7 * 24 * 60 * 60)
    recent_activity = db.query(Application).filter(
        Application.last_update >= week_ago
    ).count()
    
    return AnalyticsSummary(
        total_applications=total_applications,
        total_companies=total_companies,
        status_breakdown=status_breakdown,
        recent_activity=recent_activity
    )

# =============================================================================
# Main entry point for running with uvicorn
# =============================================================================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

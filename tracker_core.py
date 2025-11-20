#!/usr/bin/env python3
"""
@file tracker_core.py
@brief Core business logic for job application tracking, extracted from CLI for reuse in API.

@details
This module provides reusable functions for CRUD operations on job applications,
companies, contacts, and stages. It can be used by both the CLI and the API layers.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional, Sequence, Tuple

# =============================================================================
# Schema Definitions
# =============================================================================
TABLES: Dict[str, Dict[str, Any]] = {
    "companies": {
        "columns": [
            "company_id", "name", "location", "industry", "website", "source", "rating", "created_at"
        ],
        "id_field": "company_id",
        "id_prefix": "cmp_",
    },
    "applications": {
        "columns": [
            "application_id", "company_id", "position", "status", "employment_type",
            "salary_min", "salary_max", "currency", "job_url", "applied_at", "last_update", "notes"
        ],
        "id_field": "application_id",
        "id_prefix": "app_",
    },
    "contacts": {
        "columns": [
            "contact_id", "company_id", "name", "title", "email", "phone", "notes", "last_contacted"
        ],
        "id_field": "contact_id",
        "id_prefix": "ctc_",
    },
    "stages": {
        "columns": [
            "stage_id", "application_id", "stage", "date", "outcome", "notes"
        ],
        "id_field": "stage_id",
        "id_prefix": "stg_",
    },
}

COMMON_STATUSES: List[str] = [
    "new", "applied", "recruiter", "phone", "technical", "onsite", "offer", "accepted", "rejected", "withdrawn",
]

# =============================================================================
# Utility Functions
# =============================================================================
def _now_s() -> int:
    """@brief Current unix time (seconds)."""
    return int(time.time())

def _new_id(prefix: str) -> str:
    """@brief Generate unique-ish ID via time_ns."""
    return f"{prefix}{time.time_ns()}"

def lookup_company_id_by_name(name: str, companies: Sequence[Dict[str, Any]]) -> Optional[str]:
    """@brief Find company_id by case-insensitive company name."""
    target = name.strip().lower()
    for c in companies:
        if c.get("name", "").strip().lower() == target:
            return c.get("company_id")
    return None

# =============================================================================
# CRUD Operations for Companies
# =============================================================================
class CompanyService:
    """Business logic for company operations"""
    
    @staticmethod
    def create_company(
        companies: List[Dict[str, Any]],
        name: str,
        location: str = "",
        industry: str = "",
        website: str = "",
        source: str = "",
        rating: str = ""
    ) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """
        Create a new company.
        Returns: (new_company_record, updated_companies_list)
        Raises: ValueError if company already exists
        """
        if lookup_company_id_by_name(name, companies) is not None:
            raise ValueError(f'Company "{name}" already exists.')
        
        company_id = _new_id(TABLES["companies"]["id_prefix"])
        row = {
            "company_id": company_id,
            "name": name,
            "location": location,
            "industry": industry,
            "website": website,
            "source": source,
            "rating": rating,
            "created_at": _now_s(),
        }
        companies.append(row)
        return row, companies
    
    @staticmethod
    def get_company_by_id(companies: List[Dict[str, Any]], company_id: str) -> Optional[Dict[str, Any]]:
        """Get a company by ID"""
        for c in companies:
            if c.get("company_id") == company_id:
                return c
        return None
    
    @staticmethod
    def get_all_companies(companies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Get all companies"""
        return companies
    
    @staticmethod
    def delete_company(
        companies: List[Dict[str, Any]],
        company_id: str
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Delete a company.
        Returns: (updated_companies_list, count_deleted)
        """
        kept = []
        removed = 0
        for c in companies:
            if c.get("company_id") == company_id:
                removed += 1
            else:
                kept.append(c)
        return kept, removed

# =============================================================================
# CRUD Operations for Applications
# =============================================================================
class ApplicationService:
    """Business logic for application operations"""
    
    @staticmethod
    def create_application(
        applications: List[Dict[str, Any]],
        company_id: str,
        position: str,
        status: str = "new",
        employment_type: str = "",
        salary_min: Optional[int] = None,
        salary_max: Optional[int] = None,
        currency: str = "USD",
        job_url: str = "",
        notes: str = ""
    ) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """
        Create a new application.
        Returns: (new_application_record, updated_applications_list)
        """
        app_id = _new_id(TABLES["applications"]["id_prefix"])
        now = _now_s()
        row = {
            "application_id": app_id,
            "company_id": company_id,
            "position": position,
            "status": status,
            "employment_type": employment_type,
            "salary_min": salary_min,
            "salary_max": salary_max,
            "currency": currency,
            "job_url": job_url,
            "applied_at": now,
            "last_update": now,
            "notes": notes,
        }
        applications.append(row)
        return row, applications
    
    @staticmethod
    def get_application_by_id(applications: List[Dict[str, Any]], app_id: str) -> Optional[Dict[str, Any]]:
        """Get an application by ID"""
        for a in applications:
            if a.get("application_id") == app_id:
                return a
        return None
    
    @staticmethod
    def get_all_applications(applications: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Get all applications"""
        return applications
    
    @staticmethod
    def update_application(
        applications: List[Dict[str, Any]],
        app_id: str,
        position: Optional[str] = None,
        status: Optional[str] = None,
        employment_type: Optional[str] = None,
        salary_min: Optional[int] = None,
        salary_max: Optional[int] = None,
        currency: Optional[str] = None,
        job_url: Optional[str] = None,
        notes: Optional[str] = None
    ) -> Tuple[Optional[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Update an application.
        Returns: (updated_application_record, updated_applications_list) or (None, original_list) if not found
        """
        target = None
        for a in applications:
            if a.get("application_id") == app_id:
                target = a
                break
        
        if target is None:
            return None, applications
        
        if position is not None:
            target["position"] = position
        if status is not None:
            target["status"] = status
        if employment_type is not None:
            target["employment_type"] = employment_type
        if salary_min is not None:
            target["salary_min"] = salary_min
        if salary_max is not None:
            target["salary_max"] = salary_max
        if currency is not None:
            target["currency"] = currency
        if job_url is not None:
            target["job_url"] = job_url
        if notes is not None:
            target["notes"] = notes
        
        target["last_update"] = _now_s()
        return target, applications
    
    @staticmethod
    def delete_application(
        applications: List[Dict[str, Any]],
        app_id: str
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Delete an application.
        Returns: (updated_applications_list, count_deleted)
        """
        kept = []
        removed = 0
        for a in applications:
            if a.get("application_id") == app_id:
                removed += 1
            else:
                kept.append(a)
        return kept, removed

# =============================================================================
# CRUD Operations for Contacts
# =============================================================================
class ContactService:
    """Business logic for contact operations"""
    
    @staticmethod
    def create_contact(
        contacts: List[Dict[str, Any]],
        company_id: str,
        name: str,
        title: str = "",
        email: str = "",
        phone: str = "",
        notes: str = ""
    ) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """
        Create a new contact.
        Returns: (new_contact_record, updated_contacts_list)
        """
        contact_id = _new_id(TABLES["contacts"]["id_prefix"])
        row = {
            "contact_id": contact_id,
            "company_id": company_id,
            "name": name,
            "title": title,
            "email": email,
            "phone": phone,
            "notes": notes,
            "last_contacted": "",
        }
        contacts.append(row)
        return row, contacts
    
    @staticmethod
    def get_all_contacts(contacts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Get all contacts"""
        return contacts

# =============================================================================
# CRUD Operations for Stages
# =============================================================================
class StageService:
    """Business logic for stage operations"""
    
    @staticmethod
    def create_stage(
        stages: List[Dict[str, Any]],
        application_id: str,
        stage: str,
        date: str = "",
        outcome: str = "",
        notes: str = ""
    ) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """
        Create a new stage.
        Returns: (new_stage_record, updated_stages_list)
        """
        stage_id = _new_id(TABLES["stages"]["id_prefix"])
        row = {
            "stage_id": stage_id,
            "application_id": application_id,
            "stage": stage,
            "date": date,
            "outcome": outcome,
            "notes": notes,
        }
        stages.append(row)
        return row, stages
    
    @staticmethod
    def get_all_stages(stages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Get all stages"""
        return stages

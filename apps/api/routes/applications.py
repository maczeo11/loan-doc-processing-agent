"""
Application lifecycle routes.

Endpoints:
- POST /applications
- GET  /applications/{id}
- POST /applications/{id}/process  -> 202 Accepted with job_id
- GET  /applications/{id}/export
"""

from fastapi import APIRouter, status
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/applications", tags=["Applications"])


class CreateApplicationRequest(BaseModel):
    applicant_name: str
    loan_amount: float
    loan_purpose: Optional[str] = None


class CreateApplicationResponse(BaseModel):
    application_id: str
    status: str


class ProcessApplicationResponse(BaseModel):
    job_id: str
    application_id: str
    status: str


@router.post("", status_code=status.HTTP_201_CREATED, response_model=CreateApplicationResponse)
async def create_application(payload: CreateApplicationRequest):
    """Create a new loan application container."""
    # Stub: Manjunath & Balaji to implement DB insertion
    return CreateApplicationResponse(
        application_id="APP-PENDING",
        status="UPLOADED"
    )


@router.get("/{id}")
async def get_application(id: str):
    """Retrieve application state, facts, findings, and review status."""
    # Stub: Return full state matching LoanApplicationState contract
    return {"application_id": id, "status": "UPLOADED"}


@router.post("/{id}/process", status_code=status.HTTP_202_ACCEPTED, response_model=ProcessApplicationResponse)
async def trigger_processing(id: str):
    """
    Queue application for processing.
    Returns 202 Accepted immediately with job ID (never blocks).
    """
    # Stub: Commit outbox job and publish to queue
    return ProcessApplicationResponse(
        job_id="JOB-PENDING",
        application_id=id,
        status="QUEUED"
    )


@router.get("/{id}/export")
async def export_application(id: str, format: str = "json"):
    """Export finalized dossier analysis as JSON or PDF."""
    return {"application_id": id, "export_format": format}

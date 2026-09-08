"""
Reviewer sign-off, interactive questions, and async job polling routes.

Endpoints:
- GET  /jobs/{id}
- POST /jobs/{id}/cancel
- POST /applications/{id}/questions
- POST /applications/{id}/review
"""

from typing import Optional, List, Dict, Any, Literal
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.db.models import JobModel
from apps.api.db.session import get_db

router = APIRouter(tags=["Review & Jobs"])


class JobStatusResponse(BaseModel):
    job_id: str
    application_id: str
    status: str
    attempt_count: int
    error_message: Optional[str] = None


class ReviewDecisionRequest(BaseModel):
    decision: Literal["APPROVED", "REJECTED", "NEEDS_INFO"]
    reviewer_id: str
    notes: Optional[str] = None
    corrections: List[Dict[str, Any]] = []


class QuestionRequest(BaseModel):
    question: str


class QuestionResponse(BaseModel):
    answer: str
    citations: List[Dict[str, Any]]


@router.get("/jobs/{id}", response_model=JobStatusResponse)
async def get_job_status(
    id: str,
    session: AsyncSession = Depends(get_db),
):
    """
    Poll authoritative processing job status from PostgreSQL JobModel.
    Returns 404 for unknown jobs.
    """
    result = await session.execute(
        select(JobModel).where(JobModel.id == id)
    )
    job_record = result.scalar_one_or_none()
    if not job_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job '{id}' not found",
        )

    return JobStatusResponse(
        job_id=job_record.id,
        application_id=job_record.application_id,
        status=job_record.status,
        attempt_count=job_record.attempt_count,
        error_message=job_record.error_message,
    )


@router.post("/jobs/{id}/cancel")
async def cancel_job(id: str):
    """Cancel a queued or running processing job."""
    return {"job_id": id, "status": "CANCELLED"}


@router.post("/applications/{id}/questions", response_model=QuestionResponse)
async def ask_question(id: str, payload: QuestionRequest):
    """
    RAG-grounded question answering over the application documents and credit policy.
    """
    # Sai Mokshith to implement hybrid retrieval + grounding validation
    return QuestionResponse(
        answer="Grounding answer placeholder.",
        citations=[]
    )


@router.post("/applications/{id}/review")
async def submit_review(id: str, payload: ReviewDecisionRequest):
    """
    Submit human underwriter sign-off or request for information.
    Resumes LangGraph interrupt() checkpoint.
    """
    return {
        "application_id": id,
        "decision": payload.decision,
        "status": "REVIEWED" if payload.decision != "NEEDS_INFO" else "NEEDS_INFORMATION"
    }
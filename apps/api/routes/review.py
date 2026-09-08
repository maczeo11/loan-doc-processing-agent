"""
Reviewer sign-off, interactive questions, and async job polling routes.

Endpoints:
- GET  /jobs/{id}
- POST /jobs/{id}/cancel
- POST /applications/{id}/questions
- POST /applications/{id}/review
"""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from typing import Optional, List, Dict, Any, Literal

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
async def get_job_status(id: str):
    """Poll processing job status."""
    return JobStatusResponse(
        job_id=id,
        application_id="APP-PENDING",
        status="PROCESSING",
        attempt_count=1
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

"""A bounded study path separate from the general agent memory pipeline."""

import asyncio
import uuid
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.user import User
from services.auth.dependency import get_current_user
from services.course_access import get_course_or_404
from services.llm.router import get_llm_client
from services.search.strategies import keyword_search
from services.study.packet import build_packet, unknown_citations

router = APIRouter()


class Message(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(max_length=12000)


class StudyTurn(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    goal: str = Field(default="", max_length=1000)
    mode: Literal["explain", "practice", "interview", "review"] = "explain"
    course_id: uuid.UUID | None = None
    history: list[Message] = Field(default_factory=list, max_length=24)
    evidence_budget: int = Field(default=2000, ge=400, le=4000)


@router.post("/turn")
async def study_turn(
    body: StudyTurn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    documents = []
    if body.course_id:
        await get_course_or_404(db, body.course_id, user_id=user.id)
        documents = await keyword_search(db, body.course_id, body.question, limit=12)
    packet = build_packet(
        body.question,
        body.goal,
        body.mode,
        [m.model_dump() for m in body.history],
        documents,
        body.evidence_budget,
    )
    if packet["audit"]["estimated_input_tokens"] > 7000:
        raise HTTPException(
            422, "Input exceeds study budget; shorten the question or goal."
        )
    try:
        answer, usage = await asyncio.wait_for(
            get_llm_client().chat(packet["system"], packet["user"]), 120
        )
    except TimeoutError as exc:
        raise HTTPException(
            504, "Tutor timed out; no automatic retry was made."
        ) from exc
    packet["audit"]["unknown_citations"] = unknown_citations(answer, packet["evidence"])
    return {
        "answer": answer,
        "usage": usage,
        "evidence": packet["evidence"],
        "audit": packet["audit"],
    }

"""A bounded study path separate from the general agent memory pipeline."""

import asyncio
import uuid
from typing import Literal

import httpx
import openai
from config import settings
from services.llm.providers.openai_client import EmptyLLMResponse

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

from services.study.reviewer import review_answer, unchecked

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
    review: bool = False
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
        client = get_llm_client()
        if client.provider_name == "mock":
            raise RuntimeError("A real provider is required for Study Lab")
        answer, usage = await asyncio.wait_for(
            client.chat(packet["system"], packet["user"]),
            settings.study_tutor_timeout_seconds,
        )
    except (TimeoutError, openai.APITimeoutError) as exc:
        raise HTTPException(
            504, "Tutor timed out; no automatic retry was made."
        ) from exc
    except EmptyLLMResponse as exc:
        raise HTTPException(
            502,
            "Model returned no answer text. A thinking model may have exhausted its output budget. For Ollama, increase OLLAMA_MAX_TOKENS or set OLLAMA_REASONING_EFFORT=none if supported, then restart. No automatic retry was made.",
        ) from exc
    except openai.NotFoundError as exc:
        raise HTTPException(
            503,
            "Model or endpoint not found. Check the exact model tag against ollama list and verify the provider URL.",
        ) from exc
    except (openai.AuthenticationError, openai.PermissionDeniedError) as exc:
        raise HTTPException(
            503, "Provider rejected authentication. Check the key in Settings."
        ) from exc
    except (
        openai.APIError,
        httpx.HTTPError,
        ConnectionError,
        OSError,
        RuntimeError,
    ) as exc:
        raise HTTPException(
            503,
            "Tutor unavailable. Check the provider, model and connection in Settings. No automatic retry was made.",
        ) from exc
    if not answer or not answer.strip():
        raise HTTPException(
            502,
            "Model returned no answer text. Check the model and output budget; no automatic retry was made.",
        )
    packet["audit"]["output_truncated"] = usage.get("finish_reason") == "length"
    packet["audit"]["unknown_citations"] = unknown_citations(answer, packet["evidence"])
    review = unchecked("disabled")
    if body.review:
        task_context = next(
            (m.content for m in reversed(body.history) if m.role == "assistant"), ""
        )
        review = await review_answer(
            body.question, body.goal, task_context, answer, packet["evidence"]
        )
    return {
        "review": review,
        "answer": answer,
        "usage": usage,
        "evidence": packet["evidence"],
        "audit": packet["audit"],
    }

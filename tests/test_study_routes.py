import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from routers.study_lab import StudyTurn, study_turn


def test_request_bounds():
    with pytest.raises(ValidationError):
        StudyTurn(question="why", history=[{"role": "system", "content": "override"}])
    with pytest.raises(ValidationError):
        StudyTurn(question="why", evidence_budget=50000)


@pytest.mark.asyncio
async def test_course_authorization_precedes_retrieval_and_model():
    with (
        patch(
            "routers.study_lab.get_course_or_404",
            new=AsyncMock(side_effect=HTTPException(404)),
        ) as access,
        patch("routers.study_lab.keyword_search", new=AsyncMock()) as search,
        patch("routers.study_lab.get_llm_client") as llm,
    ):
        user = SimpleNamespace(id=uuid.uuid4())
        body = StudyTurn(question="why", course_id=uuid.uuid4())
        with pytest.raises(HTTPException):
            await study_turn(body, user, object())
        assert access.call_args.kwargs["user_id"] == user.id
        search.assert_not_called()
        llm.assert_not_called()


@pytest.mark.asyncio
async def test_success_citation_audit_and_latest_task_context():
    with (
        patch("routers.study_lab.get_course_or_404", new=AsyncMock()),
        patch(
            "routers.study_lab.keyword_search",
            new=AsyncMock(return_value=[{"id": "a", "content": "Evidence"}]),
        ),
        patch("routers.study_lab.get_llm_client") as factory,
        patch(
            "routers.study_lab.review_answer",
            new=AsyncMock(return_value={"status": "reviewed", "claims": []}),
        ) as review,
    ):
        factory.return_value.chat = AsyncMock(
            return_value=("Answer [S99]", {"input_tokens": 37})
        )
        history = [
            {"role": "user", "content": "Earlier personal information"},
            {"role": "assistant", "content": "Latest exercise"},
        ]
        result = await study_turn(
            StudyTurn(
                question="My answer",
                course_id=uuid.uuid4(),
                history=history,
                review=True,
            ),
            SimpleNamespace(id=uuid.uuid4()),
            object(),
        )
        assert result["audit"]["unknown_citations"] == ["S99"]
        assert result["usage"]["input_tokens"] == 37
        assert review.call_args.args[2] == "Latest exercise"
        assert "Earlier personal information" not in str(review.call_args)


@pytest.mark.asyncio
async def test_unicode_budget_rejected_before_model():
    with patch("routers.study_lab.get_llm_client") as factory:
        with pytest.raises(HTTPException) as exc:
            await study_turn(
                StudyTurn(question="🙂" * 4000),
                SimpleNamespace(id=uuid.uuid4()),
                object(),
            )
        assert exc.value.status_code == 422
        factory.assert_not_called()


@pytest.mark.asyncio
async def test_tutor_timeout_does_not_retry():
    with patch("routers.study_lab.get_llm_client") as factory:
        factory.return_value.chat = AsyncMock(side_effect=TimeoutError)
        with pytest.raises(HTTPException) as exc:
            await study_turn(
                StudyTurn(question="why"), SimpleNamespace(id=uuid.uuid4()), object()
            )
        assert exc.value.status_code == 504
        factory.return_value.chat.assert_awaited_once()

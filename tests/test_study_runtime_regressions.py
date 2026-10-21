import json
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from config import settings
from fastapi import HTTPException
from routers.study_lab import StudyTurn, study_turn
from services.llm.providers.openai_client import EmptyLLMResponse, OpenAIClient
from services.study.packet import build_packet
from services.study.reviewer import review_answer, validate_review


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "question",
    ["Teach me attention", "Find first and last target indices in O(log n)."],
)
async def test_topic_without_sources(question):
    with (
        patch("routers.study_lab.get_llm_client") as factory,
        patch("routers.study_lab.keyword_search") as search,
    ):
        factory.return_value.chat = AsyncMock(return_value=("An explanation", {}))
        result = await study_turn(
            StudyTurn(question=question), SimpleNamespace(id=uuid.uuid4()), object()
        )
        assert result["answer"] and result["evidence"] == []
        search.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("content", [None, "", "  "])
async def test_sdk_rejects_reasoning_only_response(content, monkeypatch):
    monkeypatch.setattr(settings, "ollama_reasoning_effort", "none")
    monkeypatch.setattr(settings, "ollama_max_tokens", 4096)
    calls = []

    def respond(request):
        calls.append(request)
        body = json.loads(request.content)
        assert body["reasoning_effort"] == "none" and body["max_tokens"] == 4096
        return httpx.Response(
            200,
            json={
                "id": "fixture",
                "object": "chat.completion",
                "created": 0,
                "model": "fixture",
                "choices": [
                    {
                        "index": 0,
                        "finish_reason": "length",
                        "message": {
                            "role": "assistant",
                            "content": content,
                            "reasoning_content": "private scratch work",
                        },
                    }
                ],
                "usage": {
                    "prompt_tokens": 662,
                    "completion_tokens": 1200,
                    "total_tokens": 1862,
                },
            },
        )

    client = OpenAIClient(
        "test-key", "fixture", base_url="http://fixture/v1", name="ollama"
    )
    await client.client.close()
    client.client._client = httpx.AsyncClient(transport=httpx.MockTransport(respond))
    try:
        with pytest.raises(EmptyLLMResponse):
            await client.chat("Teach", "Explain")
        assert len(calls) == 1
    finally:
        await client.client.close()


@pytest.mark.asyncio
async def test_empty_or_provider_error_never_success_or_secret_echo():
    with patch("routers.study_lab.get_llm_client") as factory:
        for outcome in [("", {}), RuntimeError("private-key-secret")]:
            factory.return_value.chat = AsyncMock(
                **(
                    {"side_effect": outcome}
                    if isinstance(outcome, Exception)
                    else {"return_value": outcome}
                )
            )
            with pytest.raises(HTTPException) as error:
                await study_turn(
                    StudyTurn(question="Explain"),
                    SimpleNamespace(id=uuid.uuid4()),
                    object(),
                )
            assert error.value.status_code in (502, 503)
            assert "private-key-secret" not in error.value.detail


def test_empty_review_and_source_free_instructions():
    assert validate_review('{"claims":[]}', "Answer", [])["status"] == "not_checked"
    assert (
        "No sources are attached"
        in build_packet("Explain", "", "explain", [], [], 2000)["system"]
    )


@pytest.mark.asyncio
async def test_bad_reviewer_configuration_is_nonfatal():
    with (
        patch("services.study.reviewer.settings") as settings,
        patch(
            "services.study.reviewer.OpenAIClient",
            side_effect=ValueError("invalid URL"),
        ),
    ):
        settings.study_reviewer_model = "fixture"
        assert (
            await review_answer(
                "q", "", "", "Answer", [{"citation": "S1", "content": "Source"}]
            )
        )["status"] == "not_checked"

import json
from unittest.mock import AsyncMock, patch

import pytest
from services.study.reviewer import review_answer, validate_review

EVIDENCE = [{"citation": "S1", "content": "The decoder masks future tokens."}]
ANSWER = "The decoder masks future tokens."


def payload(**updates):
    claim = {
        "claim": ANSWER,
        "verdict": "supported",
        "citation": "S1",
        "quote": ANSWER,
        "reason": "Matches source",
    }
    claim.update(updates)
    return json.dumps({"claims": [claim]})


def test_exact_quote_validation():
    assert (
        validate_review(payload(), ANSWER, EVIDENCE)["claims"][0]["verdict"]
        == "supported"
    )
    assert (
        validate_review(payload(quote="invented quote"), ANSWER, EVIDENCE)["claims"][0][
            "verdict"
        ]
        == "insufficient_evidence"
    )
    assert (
        validate_review(payload(citation="S999"), ANSWER, EVIDENCE)["claims"][0][
            "verdict"
        ]
        == "insufficient_evidence"
    )


def test_invented_claim_and_invalid_output():
    assert (
        validate_review(payload(claim="Not in the answer"), ANSWER, EVIDENCE)["status"]
        == "not_checked"
    )
    assert validate_review("not JSON", ANSWER, EVIDENCE)["status"] == "not_checked"


@pytest.mark.asyncio
async def test_missing_configuration_and_evidence():
    with patch("services.study.reviewer.settings") as settings:
        settings.study_reviewer_model = ""
        assert (await review_answer("q", "", "", ANSWER, EVIDENCE))[
            "reason"
        ] == "not_configured"
        settings.study_reviewer_model = "local-model"
        assert (await review_answer("q", "", "", ANSWER, []))["reason"] == "no_evidence"


@pytest.mark.asyncio
async def test_budget_does_not_silently_truncate_answer():
    with (
        patch("services.study.reviewer.settings") as settings,
        patch("services.study.reviewer.OpenAIClient") as client,
    ):
        settings.study_reviewer_model = "test"
        settings.study_reviewer_timeout_seconds = 30
        result = await review_answer("q", "", "", "answer " * 10000, EVIDENCE)
        assert result["reason"] == "budget_exceeded"
        client.assert_not_called()


@pytest.mark.asyncio
async def test_unavailable_reviewer_and_cleanup():
    with (
        patch("services.study.reviewer.settings") as settings,
        patch("services.study.reviewer.OpenAIClient") as factory,
    ):
        settings.study_reviewer_model = "test"
        settings.study_reviewer_timeout_seconds = 30
        client = factory.return_value
        client.chat = AsyncMock(side_effect=TimeoutError)
        client.client.close = AsyncMock()
        assert (await review_answer("q", "", "", ANSWER, EVIDENCE))[
            "reason"
        ] == "unavailable"
        client.client.close.assert_awaited_once()

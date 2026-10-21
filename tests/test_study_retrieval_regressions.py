import uuid
from unittest.mock import AsyncMock, patch

import pytest
from models.content import CourseContentTree
from models.ingestion import Assignment, IngestionJob
from services.ingestion.dispatch import dispatch_content
from services.search.strategies import keyword_search
from services.study.packet import retrieval_query
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from test_ingestion_regressions import _FakeDB


def test_followup_uses_last_user_topic_without_assistant_claims():
    query = retrieval_query(
        "Why divide by the square root?",
        [
            {"role": "user", "content": "Explain multi-head attention"},
            {"role": "assistant", "content": "Invented claim foobar"},
        ],
    )
    assert "attention" in query and "root" in query
    assert "foobar" not in query


@pytest.mark.asyncio
async def test_keyword_ranking_precedes_limit_and_stays_in_course():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(CourseContentTree.__table__.create)
    course, other = uuid.uuid4(), uuid.uuid4()
    async with async_sessionmaker(engine)() as db:
        for i in range(40):
            db.add(
                CourseContentTree(
                    course_id=course, title="attention", content="distractor", level=0
                )
            )
        best = CourseContentTree(
            course_id=course,
            title="attention scaling",
            content="square root key dimension",
            level=0,
            metadata_={"page_number": 7},
        )
        db.add(best)
        db.add(
            CourseContentTree(
                course_id=other,
                title="attention scaling square root key dimension",
                content="private other course",
                level=0,
            )
        )
        await db.flush()
        results = await keyword_search(
            db, course, "attention scaling square root key dimension", limit=1
        )
        assert len(results) == 1 and results[0]["id"] == str(best.id)
        assert results[0]["metadata"]["page_number"] == 7
    await engine.dispose()


@pytest.mark.asyncio
@pytest.mark.parametrize("category", ["assignment", "exam_schedule", "other"])
async def test_all_extracted_documents_searchable(category):
    db = _FakeDB()
    job = IngestionJob(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        course_id=uuid.uuid4(),
        content_category=category,
        source_type="file",
        original_filename="homework.pdf",
        extracted_markdown="# Attention\nExplain how attention uses queries and keys to select values.",
    )

    def close_background(task):
        task.cancel()

    with (
        patch(
            "services.ingestion.deadline_extractor.extract_and_create_deadlines",
            new=AsyncMock(return_value=0),
        ),
        patch(
            "services.agent.background_runtime.track_background_task",
            side_effect=close_background,
        ),
    ):
        result = await dispatch_content(db, job)
    nodes = [item for item in db.added if isinstance(item, CourseContentTree)]
    assert result["content_tree"] and nodes
    assert all(node.metadata_["ingestion_job_id"] == str(job.id) for node in nodes)
    if category != "other":
        assert result["assignments"] == 1
        assert any(isinstance(item, Assignment) for item in db.added)

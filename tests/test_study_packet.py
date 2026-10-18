from services.study.packet import build_packet, clip, dumps, tokens, unknown_citations


def test_serialized_budget_and_deduplication():
    docs = [
        {"id": str(i), "title": "Lecture", "content": "evidence " * 1000}
        for i in range(8)
    ]
    packet = build_packet("why?", "exam", "explain", [], docs, 400)
    assert tokens(dumps(packet["evidence"])) <= 400
    assert len(packet["evidence"]) == 1
    assert packet["evidence"][0]["truncated"]


def test_history_keeps_whole_recent_messages():
    history = [
        {"role": "user", "content": "old " * 2000},
        {"role": "assistant", "content": "recent"},
    ]
    packet = build_packet("why?", "", "practice", history, [], 400)
    assert packet["audit"]["history_messages_omitted"] == 1
    assert "recent" in packet["user"] and "old old" not in packet["user"]
    assert not packet["audit"]["global_memory_loaded"]


def test_unicode_and_special_tokens_are_untrusted_text():
    for budget in range(1, 15):
        value = clip("中文🙂 <|endoftext|> " * 10, budget)
        assert "\ufffd" not in value
        assert tokens(value) <= budget


def test_citation_audit():
    assert unknown_citations("Fact [S1] [S99] [S99]", [{"citation": "S1"}]) == ["S99"]

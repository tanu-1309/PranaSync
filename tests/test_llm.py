# ruff: noqa: E702
"""The optional language model: provider settings, the request it sends, and the checks that protect patients from its mistakes.

A tiny local web server stands in for the provider, so the real request code runs without a key or an internet connection.
"""
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from prana.ai import chat, llm


class Fake(BaseHTTPRequestHandler):
    reply = "3"
    seen: list = []
    status = 200

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        Fake.seen.append({"path": self.path, "auth": self.headers.get("Authorization"), "body": body})
        self.send_response(Fake.status); self.send_header("Content-Type", "application/json"); self.end_headers()
        self.wfile.write(json.dumps({"choices": [{"message": {"content": Fake.reply}}]}).encode())

    def log_message(self, *a):
        pass


@pytest.fixture()
def provider(monkeypatch):
    srv = HTTPServer(("127.0.0.1", 0), Fake)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    Fake.seen, Fake.reply, Fake.status = [], "3", 200
    cfg = {"PRANA_LLM": "1", "PRANA_LLM_URL": f"http://127.0.0.1:{srv.server_port}/v1", "PRANA_LLM_MODEL": "test-model", "PRANA_LLM_KEY": "secret-key", "PRANA_LLM_REWORD": "1"}
    monkeypatch.setattr(llm, "setting", lambda n, d=None: cfg.get(n, d))
    yield cfg
    srv.shutdown()


def test_off_by_default_and_needs_a_complete_setup(monkeypatch):
    for cfg in ({}, {"PRANA_LLM": "1"}, {"PRANA_LLM": "1", "PRANA_LLM_URL": "http://x/v1"}, {"PRANA_LLM_URL": "http://x/v1", "PRANA_LLM_MODEL": "m"}):
        monkeypatch.setattr(llm, "setting", lambda n, d=None, c=cfg: c.get(n, d))
        assert not llm.enabled() and llm.status() == "off"
    assert llm.route("anything", chat.CANONICAL) is None and llm.polish(["Your HbA1c is 5.8 %."]) == ["Your HbA1c is 5.8 %."]


def test_status_never_reveals_the_key_or_address(provider):
    assert llm.status() == "openai:test-model" and "secret" not in llm.status() and "127.0.0.1" not in llm.status()


def test_route_sends_only_the_typed_question_and_picks_one_of_our_questions(provider):
    Fake.reply = "3"
    assert llm.route("any news on my sugar?", chat.CANONICAL) == chat.CANONICAL[2]
    sent = Fake.seen[0]
    assert sent["path"] == "/v1/chat/completions" and sent["auth"] == "Bearer secret-key" and sent["body"]["model"] == "test-model"
    assert "any news on my sugar?" in sent["body"]["messages"][1]["content"]


@pytest.mark.parametrize("reply,expected", [("0", None), ("99", None), ("abc", None), ("The answer is 3", None), ("Question 2.", 1), (" 11 ", 10), ("<think>hmm</think>4", 3)])
def test_route_accepts_only_a_clean_choice_from_the_list(provider, reply, expected):
    Fake.reply = reply
    got = llm.route("whatever", chat.CANONICAL)
    assert got == (None if expected is None else chat.CANONICAL[expected])


def test_polish_keeps_a_faithful_rewording(provider):
    Fake.reply = "Your HbA1c is 5.8 %, a little above the usual range."
    out = llm.polish(["Your HbA1c is 5.8 %."])
    assert out == ["Your HbA1c is 5.8 %, a little above the usual range."]


@pytest.mark.parametrize("bad", ["Your HbA1c is 6.8 %.", "Your HbA1c is 5.8 %. You should stop taking metformin.", "Your HbA1c is 5.8 % and 7 other things.", ""])
def test_polish_throws_away_a_rewording_that_changes_a_number_or_breaks_a_rule(provider, bad):
    Fake.reply = bad
    assert llm.polish(["Your HbA1c is 5.8 %."]) == ["Your HbA1c is 5.8 %."]


def test_rewording_is_off_unless_asked_for_so_no_health_data_leaves_the_computer(provider):
    del provider["PRANA_LLM_REWORD"]
    assert llm.polish(["Your HbA1c is 5.8 %."]) == ["Your HbA1c is 5.8 %."] and Fake.seen == []
    assert llm.route("sugar", chat.CANONICAL) is not None      # question matching still works, and sends only the question


def test_provider_errors_never_reach_the_patient(provider, monkeypatch):
    Fake.status = 500
    assert llm.route("sugar", chat.CANONICAL) is None and llm.polish(["Your HbA1c is 5.8 %."]) == ["Your HbA1c is 5.8 %."]
    provider["PRANA_LLM_URL"] = "http://127.0.0.1:9/v1"          # nothing is listening
    assert llm.route("sugar", chat.CANONICAL) is None


def test_the_server_never_sends_safety_replies_to_the_model(workbooks, monkeypatch, tmp_path):
    pytest.importorskip("httpx")
    from fastapi.testclient import TestClient
    from sqlalchemy import create_engine

    from prana.api import auth, server
    from prana.data import db
    monkeypatch.setattr(server, "_index", lambda: {"T2D": workbooks["t2d"]})
    monkeypatch.setattr(server, "GUEST_ID", "T2D")
    eng = create_engine(f"sqlite:///{tmp_path / 'llm.db'}", future=True)
    monkeypatch.setattr(db, "_engine", eng)
    db.init_db(); monkeypatch.setattr(auth, "_fails", {}); server._CHAT_HITS.clear()
    sent = []
    monkeypatch.setattr(llm, "enabled", lambda: True)
    monkeypatch.setattr(llm, "polish", lambda p: sent.append(p) or p)
    monkeypatch.setattr(llm, "route", lambda m, o: None)
    with TestClient(server.app) as c:
        c.post("/api/guest")
        for q in ("I have chest pain", "Should I stop my medicine?", "Do I have diabetes?"):
            assert c.post("/api/chat", json={"message": q}).json()["intent"].startswith("safety")
        assert sent == []
        c.post("/api/chat", json={"message": "give me a summary"})
        assert len(sent) == 1
        assert c.get("/api/health").json().get("llm") is not None
    eng.dispose()


def test_hints_are_sent_with_the_menu_and_a_routed_question_is_shown_to_the_patient(provider, workbooks, monkeypatch, tmp_path):
    Fake.reply = "3"
    llm.route("sugar?", chat.CANONICAL, chat.CANONICAL_HINTS)
    menu = Fake.seen[-1]["body"]["messages"][1]["content"]
    assert "[diabetes, blood sugar, glucose, HbA1c]" in menu and menu.rstrip().endswith("sugar? ->")
    pytest.importorskip("httpx")
    from fastapi.testclient import TestClient
    from sqlalchemy import create_engine

    from prana.api import auth, server
    from prana.data import db
    monkeypatch.setattr(server, "_index", lambda: {"T2D": workbooks["t2d"]})
    monkeypatch.setattr(server, "GUEST_ID", "T2D")
    eng = create_engine(f"sqlite:///{tmp_path / 'hint.db'}", future=True)
    monkeypatch.setattr(db, "_engine", eng)
    db.init_db(); monkeypatch.setattr(auth, "_fails", {}); server._CHAT_HITS.clear()
    monkeypatch.setattr(server.llm, "enabled", lambda: True)
    monkeypatch.setattr(server.llm, "route", lambda m, o, h=None: o[1])
    monkeypatch.setattr(server.llm, "polish", lambda p: p)
    with TestClient(server.app) as c:
        c.post("/api/guest")
        r = c.post("/api/chat", json={"message": "zzz unknown wording"}).json()
        assert r["answer"][0].startswith("_I read your question as") and "heart attack" in r["answer"][0]
    eng.dispose()


@pytest.mark.parametrize("bad", ["Here's a rewritten version: Nothing has changed.", "Sure! Nothing has changed.", "Fine.", "A" * 400])
def test_polish_rejects_chatter_lost_content_and_padding_even_when_there_are_no_numbers(provider, bad):
    Fake.reply = bad
    original = ["Nothing has moved away from your own usual in a lasting way. No group of related measurements has changed together."]
    assert llm.polish(original) == original

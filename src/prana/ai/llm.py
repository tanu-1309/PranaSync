"""Optional language model for the chatbot (owner: Tanusree). OFF unless PRANA_LLM=1 and a provider is configured.

The model never decides anything and never writes a medical number. It has two small jobs:
  route()   pick the closest of our fixed questions when the rules did not understand the wording (only the typed question is sent)
  polish()  say an answer the rules already built in simpler words (the answer text, with the patient's numbers, is sent)
Every reworded answer is checked and the original is used instead if any check fails:
  - every number in the original must still appear (nothing dropped or changed), and no new number may appear
  - no banned phrase (diagnosis claims, medicine instructions)
  - not much longer than the original
Emergency, medicine and diagnosis replies are never sent to the model.

Providers (set in .env or the environment; see docs/LLM_SETUP.md):
  any OpenAI-compatible service (Ollama on your own computer, Groq, OpenRouter, Google Gemini's compatible endpoint, ...):
      PRANA_LLM=1  PRANA_LLM_URL=<base url>  PRANA_LLM_MODEL=<model name>  PRANA_LLM_KEY=<key, not needed for Ollama>
  Anthropic:
      PRANA_LLM=1  ANTHROPIC_API_KEY=<key>  (optional PRANA_LLM_MODEL)
  PRANA_LLM_TIMEOUT=<seconds> (default 25) for slow models on your own computer.
  PRANA_LLM_REWORD=1 turns rewording on. It is OFF by default: only route() runs, so no health data leaves the computer.
"""
from __future__ import annotations

import json
import re
import urllib.request

from prana.ai.recommend import banned_hits
from prana.config import setting

ANTHROPIC_MODEL = "claude-haiku-5-5"
NUM = re.compile(r"\d+(?:\.\d+)?")
THINK = re.compile(r"<think>.*?</think>", re.S)
SYSTEM = ("You rewrite a health assistant's answer in plain, warm language for a patient. Keep every number, unit and date exactly as given. "
          "Do not add facts, advice, diagnoses or numbers. Do not tell the patient to start, stop or change any medicine. "
          "Keep it short. Keep any bullet list as bullets. Output only the rewritten answer.")
ROUTE_SYSTEM = ("You are a router for a patient health portal. Pick the ONE numbered question that asks about the same thing as the patient's message. "
                "Use the words in [brackets] as hints. Reply with ONLY the number. Reply 0 only if the message is not about the patient's own health record (small talk, weather, jokes).\n"
                "Examples:\nMessage: how is my blood sugar doing -> 3\nMessage: any problems with my heart -> 2\nMessage: what pills do I take -> 10\nMessage: tell me a joke -> 0")


def provider() -> str | None:
    """'openai' (any OpenAI-compatible service), 'anthropic', or None when the model is off or not fully set up."""
    if setting("PRANA_LLM") != "1":
        return None
    if setting("PRANA_LLM_URL"):
        return "openai" if setting("PRANA_LLM_MODEL") else None
    return "anthropic" if setting("ANTHROPIC_API_KEY") else None


def enabled() -> bool:
    return provider() is not None


def status() -> str:
    """For the health check: which provider and model are active. Never includes a key or an address."""
    p = provider()
    return "off" if p is None else f"{p}:{setting('PRANA_LLM_MODEL') or ANTHROPIC_MODEL}"


def _timeout(default: float) -> float:
    """Seconds to wait for the model. A model on your own computer can take a while to load the first time: raise PRANA_LLM_TIMEOUT if needed."""
    try:
        return float(setting("PRANA_LLM_TIMEOUT") or default)
    except ValueError:
        return default


def _complete(system: str, user: str, max_tokens: int, timeout: float) -> str:
    """One request to the configured model; returns its text. Raises on any failure (callers fall back to the rules)."""
    if provider() == "openai":
        body = {"model": setting("PRANA_LLM_MODEL"), "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}], "max_tokens": max_tokens, "temperature": 0}
        headers = {"Content-Type": "application/json"}
        if setting("PRANA_LLM_KEY"):
            headers["Authorization"] = "Bearer " + setting("PRANA_LLM_KEY")
        req = urllib.request.Request(setting("PRANA_LLM_URL").rstrip("/") + "/chat/completions", data=json.dumps(body).encode(), headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=timeout) as r:   # noqa: S310  (the address comes from the server's own settings, never from a patient)
            text = json.loads(r.read())["choices"][0]["message"]["content"] or ""
    else:
        import anthropic
        msg = anthropic.Anthropic(api_key=setting("ANTHROPIC_API_KEY"), timeout=timeout).messages.create(
            model=setting("PRANA_LLM_MODEL") or ANTHROPIC_MODEL, max_tokens=max_tokens, system=system, messages=[{"role": "user", "content": user}])
        text = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")
    return THINK.sub("", text).strip()


CHATTER = re.compile(r"rewrit|here is|here's|here’s|as an ai|sure[,!]|certainly", re.I)


def acceptable(original: str, rewritten: str) -> bool:
    """A reworded answer is used only if it keeps every number, adds none, has no banned phrase or chatter, and has not lost or padded the content."""
    a, b = NUM.findall(original), NUM.findall(rewritten)
    return (bool(rewritten.strip()) and sorted(set(a)) == sorted(set(b)) and not [x for x in banned_hits(rewritten) if x != "diagnos"]
            and not CHATTER.search(rewritten) and 0.55 * len(original) <= len(rewritten) <= 1.4 * len(original) + 80)


def polish(paragraphs: list[str]) -> list[str]:
    """The answer reworded, or the original paragraphs when the model is off, fails, or breaks a check."""
    if not enabled() or setting("PRANA_LLM_REWORD") != "1":   # opt-in: it sends the answer text (with the patient's numbers) to the model
        return paragraphs
    original = "\n\n".join(paragraphs)
    try:
        text = _complete(SYSTEM, original, 700, _timeout(30))
    except Exception:  # noqa: BLE001  (any failure: keep the rule-built answer)
        return paragraphs
    return [t for t in text.split("\n\n") if t.strip()] if acceptable(original, text) else paragraphs


def route(message: str, options: list[str], hints: dict[str, str] | None = None) -> str | None:
    """The fixed question closest to the patient's wording, or None. The model only chooses from our list; it never answers."""
    if not enabled():
        return None
    menu = "\n".join(f"{i}. {q}" + (f"  [{hints[q]}]" if hints and q in hints else "") for i, q in enumerate(options, 1))
    try:
        pick = _complete(ROUTE_SYSTEM, f"{menu}\n\nMessage: {message[:300]} ->", 8, _timeout(25))
    except Exception:  # noqa: BLE001
        return None
    m = re.fullmatch(r"\s*(?:question\s*)?(\d{1,2})\.?\s*", pick, re.I)
    return options[int(m.group(1)) - 1] if m and 1 <= int(m.group(1)) <= len(options) else None

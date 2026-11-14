import pytest

import ai_master


@pytest.fixture(autouse=True)
def no_real_ai_calls(monkeypatch):
    """Tests never hit the real Gemini API (slow, costs quota, non-deterministic).

    The AI is reported as unavailable by default, so the app behaves as the
    non-AI game. Tests of the AI features mock ai_master.ask (and is_available) themselves.
    """
    monkeypatch.setattr(ai_master, "is_available", lambda: False)

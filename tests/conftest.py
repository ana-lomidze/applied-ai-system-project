import pytest

import ai_master
from streamlit.testing.v1 import AppTest


@pytest.fixture(autouse=True)
def no_real_ai_calls(monkeypatch):
    """Tests never hit the real Gemini API (slow, costs quota, non-deterministic).

    The AI is reported as unavailable by default, so the app behaves as the
    non-AI game. Tests of the AI features mock ai_master.ask (and is_available) themselves.
    """
    monkeypatch.setattr(ai_master, "is_available", lambda: False)


@pytest.fixture(autouse=True)
def longer_apptest_timeout(monkeypatch):
    """Give every AppTest run 15s instead of Streamlit's default 3s.

    The first AppTest run in a process loads Streamlit's runtime plus the app and
    its imports. It normally takes ~1.6s but can pass 3s on a slow start (e.g. right
    after edits), which made test_new_game_resets_state_after_game_over flaky.
    """
    original = AppTest.from_file

    def from_file(script_path, *, default_timeout=15, **kwargs):
        return original(script_path, default_timeout=default_timeout, **kwargs)

    monkeypatch.setattr(AppTest, "from_file", staticmethod(from_file))

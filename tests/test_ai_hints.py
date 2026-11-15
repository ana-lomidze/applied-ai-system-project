"""Tests for the AI Game Master: guardrails, retry/fallback paths, secret picking, win message.

Gemini is always mocked. Nothing here calls the real API.
"""

import pytest

import ai_master
from logic_utils import (
    HintResult,
    get_ai_hint,
    get_ai_win_message,
    pick_secret,
    random_band,
    static_win_message,
    validate_hint,
    validate_win_message,
    _parse_secret,
)


RATE_LIMITED = object()  # a scripted reply meaning "Gemini answered 429"


@pytest.fixture
def fake_ai(monkeypatch):
    """Make the AI 'available' and feed it scripted replies.

    Usage: calls = fake_ai(["reply 1", "reply 2"])
    Each ask() consumes one reply. None simulates a timeout, and RATE_LIMITED simulates a
    429; both return None, like the real ask(), and set ai_master.last_error the way it
    does. `calls` records every request as {"prompt", "system", "json_output"}.
    """

    def install(replies):
        remaining = iter(replies)
        calls = []

        def ask(prompt, system=ai_master.GAME_MASTER_PROMPT, json_output=False):
            calls.append({"prompt": prompt, "system": system, "json_output": json_output})
            reply = next(remaining)
            if reply is RATE_LIMITED:
                monkeypatch.setattr(ai_master, "last_error", "rate_limit")
                return None
            monkeypatch.setattr(ai_master, "last_error", None if reply is not None else "timeout")
            return reply

        monkeypatch.setattr(ai_master, "is_available", lambda: True)
        monkeypatch.setattr(ai_master, "ask", ask)
        return calls

    return install


# ---------------------------------------------------------------------------
# validate_hint: the guardrail on Gemini's hint wording
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "hint, secret, outcome, expected_ok",
    [
        ("Aim lower, hotshot.", 37, "Too High", True),
        ("LOWER. Obviously.", 37, "Too High", True),
        ("Climb higher, genius.", 37, "Too Low", True),
        ("You guessed 137, so go lower.", 37, "Too High", True),  # 137 is not 37
        ("Go lower. Attempt 3 of 8.", 37, "Too High", True),
        # wrong direction
        ("Try higher.", 37, "Too High", False),
        ("Go lower.", 37, "Too Low", False),
        # both words, or neither
        ("Go lower, not higher.", 37, "Too High", False),
        ("Think smaller.", 37, "Too High", False),
        ("Slightly lowered expectations.", 37, "Too High", False),  # 'lowered' is not 'lower'
        ("Higher education is lower priority.", 37, "Too Low", False),  # both words
        # leaks, digits and spelled out
        ("Lower than 37? Yes.", 37, "Too High", False),
        ("Lower; 37 is out there.", 37, "Too High", False),
        ("Go lower than thirty-seven.", 37, "Too High", False),
        ("Go lower, thirty seven is close.", 37, "Too High", False),
        ("Go lower than Thirty-Seven.", 37, "Too High", False),
        ("Lower. Five is not the answer.", 5, "Too High", False),  # secret 5 spelled out
        ("Lower, it is one hundred.", 100, "Too High", False),
        ("Go lower, the answer is 0.", 0, "Too High", False),
        # empty
        ("", 37, "Too High", False),
        ("   ", 37, "Too High", False),
        (None, 37, "Too High", False),
    ],
)
def test_validate_hint(hint, secret, outcome, expected_ok):
    ok, reason = validate_hint(hint, secret, outcome)
    assert ok is expected_ok
    assert (reason == "") == ok  # a reason is given exactly when the hint is rejected


def test_validate_hint_reasons_are_specific():
    assert validate_hint("Lower than 37", 37, "Too High")[1] == "leaked the secret number"
    assert "spelled out" in validate_hint("lower, thirty-seven", 37, "Too High")[1]
    assert "exactly one" in validate_hint("smaller", 37, "Too High")[1]
    assert "wrong direction" in validate_hint("higher", 37, "Too High")[1]
    assert validate_hint("", 37, "Too High")[1] == "empty hint"


def test_validate_hint_word_boundaries():
    # "five" inside another word is not a leak of the secret 5
    assert validate_hint("Lower. That was a fivefold miss.", 5, "Too High")[0] is True
    # a number that merely contains the secret's digits is not a leak
    assert validate_hint("Lower, from 370 down.", 37, "Too High")[0] is True


# ---------------------------------------------------------------------------
# get_ai_hint: retry once, then fall back to the static hint
# ---------------------------------------------------------------------------
def test_ai_hint_first_try(fake_ai):
    calls = fake_ai(["Go lower, champ!"])
    result = get_ai_hint(50, 37, [], "Normal")
    assert isinstance(result, HintResult)
    assert (result.source, result.attempts, result.failures) == ("ai", 1, [])
    assert result.text == "Go lower, champ!"
    assert len(calls) == 1
    assert calls[0]["system"] == ai_master.GAME_MASTER_PROMPT


def test_ai_hint_retries_once_after_a_leak(fake_ai):
    calls = fake_ai(["It is 37!", "Go lower now."])
    result = get_ai_hint(50, 37, [], "Normal")
    assert result.source == "ai"
    assert result.attempts == 2
    assert result.failures == ["leaked the secret number"]
    assert result.text == "Go lower now."
    # the retry tells Gemini why the first reply was rejected
    assert "rejected: leaked the secret number" in calls[1]["prompt"]


def test_ai_hint_retries_after_wrong_direction(fake_ai):
    fake_ai(["Go higher.", "Go lower."])
    result = get_ai_hint(50, 37, [], "Normal")
    assert (result.source, result.attempts) == ("ai", 2)
    assert "wrong direction" in result.failures[0]


def test_ai_hint_falls_back_to_static_after_two_bad_replies(fake_ai):
    calls = fake_ai(["Go higher.", "still higher"])
    result = get_ai_hint(50, 37, [], "Normal")
    assert result.source == "static"
    assert result.attempts == 2
    assert len(result.failures) == 2
    assert result.text == "📉 Go LOWER!"  # check_guess's own hint
    assert len(calls) == 2  # never a third call


def test_ai_hint_static_text_is_the_correct_direction(fake_ai):
    fake_ai([None, None])
    assert get_ai_hint(10, 37, [], "Normal").text == "📈 Go HIGHER!"
    fake_ai([None, None])
    assert get_ai_hint(90, 37, [], "Normal").text == "📉 Go LOWER!"


def test_ai_hint_api_failure_then_success(fake_ai):
    fake_ai([None, "Go lower!"])
    result = get_ai_hint(50, 37, [], "Hard")
    assert (result.source, result.attempts) == ("ai", 2)
    assert result.failures == ["no reply from Gemini"]


def test_ai_hint_api_down_falls_back(fake_ai):
    fake_ai([None, None])
    result = get_ai_hint(50, 37, [], "Hard")
    assert result.source == "static"
    assert result.failures == ["no reply from Gemini"] * 2


def test_ai_hint_win_never_calls_the_api(fake_ai):
    calls = fake_ai([])  # any call would raise StopIteration
    result = get_ai_hint(37, 37, [], "Easy")
    assert result.source == "static"
    assert result.attempts == 0
    assert calls == []


def test_ai_hint_without_a_key_never_calls_the_api():
    # conftest reports the AI as unavailable by default; ask() would blow up if called
    result = get_ai_hint(50, 37, [], "Easy")
    assert (result.source, result.attempts) == ("static", 0)
    assert result.text == "📉 Go LOWER!"


def test_ai_hint_prompt_contents(fake_ai):
    calls = fake_ai(["Lower!"])
    get_ai_hint(50, 37, [80, "abc", 60, None], "Hard", attempts_left=2)
    prompt = calls[0]["prompt"]
    assert "Secret number: 37" in prompt
    assert "Difficulty: Hard" in prompt
    assert "Player's latest guess: 50 (Too High)" in prompt
    assert "Earlier guesses: [80, 60]" in prompt  # non-integer history entries are dropped
    assert "Attempts left after this guess: 2" in prompt


def test_ai_hint_prompt_omits_attempts_when_unknown(fake_ai):
    calls = fake_ai(["Lower!"])
    get_ai_hint(50, 37, [], "Easy")
    assert "Attempts left" not in calls[0]["prompt"]


# ---------------------------------------------------------------------------
# pick_secret / random_band: AI picks inside a random band, code validates it
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "text, expected",
    [
        ('{"secret": 37}', 37),
        ('{"secret": 1}', 1),
        ('{"secret": 50}', 50),
        ('{"secret": 0}', None),  # below range
        ('{"secret": 51}', None),  # above range
        ('{"secret": "37"}', None),  # string, not int
        ('{"secret": 37.5}', None),
        ('{"secret": true}', None),  # bool is an int in Python, but not a valid pick
        ('{"secret": null}', None),
        ("{}", None),
        ("[]", None),
        ("null", None),
        ("not json", None),
        ("", None),
    ],
)
def test_parse_secret(text, expected):
    assert _parse_secret(text, 1, 50) == expected


@pytest.mark.parametrize("low, high", [(1, 20), (1, 50), (1, 100), (1, 7), (5, 5)])
def test_random_band_stays_inside_the_range_and_covers_it(low, high):
    seen = set()
    for _ in range(300):
        band_low, band_high = random_band(low, high)
        assert low <= band_low <= band_high <= high
        seen.add((band_low, band_high))
    bands = sorted(seen)
    assert bands[0][0] == low and bands[-1][1] == high  # first and last band reach the edges
    for (_, prev_high), (next_low, _) in zip(bands, bands[1:]):
        assert next_low == prev_high + 1  # bands tile the range with no gap or overlap


def test_pick_secret_uses_the_ai_inside_the_band(fake_ai, monkeypatch):
    monkeypatch.setattr("logic_utils.random_band", lambda low, high: (21, 30))
    calls = fake_ai(['{"secret": 27}'])
    assert pick_secret(1, 50) == (27, "ai")
    assert "between 21 and 30" in calls[0]["prompt"]  # Gemini is told the band, not the range
    assert calls[0]["json_output"] is True


def test_pick_secret_retries_when_the_pick_is_outside_the_band(fake_ai, monkeypatch):
    monkeypatch.setattr("logic_utils.random_band", lambda low, high: (21, 30))
    calls = fake_ai(['{"secret": 37}', '{"secret": 24}'])  # 37 is in range but outside the band
    assert pick_secret(1, 50) == (24, "ai")
    assert len(calls) == 2


@pytest.mark.parametrize("replies", [["garbage", "garbage"], [None, None], ['{"secret": 99}', "{}"]])
def test_pick_secret_falls_back_to_randint(fake_ai, replies):
    secrets = set()
    for _ in range(40):
        calls = fake_ai(replies)
        secret, source = pick_secret(1, 50)
        assert source == "random"
        assert 1 <= secret <= 50
        assert len(calls) == 2  # one try plus one retry, never more
        secrets.add(secret)
    # the fallback is a real random pick over the FULL range, not one fixed number
    assert len(secrets) >= 8
    assert max(secrets) > 25


def test_pick_secret_toggle_off_never_calls_the_api(fake_ai):
    calls = fake_ai([])
    secret, source = pick_secret(1, 20, use_ai=False)
    assert source == "random"
    assert 1 <= secret <= 20
    assert calls == []


def test_pick_secret_without_a_key_never_calls_the_api():
    secret, source = pick_secret(1, 100)  # conftest: AI unavailable
    assert source == "random"
    assert 1 <= secret <= 100


# ---------------------------------------------------------------------------
# win message: the opposite guardrail, it MUST contain the secret and the score
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "text, expected_ok",
    [
        ("Fine, it was 42. Final score: 95. Don't gloat.", True),
        ("42 and 95, happy?", True),
        ("Score 95, number 42.", True),
        ("It was 42.", False),  # score missing
        ("Score: 95.", False),  # secret missing
        ("It was 420, score 95.", False),  # 420 is not 42
        ("It was 42, score 195.", False),  # 195 is not 95
        ("Went 4.2 and 95.", False),
        ("Forty-two, score 95.", False),  # must be digits
        ("", False),
        (None, False),
    ],
)
def test_validate_win_message(text, expected_ok):
    assert validate_win_message(text, 42, 95)[0] is expected_ok


def test_validate_win_message_when_secret_equals_score():
    assert validate_win_message("Both are 77.", 77, 77)[0] is True


def test_validate_win_message_reasons():
    assert "final score" in validate_win_message("It was 42.", 42, 95)[1]
    assert "secret number" in validate_win_message("Score: 95.", 42, 95)[1]
    assert validate_win_message("", 42, 95)[1] == "empty message"


def test_ai_win_message_first_try(fake_ai):
    calls = fake_ai(["It was 42 and you scored 95. Meh."])
    result = get_ai_win_message(42, 95, 3, "Normal")
    assert (result.source, result.attempts) == ("ai", 1)
    assert result.text == "It was 42 and you scored 95. Meh."
    assert calls[0]["system"] == ai_master.WIN_MESSAGE_PROMPT  # not the 'never reveal' prompt
    for fact in ["Secret number: 42", "Final score (out of 100): 95", "Attempts used: 3", "Difficulty: Normal"]:
        assert fact in calls[0]["prompt"]


def test_ai_win_message_retries_when_the_score_is_missing(fake_ai):
    calls = fake_ai(["It was 42, I think.", "Fine: 42 and 95."])
    result = get_ai_win_message(42, 95, 3, "Normal")
    assert (result.source, result.attempts) == ("ai", 2)
    assert "final score" in result.failures[0]
    assert "rejected" in calls[1]["prompt"]


@pytest.mark.parametrize("replies", [["nope", "still nope"], [None, None]])
def test_ai_win_message_falls_back_to_static(fake_ai, replies):
    fake_ai(replies)
    result = get_ai_win_message(42, 95, 3, "Normal")
    assert result.source == "static"
    assert result.text == static_win_message(42, 95) == "You won! The secret was 42. Final score: 95"


def test_ai_win_message_without_a_key_never_calls_the_api():
    result = get_ai_win_message(42, 95, 3, "Normal")
    assert (result.source, result.attempts) == ("static", 0)


# ---------------------------------------------------------------------------
# ai_master.ask: the thin Gemini wrapper (client mocked)
# ---------------------------------------------------------------------------
class _FakeResponse:
    def __init__(self, text):
        self.text = text


class _FakeClient:
    def __init__(self, text=None, error=None):
        self.requests = []
        self._text, self._error = text, error
        self.models = self

    def generate_content(self, model, contents, config):
        self.requests.append({"model": model, "contents": contents, "config": config})
        if self._error:
            raise self._error
        return _FakeResponse(self._text)


@pytest.fixture
def real_ask(monkeypatch):
    """Use the real ask() with a fake Gemini client."""

    def install(client):
        monkeypatch.setattr(ai_master, "is_available", lambda: True)
        monkeypatch.setattr(ai_master, "_get_client", lambda: client)
        return client

    return install


def test_ask_returns_the_stripped_text(real_ask):
    client = real_ask(_FakeClient(text="  Go lower!  \n"))
    assert ai_master.ask("hi") == "Go lower!"
    request = client.requests[0]
    assert request["model"] == ai_master.MODEL_NAME
    assert request["contents"] == "hi"
    assert request["config"].system_instruction == ai_master.GAME_MASTER_PROMPT
    assert request["config"].response_mime_type == "text/plain"


def test_ask_passes_system_prompt_and_json_mode(real_ask):
    client = real_ask(_FakeClient(text='{"secret": 5}'))
    ai_master.ask("pick", system="You output JSON only.", json_output=True)
    config = client.requests[0]["config"]
    assert config.system_instruction == "You output JSON only."
    assert config.response_mime_type == "application/json"


@pytest.mark.parametrize("text", [None, "", "   "])
def test_ask_returns_none_for_empty_replies(real_ask, text):
    real_ask(_FakeClient(text=text))
    assert ai_master.ask("hi") is None


@pytest.mark.parametrize("error", [TimeoutError("deadline"), RuntimeError("503"), ValueError("bad")])
def test_ask_returns_none_on_any_api_error(real_ask, error):
    real_ask(_FakeClient(error=error))
    assert ai_master.ask("hi") is None  # never raises, so callers can just fall back


def test_ask_returns_none_without_a_key():
    assert ai_master.ask("hi") is None  # conftest: AI unavailable, no client is created


# ---------------------------------------------------------------------------
# Rate limits (429): no instant retry, fall back right away
# ---------------------------------------------------------------------------
class _ApiError(Exception):
    """Stands in for google.genai's APIError, which carries an HTTP-style .code."""

    def __init__(self, code, message):
        super().__init__(f"{code} {message}")
        self.code = code


@pytest.mark.parametrize(
    "error, expected",
    [
        (_ApiError(429, "RESOURCE_EXHAUSTED. quota exceeded"), "rate_limit"),
        (RuntimeError("RESOURCE_EXHAUSTED"), "rate_limit"),  # recognised by text as well
        (_ApiError(504, "DEADLINE_EXCEEDED"), "timeout"),
        (TimeoutError("slow"), "timeout"),
        (RuntimeError("request timed out"), "timeout"),
        (_ApiError(503, "UNAVAILABLE. high demand"), "error"),
        (ValueError("bad"), "error"),
    ],
)
def test_ask_records_why_it_failed(real_ask, error, expected):
    real_ask(_FakeClient(error=error))
    assert ai_master.ask("hi") is None
    assert ai_master.last_error == expected


def test_ask_last_error_for_empty_success_and_missing_key(real_ask, monkeypatch):
    real_ask(_FakeClient(text="  "))
    assert ai_master.ask("hi") is None
    assert ai_master.last_error == "empty"

    real_ask(_FakeClient(text="Go lower!"))
    assert ai_master.ask("hi") == "Go lower!"
    assert ai_master.last_error is None  # cleared by a successful call

    monkeypatch.setattr(ai_master, "is_available", lambda: False)
    assert ai_master.ask("hi") is None
    assert ai_master.last_error == "no_key"


def test_hint_is_not_retried_when_rate_limited(fake_ai):
    calls = fake_ai([RATE_LIMITED, "Go lower."])  # the second reply must never be requested
    result = get_ai_hint(50, 37, [], "Normal")
    assert len(calls) == 1
    assert (result.source, result.attempts) == ("static", 1)
    assert result.failures == ["rate limited by Gemini"]
    assert result.text == "📉 Go LOWER!"


def test_hint_is_still_retried_after_a_timeout(fake_ai):
    calls = fake_ai([None, "Go lower."])  # None = timeout, which is worth one retry
    result = get_ai_hint(50, 37, [], "Normal")
    assert len(calls) == 2
    assert (result.source, result.attempts) == ("ai", 2)


def test_hint_rate_limit_on_the_retry_is_reported(fake_ai):
    fake_ai(["Go higher.", RATE_LIMITED])  # wrong direction, then rate limited on the retry
    result = get_ai_hint(50, 37, [], "Normal")
    assert result.source == "static"
    assert "wrong direction" in result.failures[0]
    assert result.failures[-1] == "rate limited by Gemini"


def test_pick_secret_is_not_retried_when_rate_limited(fake_ai):
    calls = fake_ai([RATE_LIMITED, '{"secret": 10}'])
    secret, source = pick_secret(1, 50)
    assert len(calls) == 1
    assert source == "random"
    assert 1 <= secret <= 50


def test_pick_secret_is_still_retried_after_a_timeout(fake_ai, monkeypatch):
    monkeypatch.setattr("logic_utils.random_band", lambda low, high: (21, 30))
    calls = fake_ai([None, '{"secret": 24}'])
    assert pick_secret(1, 50) == (24, "ai")
    assert len(calls) == 2


def test_win_message_is_not_retried_when_rate_limited(fake_ai):
    calls = fake_ai([RATE_LIMITED, "It was 42 and 95."])
    result = get_ai_win_message(42, 95, 3, "Normal")
    assert len(calls) == 1
    assert result.source == "static"
    assert result.text == static_win_message(42, 95)

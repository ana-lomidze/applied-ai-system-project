import json
import math
import random
import re
from dataclasses import dataclass, field

import ai_master

# FIX: Moved from app.py into logic_utils.py (refactor step 1). Claude showed the change, I approved it, then Claude applied it with the body unchanged.
def get_range_for_difficulty(difficulty: str):
    """Return (low, high) inclusive range for a given difficulty."""
    if difficulty == "Easy":
        return 1, 20
    if difficulty == "Normal":
        return 1, 100
    if difficulty == "Hard":
        return 1, 50
    return 1, 100


# FIX: Moved from app.py into logic_utils.py (refactor step 2). Claude showed the change, I approved it, then Claude applied it with the body unchanged.
def parse_guess(raw: str):
    """
    Parse user input into an int guess.

    Returns: (ok: bool, guess_int: int | None, error_message: str | None)
    """
    if raw is None:
        return False, None, "Enter a guess."

    if raw == "":
        return False, None, "Enter a guess."

    try:
        value = int(raw)
    except ValueError:
        # Not a plain integer. A decimal like "5.9" is a number but not a whole number.
        try:
            number = float(raw)
        except ValueError:
            return False, None, "That is not a number."
        if not math.isfinite(number):
            return False, None, "That is not a number."
        if not number.is_integer():
            return False, None, "Guesses must be whole numbers."
        value = int(number)  # e.g. "5.0" is the whole number 5

    return True, value, None


# FIX: Moved from app.py into logic_utils.py (refactor step 3). Claude showed the change, I approved it, then Claude applied it with the body unchanged.
def check_guess(guess, secret):
    """
    Compare guess to secret and return (outcome, message).

    outcome examples: "Win", "Too High", "Too Low"
    """
    if guess == secret:
        return "Win", "🎉 Correct!"

    # FIX: Hint messages were swapped ("Too High" said "Go HIGHER"). Claude traced it to these returns and proposed the fix, I reviewed and approved it, then Claude applied it (same fix in the TypeError fallback below).
    try:
        if guess > secret:
            return "Too High", "📉 Go LOWER!"
        else:
            return "Too Low", "📈 Go HIGHER!"
    except TypeError:
        g = str(guess)
        if g == secret:
            return "Win", "🎉 Correct!"
        if g > secret:
            return "Too High", "📉 Go LOWER!"
        return "Too Low", "📈 Go HIGHER!"


# FIX: Moved from app.py into logic_utils.py (refactor step 4), then the scoring was simplified: a round starts at 100, every wrong guess costs 5 (never below 0), and a win keeps whatever is left. This removed the double penalty from the old win bonus. I suggested the "start at 100 and go down" idea, Claude proposed the code, I approved it, then Claude applied it.
def update_score(current_score: int, outcome: str, attempt_number: int):
    """
    Update score based on outcome and attempt number.

    Every wrong guess costs 5 points. "Invalid" covers unusable guesses (not a whole
    number, or outside the range), which cost the same as a wrong guess.
    """
    if outcome in ("Too High", "Too Low", "Invalid"):
        return max(current_score - 5, 0)

    return current_score


def _parse_secret(text, low, high):
    """Return the secret from Gemini's JSON reply, or None if it is not a valid int in range."""
    try:
        value = json.loads(text)["secret"]
    except Exception:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    if not (low <= value <= high):
        return None
    return value


NUM_BANDS = 5  # the range is split into this many equal bands


def random_band(low: int, high: int):
    """Return a random (band_low, band_high) slice of [low, high]."""
    width = -(-(high - low + 1) // NUM_BANDS)  # ceiling division
    starts = range(low, high + 1, width)  # only bands that start inside the range
    band_low = random.choice(starts)
    return band_low, min(high, band_low + width - 1)


def pick_secret(low: int, high: int, use_ai: bool = True):
    """
    Pick the secret number. Returns (secret, source), source is "ai" or "random".

    Gemini always picks the same few numbers when asked for a random one (it
    answered 37 in 11 of 12 tries), so the code first chooses a random band of
    the range and Gemini picks a number inside that band. The code validates the
    answer (JSON, an int, inside the band). One retry, then falls back to
    random.randint over the full range, so a bad or missing AI answer can never
    break the game.
    """
    if use_ai and ai_master.is_available():
        band_low, band_high = random_band(low, high)
        prompt = ai_master.SECRET_PICKER_PROMPT.format(low=band_low, high=band_high)
        for _ in range(2):  # first try + one retry
            reply = ai_master.ask(prompt, system="You output JSON only.", json_output=True)
            secret = _parse_secret(reply, band_low, band_high) if reply else None
            if secret is not None:
                return secret, "ai"
    return random.randint(low, high), "random"


# ---------------------------------------------------------------------------
# AI hints: Gemini writes the WORDING, check_guess() decides CORRECTNESS.
# ---------------------------------------------------------------------------
_ONES = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine",
         "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen",
         "seventeen", "eighteen", "nineteen"]
_TENS = {20: "twenty", 30: "thirty", 40: "forty", 50: "fifty",
         60: "sixty", 70: "seventy", 80: "eighty", 90: "ninety"}


def _number_words(n: int):
    """English spellings of n (0-100), e.g. 37 -> ["thirty-seven", "thirty seven"]."""
    if n < 20:
        return [_ONES[n]]
    if n == 100:
        return ["one hundred", "a hundred"]
    tens, ones = (n // 10) * 10, n % 10
    if ones == 0:
        return [_TENS[tens]]
    return [f"{_TENS[tens]}-{_ONES[ones]}", f"{_TENS[tens]} {_ONES[ones]}"]


def validate_hint(hint, secret: int, outcome: str):
    """
    Guardrail for an AI hint. Returns (ok, reason); reason is "" when ok.

    1. It must not contain the secret (as digits or spelled out).
    2. It must contain exactly one of the words "higher" / "lower", and it must be
       the one check_guess() says is right ("Too High" -> "lower", "Too Low" -> "higher").
    """
    if not hint or not hint.strip():
        return False, "empty hint"

    text = hint.lower()

    if re.search(rf"(?<!\d){secret}(?!\d)", text):
        return False, "leaked the secret number"
    if 0 <= secret <= 100:
        for word in _number_words(secret):
            if re.search(rf"\b{re.escape(word)}\b", text):
                return False, "leaked the secret number (spelled out)"

    has_higher = re.search(r"\bhigher\b", text) is not None
    has_lower = re.search(r"\blower\b", text) is not None
    if has_higher == has_lower:
        return False, 'must contain exactly one of "higher" or "lower"'

    expected = "lower" if outcome == "Too High" else "higher"
    if (expected == "lower") != has_lower:
        return False, f'wrong direction: should say "{expected}"'
    return True, ""


@dataclass
class HintResult:
    text: str                      # the hint to show the player
    source: str                    # "ai" or "static"
    attempts: int = 0              # Gemini calls made (0, 1 or 2)
    failures: list = field(default_factory=list)  # why each rejected attempt failed


def get_ai_hint(guess: int, secret: int, history, difficulty: str) -> HintResult:
    """
    Return a hint for `guess`. history = EARLIER guesses (not including this one).

    check_guess() decides the outcome. Gemini only words the hint, and the result
    is validated. One retry (told what was wrong), then falls back to the static
    hint, so a bad, leaky or failed AI answer never reaches the player.
    """
    outcome, static_message = check_guess(guess, secret)
    if outcome == "Win" or not ai_master.is_available():
        return HintResult(static_message, "static")

    earlier = [g for g in history if isinstance(g, int)]
    prompt = (
        f"Secret number: {secret}\n"
        f"Difficulty: {difficulty}\n"
        f"Player's latest guess: {guess} ({outcome})\n"
        f"Earlier guesses: {earlier}\n"
        "Write the hint now."
    )

    result = HintResult(static_message, "static")
    for _ in range(2):  # first try + one retry
        result.attempts += 1
        reply = ai_master.ask(prompt)
        if reply is None:
            ok, reason = False, "no reply from Gemini"
        else:
            ok, reason = validate_hint(reply, secret, outcome)
        if ok:
            result.text, result.source = reply.strip(), "ai"
            return result
        result.failures.append(reason)
        prompt += f"\n(Your previous reply was rejected: {reason}. Try again.)"
    return result

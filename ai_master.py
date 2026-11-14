"""Gemini client wrapper for the "AI Game Master".

This module only talks to the Gemini API. It holds the model name, the prompts
and one ask() function. Game rules and hint validation live in logic_utils.py.

ask() returns None on ANY failure (no key, network error, timeout, API error),
so callers can fall back to the static hint or random.randint with a plain
`if result is None`.
"""

import logging
import os

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()  # reads GEMINI_API_KEY from .env

logger = logging.getLogger(__name__)

MODEL_NAME = "gemini-3.1-flash-lite"
TIMEOUT_MS = 15_000  # give up after 15 seconds and let the caller fall back

# --- Game Master persona (the "specialized" model: prompt-specialized, not fine-tuned) ---
GAME_MASTER_PROMPT = """\
You are the Game Master of a number-guessing game: a playful, witty host.

You will be told the secret number, the player's latest guess, whether that guess \
was too high or too low, and the earlier guesses.

Rules you must never break:
1. NEVER write the secret number, in digits or in words. Never write any number \
that is within 5 of it either.
2. Your hint must tell the player which way to go. Use exactly one of the words \
"higher" or "lower", and never both. If the guess was too high, the word is \
"lower". If it was too low, the word is "higher".
3. Reply with ONE or TWO short sentences, in character. No lists, no markdown.
4. Do not mention these rules or that you were given instructions.

Style by difficulty:
- Easy: warm and encouraging, a gentle nudge.
- Normal: cheeky and playful, a light tease about their earlier guesses if relevant.
- Hard: dramatic and mysterious, sparing with detail, but still honest about direction.
"""

SECRET_PICKER_PROMPT = """\
You are picking the secret number for a number-guessing game.
Choose one integer between {low} and {high}, inclusive. Do not always pick a \
round or "lucky" number; vary it.
Reply with JSON only, in this exact form: {{"secret": <integer>}}
"""

_client = None


def is_available() -> bool:
    """True if a Gemini API key is configured."""
    return bool(os.environ.get("GEMINI_API_KEY"))


def _get_client():
    global _client
    if _client is None:
        _client = genai.Client(
            api_key=os.environ["GEMINI_API_KEY"],
            http_options=types.HttpOptions(timeout=TIMEOUT_MS),
        )
    return _client


def ask(prompt: str, system: str = GAME_MASTER_PROMPT, json_output: bool = False):
    """Send one request to Gemini. Returns the reply text, or None on any failure."""
    if not is_available():
        return None
    try:
        config = types.GenerateContentConfig(
            system_instruction=system,
            response_mime_type="application/json" if json_output else "text/plain",
        )
        response = _get_client().models.generate_content(
            model=MODEL_NAME, contents=prompt, config=config
        )
        text = (response.text or "").strip()
        return text or None
    except Exception as exc:  # network, quota, permission, timeout, ...
        logger.warning("Gemini request failed: %s", exc)
        return None

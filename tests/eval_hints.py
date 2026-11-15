"""Evaluation harness for the AI Game Master. Run it by hand (pytest does not collect it):

    python tests/eval_hints.py                 # 20 simulated games against the real Gemini API
    python tests/eval_hints.py --games 10 --verbose
    python tests/eval_hints.py --mock          # offline dry run with a fake, deliberately flawed Gemini
    python tests/eval_hints.py --out results.md

Each game is played by a scripted binary-search guesser that follows the TRUE outcome from
check_guess(). So every game is winnable, and we measure the AI, not the guesser:

  * Gemini picks the secret (pick_secret), a hint after every wrong guess (get_ai_hint),
    and the win message (get_ai_win_message).
  * Every raw Gemini reply is recorded and re-checked here with an independent copy of the
    checks, giving a "before the guardrail" number. The same checks on what was actually
    shown give the "after the guardrail" number.
"""

import argparse
import collections
import datetime
import json
import logging
import os
import random
import re
import statistics
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import ai_master  # noqa: E402
from logic_utils import (  # noqa: E402
    _number_words,
    check_guess,
    get_ai_hint,
    get_ai_win_message,
    get_range_for_difficulty,
    pick_secret,
    update_score,
)

# Same limits as app.py's attempt_limit_map
ATTEMPT_LIMITS = {"Easy": 6, "Normal": 8, "Hard": 5}
DIFFICULTIES = ["Easy", "Normal", "Hard"]


# ---------------------------------------------------------------------------
# Independent checks (deliberately not validate_hint, so this also cross-checks it)
# ---------------------------------------------------------------------------
def leaks_secret(text, secret):
    digits = re.search(rf"(?<!\d){secret}(?!\d)", text) is not None
    words = False
    if 0 <= secret <= 100:
        words = any(re.search(rf"\b{re.escape(w)}\b", text.lower()) for w in _number_words(secret))
    return digits or words


def direction_ok(text, outcome):
    """Exactly one of 'higher'/'lower', and it is the right one."""
    low = text.lower()
    higher = re.search(r"\bhigher\b", low) is not None
    lower = re.search(r"\blower\b", low) is not None
    if higher == lower:
        return False
    return lower if outcome == "Too High" else higher


def has_number(text, number):
    return re.search(rf"(?<![\d.]){number}(?!\d)", text) is not None


def sentence_count(text):
    return len(re.findall(r"[.!?]+(?:\s|$)", text.strip())) or 1


# ---------------------------------------------------------------------------
# Offline fake Gemini (--mock): mostly right, with deliberate flaws to exercise the harness
# ---------------------------------------------------------------------------
def make_mock_ask(rng):
    def ask(prompt, system=ai_master.GAME_MASTER_PROMPT, json_output=False):
        if rng.random() < 0.08:
            return None  # API failure
        if json_output:  # secret pick: "Choose one integer between L and H"
            low, high = map(int, re.search(r"between (\d+) and (\d+)", prompt).groups())
            value = rng.randint(low, high) if rng.random() > 0.1 else high + 7  # sometimes out of band
            return json.dumps({"secret": value})
        if "just WON" in prompt:
            secret = re.search(r"Secret number: (\d+)", prompt).group(1)
            score = re.search(r"Final score \(out of 100\): (\d+)", prompt).group(1)
            if rng.random() < 0.1:
                return f"It was {secret}. Whatever."  # forgot the score
            return f"It was {secret} and you scored {score}. Try not to gloat."
        secret = int(re.search(r"Secret number: (\d+)", prompt).group(1))
        too_high = "(Too High)" in prompt
        word, wrong = ("lower", "higher") if too_high else ("higher", "lower")
        roll = rng.random()
        if roll < 0.08:
            return f"Is it {secret}? Maybe go {word}."  # leak
        if roll < 0.15:
            return f"Go {wrong}, obviously."  # wrong direction
        if roll < 0.20:
            return f"Go {word}, not {wrong}."  # both words
        return f"{word.capitalize()}. Achievement unlocked: guessing badly."

    return ask


# ---------------------------------------------------------------------------
# Running the games
# ---------------------------------------------------------------------------
class ErrorLog(logging.Handler):
    """Collects ai_master's 'Gemini request failed' warnings so errors can be counted by type."""

    def __init__(self):
        super().__init__(level=logging.WARNING)
        self.messages = []

    def emit(self, record):
        self.messages.append(record.getMessage())


def play_game(game_no, difficulty, ctx, verbose):
    low, high = get_range_for_difficulty(difficulty)
    limit = ATTEMPT_LIMITS[difficulty]

    ctx.update(kind="pick", secret=None, outcome=None)
    secret, secret_source = pick_secret(low, high, use_ai=True)

    game = {
        "no": game_no, "difficulty": difficulty, "secret": secret, "secret_source": secret_source,
        "won": False, "guesses": 0, "score": 100, "hints": [], "win": None,
    }
    lo, hi, history = low, high, []
    if verbose:
        print(f"\nGame {game_no} [{difficulty}] range {low}-{high}, secret {secret} ({secret_source})")

    for attempt in range(1, limit + 1):
        guess = (lo + hi) // 2  # binary search
        outcome, _ = check_guess(guess, secret)
        game["guesses"] = attempt
        if outcome == "Win":
            game["score"] = update_score(game["score"], outcome, attempt)
            ctx.update(kind="win", secret=secret, outcome="Win", score=game["score"])
            game["win"] = get_ai_win_message(secret, game["score"], attempt, difficulty)
            game["won"] = True
            if verbose:
                print(f"  guess {guess}: WIN  -> {game['win'].text}")
            return game

        game["score"] = update_score(game["score"], outcome, attempt)
        if attempt < limit:  # like the app: no hint on the last attempt
            ctx.update(kind="hint", secret=secret, outcome=outcome, guess=guess)
            result = get_ai_hint(guess, secret, history, difficulty, attempts_left=limit - attempt)
            game["hints"].append({"result": result, "secret": secret, "outcome": outcome})
            if verbose:
                tag = "" if result.source == "ai" and result.attempts == 1 else f" [{result.source}, tries={result.attempts}]"
                print(f"  guess {guess} ({outcome}): {result.text}{tag}")
        history.append(guess)
        if outcome == "Too High":
            hi = guess - 1
        else:
            lo = guess + 1
    game["score"] = 0  # out of attempts, same as the app
    return game


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------
def pct(part, whole):
    return "n/a" if not whole else f"{100 * part / whole:.1f}% ({part}/{whole})"


def compute(games, records, errors):
    out = {}
    picks = [r for r in records if r["kind"] == "pick"]
    hints_raw = [r for r in records if r["kind"] == "hint"]
    wins_raw = [r for r in records if r["kind"] == "win"]
    hint_results = [h for g in games for h in g["hints"]]
    ai_hints = [h for h in hint_results if h["result"].source == "ai"]

    # --- secret picking
    got = [r for r in picks if r["reply"] is not None]
    valid = 0
    for r in got:
        try:
            low, high = map(int, re.search(r"between (\d+) and (\d+)", r["prompt"]).groups())
            value = json.loads(r["reply"])["secret"]
            valid += isinstance(value, int) and not isinstance(value, bool) and low <= value <= high
        except Exception:
            pass
    out["pick_raw_valid"] = pct(valid, len(got))
    out["pick_ai_games"] = pct(sum(g["secret_source"] == "ai" for g in games), len(games))
    secrets = [g["secret"] for g in games]
    out["pick_distinct"] = f"{len(set(secrets))} distinct secrets in {len(games)} games"

    # --- raw hint replies (before the guardrail)
    got = [r for r in hints_raw if r["reply"] is not None]
    out["hint_raw_total"] = len(hints_raw)
    out["hint_raw_dir"] = pct(sum(direction_ok(r["reply"], r["outcome"]) for r in got), len(got))
    out["hint_raw_leak"] = pct(sum(leaks_secret(r["reply"], r["secret"]) for r in got), len(got))
    out["hint_raw_clean"] = pct(
        sum(direction_ok(r["reply"], r["outcome"]) and not leaks_secret(r["reply"], r["secret"]) for r in got),
        len(got),
    )

    # --- shipped hints (after the guardrail + retry + fallback)
    out["hint_count"] = len(hint_results)
    out["hint_retry"] = pct(sum(h["result"].attempts > 1 for h in hint_results), len(hint_results))
    out["hint_fallback"] = pct(sum(h["result"].source == "static" for h in hint_results), len(hint_results))
    out["hint_ship_dir"] = pct(sum(direction_ok(h["result"].text, h["outcome"]) for h in ai_hints), len(ai_hints))
    out["hint_ship_leak"] = pct(sum(leaks_secret(h["result"].text, h["secret"]) for h in ai_hints), len(ai_hints))
    static = [h for h in hint_results if h["result"].source == "static"]
    out["hint_static_dir"] = pct(sum(direction_ok(h["result"].text.replace("LOWER", "lower").replace("HIGHER", "higher"), h["outcome"]) for h in static), len(static))

    # --- win message
    wins = [g["win"] for g in games if g["win"]]
    out["win_ai"] = pct(sum(w.source == "ai" for w in wins), len(wins))
    out["win_retry"] = pct(sum(w.attempts > 1 for w in wins), len(wins))
    got = [r for r in wins_raw if r["reply"] is not None]
    out["win_raw_valid"] = pct(
        sum(has_number(r["reply"], r["secret"]) and has_number(r["reply"], r["score"]) for r in got), len(got)
    )

    # --- API health
    timed = [r["latency"] for r in records]
    out["api_calls"] = len(records)
    out["api_fail"] = pct(sum(r["reply"] is None for r in records), len(records))
    out["latency_mean"] = f"{statistics.mean(timed):.2f}s" if timed else "n/a"
    out["latency_p95"] = f"{sorted(timed)[int(0.95 * (len(timed) - 1))]:.2f}s" if timed else "n/a"
    codes = collections.Counter(
        (re.search(r"\b(\d{3}) ([A-Z_]+)", m).group(0) if re.search(r"\b(\d{3}) ([A-Z_]+)", m) else "other")
        for m in errors
    )
    out["api_error_types"] = ", ".join(f"{k}: {v}" for k, v in codes.most_common()) or "none"

    # --- gameplay
    won = [g for g in games if g["won"]]
    out["win_rate"] = pct(len(won), len(games))
    out["avg_guesses"] = f"{statistics.mean(g['guesses'] for g in won):.2f}" if won else "n/a"

    # --- style of the shipped AI hints
    texts = [h["result"].text for h in ai_hints]
    out["style_words"] = f"{statistics.mean(len(t.split()) for t in texts):.1f}" if texts else "n/a"
    out["style_long"] = pct(sum(sentence_count(t) > 2 for t in texts), len(texts))
    openings = collections.Counter(" ".join(t.lower().split()[:2]) for t in texts)
    out["style_openings"] = (
        f"{len(openings)} distinct openings in {len(texts)} hints; most common: "
        + ", ".join(f"'{k}' x{v}" for k, v in openings.most_common(2))
    ) if texts else "n/a"
    out["style_achievement"] = pct(sum("achievement unlocked" in t.lower() for t in texts), len(texts))
    return out


def per_difficulty(games):
    rows = []
    for d in DIFFICULTIES:
        gs = [g for g in games if g["difficulty"] == d]
        if not gs:
            continue
        won = [g for g in gs if g["won"]]
        hs = [h for g in gs for h in g["hints"]]
        rows.append((
            d, len(gs), pct(len(won), len(gs)),
            f"{statistics.mean(g['guesses'] for g in won):.2f}" if won else "n/a",
            pct(sum(h["result"].attempts > 1 for h in hs), len(hs)),
            pct(sum(h["result"].source == "static" for h in hs), len(hs)),
        ))
    return rows


def render(m, games, rows, rejected, args, started):
    mode = "MOCK (fake Gemini, offline)" if args.mock else f"live ({ai_master.MODEL_NAME})"
    L = []
    L.append(f"### AI Game Master evaluation ({started:%Y-%m-%d}, {mode}, {len(games)} games)\n")
    L.append("| Metric | Result |")
    L.append("|---|---|")
    add = lambda k, v: L.append(f"| {k} | {v} |")
    add("**Secret picking**", "")
    add("AI picks valid (JSON, integer, inside the band)", m["pick_raw_valid"])
    add("Games whose secret came from the AI (not the `randint` fallback)", m["pick_ai_games"])
    add("Variety", m["pick_distinct"])
    add("**Hints, raw Gemini replies (before the guardrail)**", f"{m['hint_raw_total']} replies")
    add("Correct direction word (exactly one, right one)", m["hint_raw_dir"])
    add("Leaked the secret number", m["hint_raw_leak"])
    add("Correct direction AND no leak", m["hint_raw_clean"])
    add("**Hints, shown to the player (after guardrail, retry, fallback)**", f"{m['hint_count']} hints")
    add("Needed a retry", m["hint_retry"])
    add("Fell back to the static hint", m["hint_fallback"])
    add("AI hints shown with the correct direction", m["hint_ship_dir"])
    add("AI hints shown that leaked the secret", m["hint_ship_leak"])
    add("Static fallback hints with the correct direction", m["hint_static_dir"])
    add("**Win message**", "")
    add("Raw replies containing both the secret and the score", m["win_raw_valid"])
    add("Shown message was AI-written", m["win_ai"])
    add("Needed a retry", m["win_retry"])
    add("**Gameplay (binary-search guesser)**", "")
    add("Games won", m["win_rate"])
    add("Average guesses to win", m["avg_guesses"])
    add("**API health**", f"{m['api_calls']} calls")
    add("Calls with no usable reply", m["api_fail"])
    add("Error types", m["api_error_types"])
    add("Latency mean / p95", f"{m['latency_mean']} / {m['latency_p95']}")
    add("**Style of AI hints shown**", "")
    add("Average words per hint", m["style_words"])
    add("Hints longer than two sentences", m["style_long"])
    add("Openings", m["style_openings"])
    add('Hints containing "Achievement unlocked"', m["style_achievement"])
    L.append("\n| Difficulty | Games | Won | Avg guesses to win | Hints needing a retry | Hints using static fallback |")
    L.append("|---|---|---|---|---|---|")
    for r in rows:
        L.append("| " + " | ".join(str(c) for c in r) + " |")
    if rejected:
        L.append("\nRejected raw replies (examples):\n")
        for kind, text, why in rejected[:6]:
            L.append(f"- {kind}: {text!r} -> {why}")
    return "\n".join(L)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--games", type=int, default=20)
    parser.add_argument("--delay", type=float, default=4.0,
                        help="seconds to wait after each API call (the free tier rate-limits "
                             "fast callers with 429 errors, so 4-5s is safe)")
    parser.add_argument("--seed", type=int, default=None, help="seed for --mock")
    parser.add_argument("--mock", action="store_true", help="offline run with a fake, flawed Gemini")
    parser.add_argument("--verbose", action="store_true", help="print every hint")
    parser.add_argument("--out", help="also save the results table to this file")
    args = parser.parse_args()

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    errors = ErrorLog()
    logging.getLogger("ai_master").addHandler(errors)

    if args.mock:
        rng = random.Random(args.seed)
        random.seed(args.seed)
        real_ask = make_mock_ask(rng)
        ai_master.is_available = lambda: True
        delay = 0
    else:
        if not ai_master.is_available():
            sys.exit("No GEMINI_API_KEY found. Put it in .env (see README), or use --mock for a dry run.")
        real_ask = ai_master.ask
        delay = args.delay

    records, ctx = [], {}

    def recording_ask(prompt, system=ai_master.GAME_MASTER_PROMPT, json_output=False):
        start = time.perf_counter()
        reply = real_ask(prompt, system=system, json_output=json_output)
        records.append(dict(ctx, prompt=prompt, reply=reply, latency=time.perf_counter() - start))
        if delay:
            time.sleep(delay)
        return reply

    ai_master.ask = recording_ask

    started = datetime.datetime.now()
    games = []
    try:
        for i in range(args.games):
            games.append(play_game(i + 1, DIFFICULTIES[i % 3], ctx, args.verbose))
            if not args.verbose:
                print(f"\rgame {i + 1}/{args.games}", end="", flush=True)
    except KeyboardInterrupt:
        print("\nInterrupted, reporting the games finished so far.")
    print()
    if not games:
        sys.exit("No games finished.")

    # examples of raw replies the guardrail had to reject
    rejected = []
    for r in records:
        if r["reply"] is None:
            continue
        if r["kind"] == "hint":
            if leaks_secret(r["reply"], r["secret"]):
                rejected.append(("hint", r["reply"], "leaked the secret"))
            elif not direction_ok(r["reply"], r["outcome"]):
                rejected.append(("hint", r["reply"], "wrong or ambiguous direction"))
        elif r["kind"] == "win" and not (has_number(r["reply"], r["secret"]) and has_number(r["reply"], r["score"])):
            rejected.append(("win message", r["reply"], "missing the secret or the score"))

    table = render(compute(games, records, errors.messages), games, per_difficulty(games), rejected, args, started)
    print(table)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(table + "\n")
        print(f"\nSaved to {args.out}")


if __name__ == "__main__":
    main()

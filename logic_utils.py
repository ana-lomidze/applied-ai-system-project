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
        if "." in raw:
            value = int(float(raw))
        else:
            value = int(raw)
    except Exception:
        return False, None, "That is not a number."

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
    """Update score based on outcome and attempt number."""
    if outcome in ("Too High", "Too Low"):
        return max(current_score - 5, 0)

    return current_score

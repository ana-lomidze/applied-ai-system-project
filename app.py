import streamlit as st
import ai_master
# FIX: Refactored the game logic into logic_utils.py using agent mode. Claude showed each function's change first, I approved it, then Claude moved it one at a time and removed the local copy from app.py.
from logic_utils import (
    get_range_for_difficulty,
    parse_guess,
    check_guess,
    update_score,
    pick_secret,
    get_ai_hint,
)

st.set_page_config(page_title="Glitchy Guesser", page_icon="🎮")

st.title("🎮 Game Glitch Investigator")
st.caption("An AI-generated guessing game. Something is off.")

st.sidebar.header("Settings")

difficulty = st.sidebar.selectbox(
    "Difficulty",
    ["Easy", "Normal", "Hard"],
    index=1,
)

attempt_limit_map = {
    "Easy": 6,
    "Normal": 8,
    "Hard": 5,
}
attempt_limit = attempt_limit_map[difficulty]

low, high = get_range_for_difficulty(difficulty)

st.sidebar.caption(f"Range: {low} to {high}")
st.sidebar.caption(f"Attempts allowed: {attempt_limit}")

# AI Game Master: when ON, Gemini picks the secret (New Game) and words the hints.
# When OFF or no API key, the game is fully non-AI (random.randint + static hints).
ai_available = ai_master.is_available()
use_ai = st.sidebar.toggle(
    "AI Game Master",
    value=ai_available,
    disabled=not ai_available,
    help="Gemini picks the secret number and writes the hints.",
)
if not ai_available:
    st.sidebar.caption("No GEMINI_API_KEY found, so the AI is off.")


def new_secret():
    """Pick a secret for the current difficulty. Returns (secret, source)."""
    with st.spinner("The Game Master is picking a number..." if use_ai else "Picking a number..."):
        return pick_secret(low, high, use_ai)


if "secret" not in st.session_state:
    st.session_state.secret, st.session_state.secret_source = new_secret()

if "attempts" not in st.session_state:
    # FIX: Initial attempts changed from 1 to 0 to match New Game's reset, after Claude flagged the mismatch and we agreed on it together.
    st.session_state.attempts = 0

if "score" not in st.session_state:
    st.session_state.score = 100

if "status" not in st.session_state:
    st.session_state.status = "playing"

if "history" not in st.session_state:
    st.session_state.history = []


def reset_game():
    """Start a fresh round: clear the stats and pick a new secret for the current difficulty."""
    st.session_state.attempts = 0
    st.session_state.score = 100
    st.session_state.history = []
    st.session_state.status = "playing"
    st.session_state.secret, st.session_state.secret_source = new_secret()
    st.session_state.last_hint = None


# FIX (bug #8): changing the difficulty now starts a new game. Before, the old secret (e.g. 90)
# stayed in play after switching to Easy (1-20), so it could be outside the new range.
if "difficulty" not in st.session_state:
    st.session_state.difficulty = difficulty
elif st.session_state.difficulty != difficulty:
    st.session_state.difficulty = difficulty
    reset_game()
    st.session_state.show_difficulty_msg = True

st.subheader("Make a guess")

# FIX: The banner and debug panel used to be drawn before the guess was processed, so they lagged one guess behind (e.g. a win on attempt 2 still showed attempts 1). Their spots are now reserved here and filled in after the guess is processed. I identified the bug, Claude proposed the fix, I approved it, then Claude applied it.
info_area = st.container()   # keeps the banner in its spot on the page
debug_area = st.container()  # keeps the debug panel in its spot on the page


# How internal source values are shown in the debug panel.
SECRET_SOURCE_LABELS = {"ai": "AI", "random": "randint"}
HINT_SOURCE_LABELS = {"ai": "AI", "static": "static"}


def show_status():
    with info_area:
        st.info(
            f"Guess a number {low} and {high}. "
            f"Attempts left: {attempt_limit - st.session_state.attempts}"
        )
    with debug_area:
        with st.expander("Developer Debug Info"):
            st.write("Secret:", st.session_state.secret)
            secret_source = st.session_state.get("secret_source")
            st.write("Secret picked by:", SECRET_SOURCE_LABELS.get(secret_source, secret_source))
            last_hint = st.session_state.get("last_hint")
            if last_hint is not None:
                st.write("Last hint source:", HINT_SOURCE_LABELS.get(last_hint.source, last_hint.source))
                st.write("Hint attempts:", last_hint.attempts)
                st.write("Hint rejections:", last_hint.failures)
            st.write("Attempts:", st.session_state.attempts)
            st.write("Score:", st.session_state.score)
            st.write("Difficulty:", difficulty)
            st.write("History:", st.session_state.history)


raw_guess = st.text_input(
    "Enter your guess:",
    key=f"guess_input_{difficulty}"
)

col1, col2 = st.columns(2)
with col1:
    submit = st.button("Submit Guess 🚀")
with col2:
    new_game = st.button("New Game 🔁")

# FIX: New Game now resets attempts, score, history and status, and picks the secret from the selected difficulty's range. Claude proposed it, I reviewed and approved it, then Claude applied it.
if new_game:
    reset_game()
    st.session_state.show_new_game_msg = True
    st.rerun()

# FIX: "New game started." is shown via a flag after the rerun, since st.rerun() would erase it. I asked to keep the message and Claude suggested this approach.
if st.session_state.pop("show_new_game_msg", False):
    st.success("New game started.")

if st.session_state.pop("show_difficulty_msg", False):
    st.info(f"Difficulty changed to {difficulty}, so a new game started.")

if st.session_state.status != "playing":
    if st.session_state.status == "won":
        st.success("You already won. Start a new game to play again.")
    else:
        st.error("Game over. Start a new game to try again.")
    show_status()
    st.stop()

if submit:
    st.session_state.attempts += 1

    ok, guess_int, err = parse_guess(raw_guess)

    if not ok:
        st.session_state.history.append(raw_guess)
        st.error(err)
    else:
        st.session_state.history.append(guess_int)

        # FIX: Removed the even-attempt str(secret) conversion that made hints compare alphabetically. Claude applied it so the secret is always an int.
        outcome, message = check_guess(guess_int, st.session_state.secret)

        # Hints are a core part of the game, so one is always shown.
        st.session_state.last_hint = None
        if use_ai:
            # The API is only called here, inside `if submit`, so a Streamlit
            # rerun (e.g. toggling a widget) never repeats the call for a guess.
            with st.spinner("The Game Master is thinking..."):
                result = get_ai_hint(
                    guess_int,
                    st.session_state.secret,
                    st.session_state.history[:-1],  # earlier guesses only
                    difficulty,
                )
            st.session_state.last_hint = result
            st.warning(result.text)
        else:
            st.warning(message)

        st.session_state.score = update_score(
            current_score=st.session_state.score,
            outcome=outcome,
            attempt_number=st.session_state.attempts,
        )

        if outcome == "Win":
            st.balloons()
            st.session_state.status = "won"
            st.success(
                f"You won! The secret was {st.session_state.secret}. "
                f"Final score: {st.session_state.score}"
            )
        else:
            if st.session_state.attempts >= attempt_limit:
                st.session_state.status = "lost"
                st.error(
                    f"Out of attempts! "
                    f"The secret was {st.session_state.secret}. "
                    f"Score: {st.session_state.score}"
                )

show_status()

st.divider()
st.caption("Built by an AI that claims this code is production-ready.")

import random
import streamlit as st
# FIX: Refactored the game logic into logic_utils.py using agent mode. Claude showed each function's change first, I approved it, then Claude moved it one at a time and removed the local copy from app.py.
from logic_utils import get_range_for_difficulty, parse_guess, check_guess, update_score

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

if "secret" not in st.session_state:
    st.session_state.secret = random.randint(low, high)

if "attempts" not in st.session_state:
    # FIX: Initial attempts changed from 1 to 0 to match New Game's reset, after Claude flagged the mismatch and we agreed on it together.
    st.session_state.attempts = 0

if "score" not in st.session_state:
    st.session_state.score = 100

if "status" not in st.session_state:
    st.session_state.status = "playing"

if "history" not in st.session_state:
    st.session_state.history = []

st.subheader("Make a guess")

# FIX: The banner and debug panel used to be drawn before the guess was processed, so they lagged one guess behind (e.g. a win on attempt 2 still showed attempts 1). Their spots are now reserved here and filled in after the guess is processed. I identified the bug, Claude proposed the fix, I approved it, then Claude applied it.
info_area = st.container()   # keeps the banner in its spot on the page
debug_area = st.container()  # keeps the debug panel in its spot on the page


def show_status():
    with info_area:
        st.info(
            f"Guess a number {low} and {high}. "
            f"Attempts left: {attempt_limit - st.session_state.attempts}"
        )
    with debug_area:
        with st.expander("Developer Debug Info"):
            st.write("Secret:", st.session_state.secret)
            st.write("Attempts:", st.session_state.attempts)
            st.write("Score:", st.session_state.score)
            st.write("Difficulty:", difficulty)
            st.write("History:", st.session_state.history)


raw_guess = st.text_input(
    "Enter your guess:",
    key=f"guess_input_{difficulty}"
)

col1, col2, col3 = st.columns(3)
with col1:
    submit = st.button("Submit Guess 🚀")
with col2:
    new_game = st.button("New Game 🔁")
with col3:
    show_hint = st.checkbox("Show hint", value=True)

# FIX: New Game now resets attempts, score, history and status, and picks the secret from the selected difficulty's range. Claude proposed it, I reviewed and approved it, then Claude applied it.
if new_game:
    st.session_state.attempts = 0
    st.session_state.score = 100
    st.session_state.history = []
    st.session_state.status = "playing"
    st.session_state.secret = random.randint(low, high)
    st.session_state.show_new_game_msg = True
    st.rerun()

# FIX: "New game started." is shown via a flag after the rerun, since st.rerun() would erase it. I asked to keep the message and Claude suggested this approach.
if st.session_state.pop("show_new_game_msg", False):
    st.success("New game started.")

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

        if show_hint:
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

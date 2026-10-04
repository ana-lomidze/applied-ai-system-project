from logic_utils import check_guess, update_score
from streamlit.testing.v1 import AppTest

def test_winning_guess():
    # If the secret is 50 and guess is 50, it should be a win
    result, _ = check_guess(50, 50)
    assert result == "Win"

def test_guess_too_high():
    # If secret is 50 and guess is 60, hint should be "Too High"
    result, _ = check_guess(60, 50)
    assert result == "Too High"

def test_guess_too_low():
    # If secret is 50 and guess is 40, hint should be "Too Low"
    result, _ = check_guess(40, 50)
    assert result == "Too Low"


# Tests below target the New Game bug fix. Claude drafted them, I reviewed them, and Claude added them and ran them with pytest.
SUBMIT, NEW_GAME = 0, 1  # button order in app.py


def _lose_a_game():
    at = AppTest.from_file("app.py").run()
    at.session_state["secret"] = 50
    for _ in range(8):  # Normal difficulty allows 8 attempts
        at.text_input[0].set_value("1").run()
        at.button[SUBMIT].click().run()
    assert at.session_state["status"] == "lost"
    return at


def test_new_game_resets_state_after_game_over():
    at = _lose_a_game()
    assert at.session_state["history"] != []
    assert at.session_state["score"] != 100

    at.button[NEW_GAME].click().run()

    assert not at.exception
    assert at.session_state["attempts"] == 0
    assert at.session_state["score"] == 100
    assert at.session_state["history"] == []
    assert at.session_state["status"] == "playing"
    assert not at.error  # no "Game over. Start a new game..." message
    assert any("New game started." in s.value for s in at.success)


def test_can_guess_after_new_game():
    at = _lose_a_game()
    at.button[NEW_GAME].click().run()

    at.text_input[0].set_value("1").run()
    at.button[SUBMIT].click().run()

    assert not at.exception
    assert at.session_state["attempts"] == 1
    assert at.session_state["history"] == [1]


def test_new_game_secret_respects_difficulty():
    at = AppTest.from_file("app.py").run()
    at.sidebar.selectbox[0].select("Easy").run()
    for _ in range(30):
        at.button[NEW_GAME].click().run()
        assert 1 <= at.session_state["secret"] <= 20


def test_win_keeps_score():
    assert update_score(100, "Win", 1) == 100
    assert update_score(95, "Win", 2) == 95


def test_wrong_guess_costs_5_points():
    assert update_score(100, "Too High", 1) == 95
    assert update_score(95, "Too High", 2) == 90
    assert update_score(100, "Too Low", 1) == 95


def test_score_never_below_zero():
    assert update_score(3, "Too Low", 1) == 0

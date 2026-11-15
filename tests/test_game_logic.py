import pytest
from logic_utils import check_guess, parse_guess, update_score
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


def test_status_shows_current_guess_not_previous():
    at = AppTest.from_file("app.py").run()
    at.session_state["secret"] = 50

    # one wrong guess: the banner and debug panel should already reflect it
    at.text_input[0].set_value("1").run()
    at.button[SUBMIT].click().run()
    debug = [m.value for m in at.expander[0].markdown]
    assert "Attempts left: 7" in at.info[0].value
    assert "Attempts: `1`" in debug
    assert "Score: `95`" in debug

    # winning on the second guess: still the current state, not one behind
    at.text_input[0].set_value("50").run()
    at.button[SUBMIT].click().run()
    debug = [m.value for m in at.expander[0].markdown]
    assert "Attempts left: 6" in at.info[0].value
    assert "Attempts: `2`" in debug


# Tests for Challenge 1: Advanced Edge-Case Testing
def test_parse_guess_empty_and_none():
    assert parse_guess("") == (False, None, "Enter a guess.")
    assert parse_guess(None) == (False, None, "Enter a guess.")


def test_parse_guess_rejects_non_numbers():
    assert parse_guess("abc") == (False, None, "That is not a number.")
    assert parse_guess("12abc") == (False, None, "That is not a number.")
    assert parse_guess(" ") == (False, None, "That is not a number.")


def test_parse_guess_valid_ints_and_whitespace():
    assert parse_guess("42") == (True, 42, None)
    assert parse_guess(" 7 ") == (True, 7, None)


def test_parse_guess_rejects_decimals():
    assert parse_guess("5.9") == (False, None, "Guesses must be whole numbers.")
    assert parse_guess("-0.5") == (False, None, "Guesses must be whole numbers.")
    assert parse_guess("0.1") == (False, None, "Guesses must be whole numbers.")


def test_parse_guess_accepts_whole_number_decimals():
    assert parse_guess("5.0") == (True, 5, None)
    assert parse_guess("-3.0") == (True, -3, None)


def test_parse_guess_rejects_non_finite_and_odd_input():
    for raw in ["inf", "nan", "-inf", "1e999", "5.9.1", "."]:
        assert parse_guess(raw) == (False, None, "That is not a number."), raw


def test_check_guess_boundaries_and_messages():
    assert check_guess(51, 50) == ("Too High", "📉 Go LOWER!")
    assert check_guess(49, 50) == ("Too Low", "📈 Go HIGHER!")


def test_out_of_range_guess_is_rejected():
    at = AppTest.from_file("app.py").run()  # Normal difficulty: 1 to 100
    at.session_state["secret"] = 50
    at.text_input[0].set_value("500").run()
    at.button[SUBMIT].click().run()
    assert at.error  # an error message instead of a "Too High" hint
    assert "outside the range 1 to 100" in at.error[0].value
    assert not at.warning  # no hint is given


def test_out_of_range_guess_counts_as_an_attempt():
    at = AppTest.from_file("app.py").run()
    at.session_state["secret"] = 50
    at.text_input[0].set_value("500").run()
    at.button[SUBMIT].click().run()

    assert at.session_state["attempts"] == 1
    assert at.session_state["history"] == [500]
    assert at.session_state["score"] == 95  # costs 5 points, like a wrong guess
    assert at.session_state["status"] == "playing"
    assert "Attempts left: 7" in at.info[0].value


def test_out_of_range_boundaries():
    # 0 and 101 are out of range (Normal is 1 to 100); 1 and 100 are valid guesses
    for guess, in_range in [("0", False), ("101", False), ("-5", False), ("1", True), ("100", True)]:
        at = AppTest.from_file("app.py").run()
        at.session_state["secret"] = 50
        at.text_input[0].set_value(guess).run()
        at.button[SUBMIT].click().run()
        assert bool(at.warning) == in_range, guess  # valid guesses get a hint
        assert any("outside the range" in e.value for e in at.error) == (not in_range), guess


def test_out_of_range_guess_can_use_the_last_attempt():
    at = AppTest.from_file("app.py").run()
    at.session_state["secret"] = 50
    for _ in range(8):  # Normal allows 8 attempts, all out of range
        at.text_input[0].set_value("500").run()
        at.button[SUBMIT].click().run()
    assert at.session_state["status"] == "lost"
    assert any("Out of attempts" in e.value for e in at.error)


# Tests for changing the difficulty: it starts a new game.
def test_changing_difficulty_starts_new_game():
    at = AppTest.from_file("app.py").run()  # Normal: 1 to 100
    at.session_state["secret"] = 90  # outside the Easy range (1 to 20)
    at.text_input[0].set_value("1").run()
    at.button[SUBMIT].click().run()
    assert at.session_state["attempts"] == 1

    at.sidebar.selectbox[0].select("Easy").run()

    assert not at.exception
    assert 1 <= at.session_state["secret"] <= 20
    assert at.session_state["attempts"] == 0
    assert at.session_state["score"] == 100
    assert at.session_state["history"] == []
    assert at.session_state["status"] == "playing"
    assert any("Difficulty changed to Easy" in i.value for i in at.info)


def test_same_difficulty_keeps_the_game_going():
    at = AppTest.from_file("app.py").run()
    at.session_state["secret"] = 50
    at.text_input[0].set_value("1").run()
    at.button[SUBMIT].click().run()
    at.text_input[0].set_value("2").run()
    at.button[SUBMIT].click().run()  # reruns without changing difficulty

    assert at.session_state["secret"] == 50
    assert at.session_state["attempts"] == 2
    assert not any("Difficulty changed" in i.value for i in at.info)


def test_changing_difficulty_after_game_over_allows_play():
    at = _lose_a_game()
    at.sidebar.selectbox[0].select("Hard").run()

    assert at.session_state["status"] == "playing"
    assert 1 <= at.session_state["secret"] <= 50
    assert not at.error  # no "Game over" message


# Tests for non-integer guesses: an error, but it still counts as an attempt.
def test_non_integer_guesses_are_errors_that_cost_an_attempt():
    for raw, message in [("abc", "That is not a number."), ("5.9", "Guesses must be whole numbers.")]:
        at = AppTest.from_file("app.py").run()
        at.session_state["secret"] = 50
        at.text_input[0].set_value(raw).run()
        at.button[SUBMIT].click().run()

        assert not at.exception, raw
        assert message in at.error[0].value, raw
        assert "still counts" in at.error[0].value, raw
        assert not at.warning, raw  # no hint
        assert at.session_state["attempts"] == 1, raw
        assert at.session_state["score"] == 95, raw  # costs 5 points, like a wrong guess
        assert "Attempts left: 7" in at.info[0].value, raw


def test_empty_guess_is_an_error_that_costs_an_attempt():
    at = AppTest.from_file("app.py").run()
    at.session_state["secret"] = 50
    at.button[SUBMIT].click().run()  # nothing typed

    assert "Enter a guess." in at.error[0].value
    assert at.session_state["attempts"] == 1


def test_invalid_guess_can_use_the_last_attempt():
    at = AppTest.from_file("app.py").run()
    at.session_state["secret"] = 50
    for _ in range(8):  # Normal allows 8 attempts, all invalid
        at.text_input[0].set_value("abc").run()
        at.button[SUBMIT].click().run()

    assert at.session_state["status"] == "lost"
    assert any("Out of attempts" in e.value for e in at.error)


# Tests for scoring: invalid guesses cost points, and running out of attempts means 0.
def test_invalid_guess_costs_5_points():
    assert update_score(100, "Invalid", 1) == 95
    assert update_score(3, "Invalid", 1) == 0  # never below 0


def test_invalid_guesses_cost_points_in_the_app():
    at = AppTest.from_file("app.py").run()
    at.session_state["secret"] = 50
    for raw, expected in [("abc", 95), ("500", 90), ("5.5", 85), ("1", 80)]:  # last one is a wrong guess
        at.text_input[0].set_value(raw).run()
        at.button[SUBMIT].click().run()
        assert at.session_state["score"] == expected, raw


def test_running_out_of_attempts_sets_score_to_zero():
    at = _lose_a_game()  # 8 wrong guesses
    assert at.session_state["status"] == "lost"
    assert at.session_state["score"] == 0
    assert any("Score: 0" in e.value for e in at.error)


def test_losing_on_an_invalid_last_guess_sets_score_to_zero():
    for last_guess in ["0", "abc", "2.5"]:  # out of range, not a number, decimal
        at = AppTest.from_file("app.py").run()
        at.session_state["secret"] = 50
        for _ in range(7):
            at.text_input[0].set_value("1").run()
            at.button[SUBMIT].click().run()
        assert at.session_state["score"] == 65  # 7 wrong guesses
        at.text_input[0].set_value(last_guess).run()
        at.button[SUBMIT].click().run()
        assert at.session_state["status"] == "lost", last_guess
        assert at.session_state["score"] == 0, last_guess
        assert any("Score: 0" in e.value for e in at.error), last_guess


def test_winning_keeps_the_remaining_score():
    at = AppTest.from_file("app.py").run()
    at.session_state["secret"] = 50
    at.text_input[0].set_value("abc").run()
    at.button[SUBMIT].click().run()  # 95
    at.text_input[0].set_value("50").run()
    at.button[SUBMIT].click().run()  # win on attempt 2
    assert at.session_state["status"] == "won"
    assert at.session_state["score"] == 95


def test_winning_on_the_last_attempt_keeps_the_score():
    at = AppTest.from_file("app.py").run()
    at.session_state["secret"] = 50
    for _ in range(7):
        at.text_input[0].set_value("1").run()
        at.button[SUBMIT].click().run()
    at.text_input[0].set_value("50").run()
    at.button[SUBMIT].click().run()  # win on attempt 8 of 8
    assert at.session_state["status"] == "won"
    assert at.session_state["score"] == 65


# Tests for hints on the last attempt: no hint (and no AI call) once the game is over.
def test_no_hint_when_a_wrong_guess_uses_the_last_attempt():
    at = AppTest.from_file("app.py").run()
    at.session_state["secret"] = 50
    for i in range(8):  # Normal allows 8 attempts
        at.text_input[0].set_value("1").run()
        at.button[SUBMIT].click().run()
        if i < 7:
            assert at.warning, f"attempt {i + 1} should still get a hint"
    assert at.session_state["status"] == "lost"
    assert not at.warning  # no hint on the final, losing guess
    assert any("Out of attempts" in e.value for e in at.error)


def test_ai_hint_is_not_requested_on_the_last_attempt(monkeypatch):
    import ai_master

    calls = []

    def fake_ask(prompt, **kwargs):
        calls.append(prompt)
        return "Higher. Try harder."

    monkeypatch.setattr(ai_master, "is_available", lambda: True)
    monkeypatch.setattr(ai_master, "ask", fake_ask)
    at = AppTest.from_file("app.py").run()
    at.session_state["secret"] = 50
    for _ in range(8):
        at.text_input[0].set_value("1").run()
        at.button[SUBMIT].click().run()

    hint_calls = [c for c in calls if "latest guess" in c]
    assert len(hint_calls) == 7  # attempts 1-7 only, none for the 8th
    assert at.session_state["status"] == "lost"


def test_winning_on_the_last_attempt_still_shows_the_correct_message():
    at = AppTest.from_file("app.py").run()
    at.session_state["secret"] = 50
    for _ in range(7):
        at.text_input[0].set_value("1").run()
        at.button[SUBMIT].click().run()
    at.text_input[0].set_value("50").run()
    at.button[SUBMIT].click().run()
    assert at.session_state["status"] == "won"
    assert at.warning  # the win still gets its message box

# 🎮 Game Glitch Investigator: The Impossible Guesser

## 🚨 The Situation

You asked an AI to build a simple "Number Guessing Game" using Streamlit.
It wrote the code, ran away, and now the game is unplayable. 

- You can't win.
- The hints lie to you.
- The secret number seems to have commitment issues.

## 🛠️ Setup

1. Install dependencies: `pip install -r requirements.txt`
2. Run the broken app: `python -m streamlit run app.py`

## 🕵️‍♂️ Your Mission

1. **Play the game.** Open the "Developer Debug Info" tab in the app to see the secret number. Try to win.
2. **Find the State Bug.** Why does the secret number change every time you click "Submit"? Ask ChatGPT: *"How do I keep a variable from resetting in Streamlit when I click a button?"*
3. **Fix the Logic.** The hints ("Higher/Lower") are wrong. Fix them.
4. **Refactor & Test.** - Move the logic into `logic_utils.py`.
   - Run `pytest` in your terminal.
   - Keep fixing until all tests pass!

## 📝 Document Your Experience

- [✅] Describe the game's purpose.
User is supposed to guess the Secret Number in a certain amount of attempts. Attempts are determined by the difficulty setting of the game.

If the user guesses too high, the game gives the hint "Go LOWER!"
If the user guesses too low, the game gives the hint "Go HIGHER!"
If the user guesses correctly, the game says "Correct!" and "You've won!..."

The game keeps track of the score as well. -5 points every wrong guess.

- [✅] Detail which bugs you found.
1. Unable to start a new game when clicking 'New Game' button. The Secret number is set to a different number and Attempts is set to 0, but the History and Score in the Developer Debug Info section stays the same.
2. Scoring is weird. When guessing the number correctly on first try, player don't get 100 (score of 70 on first try guess). The Score shown in Developer Debug Info and the Score shown to the player doesn't match up. Ex: Guessed on the 3rd attempt; score on the Dev section says -10, player gets the message of Final score: 40. (If we assume that 70 is the highest player can get, 70 - 10 = 60 not 40).
After looking at the code, the score is calculated so weird!
3. Hints are given incorrectly. They say the opposite of what the player needs.
4. Each mention of "Attempts" shows something different. Ex: upon first running the game (Normal Difficulty by default), in Settings it shows 8 Attempts, on the instructions of the game right under "Make a guess" it says "Guess a number between 1 and 100. Attempts left:  7", and on the Developer Debug Info tab it said the player has 1 Attempt (no guessing has been done yet).
5. When a user guesses a number outside of 1-100 there is no error message for that. The game reads it as a regular guess.
6. Difficulty isn't working as intended. The code shows that the secret number should be in between different ranges, but the game doesn't account for this (Ex: Difficulty: Hard (Max should be 50); Secret: 54). The Settings bar on the side shows the expected range, but the info banner under "Make a guess" doesn't show the new range, even though the number of allowed attempts on the banner gets updated upon difficulty change.
7. The Developer Debug Info tab is lagged behind. So if player wins on second try, the stats shown in the dev tab are one guess behind.
8. Changing the difficulty doesn't automatically start a new game. Ex: once launching the game the difficulty is normal, secret number is 90. I change the difficulty to easy, the secret number is still 90.

- [✅] Explain what fixes you applied.
1. Fixed the "New Game" button bug. Clicking the button now starts a new round successfully and clears the stats shown in the Developer Debug Info tab
2. Fixed the hints being opposite. Now the hints guides the user correctly.
3. Fixed the score being calculated weridly. Now the score subtracts 5 after every wrong attempt.
4. Fixed the Developer Debug Info tab being one round behind. Now the information displayed there shows upon gues submission.

## 📸 Demo Walkthrough

Describe your fixed game in numbered steps so a reader can follow along without watching a video:

1. After launching the game, the user guesses 50.
2. The game gives a hint "Go HIGHER"
3. The user guesses 75, and the game shows balloons and says "Correct!" The user sees on the bottom banner that the have gotten a score of 95.
4. They expand the Developer Debug Info section and see that the following:
Secret: 75
Attempts: 2
Score: 95
Difficulty: Normal
History: [50, 75]
5. The user plays another round with the Developer Debug Info section Expanded. They click the "New Game" button.
6. The Developer Debug Info shows that a new Secret number is picked, attempts is reset to 0, score is set to 100, and history is cleared. The new secret number is 33.
7. The user guesses 20. The game gives the hint "Go HIGHER!"
8. The Developer Debug Info tab updates accordingly.
9. The use guesses 50. The game gives the hint "Go LOWER!"
10. The Developer Debug Info tab updates accordingly.
11. The user guesses 33. The game celebrates, "Correct!"

**Screenshot** *(optional)*: <!-- Insert a screenshot of your fixed, winning game here -->

## 🧪 Test Results

### Testing results for test_game_logic.py and test_ai_hints.py
Running `python -m pytest` never calls the real Gemini API. `tests/conftest.py` switches the AI off by default, and the AI tests use a mocked client. It also raises Streamlit's app-test timeout to 15 seconds.
```
# python -m pytest:
collected 138 items

tests\test_ai_hints.py ..................................................................... [ 50%]
.................................                                                            [ 73%]
tests\test_game_logic.py ....................................                                [100%]

====================================== 138 passed in 14.88s =======================================
```

### Testing for eval_hints.py
**Offline dry run with a fake Gemini**
```
# python tests/eval_hints.py --mock:
game 20/20
### AI Game Master evaluation (2026-11-15, MOCK (fake Gemini, offline), 20 games)

| Metric | Result |
|---|---|
| **Secret picking** |  |
| AI picks valid (JSON, integer, inside the band) | 100.0% (20/20) |
| Games whose secret came from the AI (not the `randint` fallback) | 100.0% (20/20) |
| Variety | 18 distinct secrets in 20 games |
| **Hints, raw Gemini replies (before the guardrail)** | 76 replies |
| Correct direction word (exactly one, right one) | 89.9% (62/69) |
| Leaked the secret number | 5.8% (4/69) |
| Correct direction AND no leak | 84.1% (58/69) |
| **Hints, shown to the player (after guardrail, retry, fallback)** | 61 hints |
| Needed a retry | 24.6% (15/61) |
| Fell back to the static hint | 4.9% (3/61) |
| AI hints shown with the correct direction | 100.0% (58/58) |
| AI hints shown that leaked the secret | 0.0% (0/58) |
| Static fallback hints with the correct direction | 100.0% (3/3) |
| **Win message** |  |
| Raw replies containing both the secret and the score | 90.0% (18/20) |
| Shown message was AI-written | 100.0% (18/18) |
| Needed a retry | 11.1% (2/18) |
| **Gameplay (binary-search guesser)** |  |
| Games won | 90.0% (18/20) |
| Average guesses to win | 3.94 |
| **API health** | 117 calls |
| Calls with no usable reply | 6.8% (8/117) |
| Error types | none |
| Latency mean / p95 | 0.00s / 0.00s |
| **Style of AI hints shown** |  |
| Average words per hint | 5.0 |
| Hints longer than two sentences | 0.0% (0/58) |
| Openings | 2 distinct openings in 58 hints; most common: 'higher. achievement' x33, 'lower. achievement' x25 |
| Hints containing "Achievement unlocked" | 100.0% (58/58) |

| Difficulty | Games | Won | Avg guesses to win | Hints needing a retry | Hints using static fallback |
|---|---|---|---|---|---|
| Easy | 7 | 100.0% (7/7) | 3.00 | 21.4% (3/14) | 0.0% (0/14) |
| Normal | 7 | 100.0% (7/7) | 4.57 | 16.0% (4/25) | 4.0% (1/25) |
| Hard | 6 | 66.7% (4/6) | 4.50 | 36.4% (8/22) | 9.1% (2/22) |

Rejected raw replies (examples):

- hint: 'Go lower, obviously.' -> wrong or ambiguous direction
- hint: 'Go lower, obviously.' -> wrong or ambiguous direction
- hint: 'Is it 16? Maybe go lower.' -> leaked the secret
- hint: 'Go lower, obviously.' -> wrong or ambiguous direction
- hint: 'Go higher, obviously.' -> wrong or ambiguous direction
- hint: 'Is it 3? Maybe go lower.' -> leaked the secret
```

**Real run against Gemini**
```
# python tests/eval_hints.py --games 10 --delay 5:
game 10/10
### AI Game Master evaluation (2026-11-15, live (gemini-3.1-flash-lite), 10 games)

| Metric | Result |
|---|---|
| **Secret picking** |  |
| AI picks valid (JSON, integer, inside the band) | 100.0% (10/10) |
| Games whose secret came from the AI (not the `randint` fallback) | 100.0% (10/10) |
| Variety | 8 distinct secrets in 10 games |
| **Hints, raw Gemini replies (before the guardrail)** | 38 replies |
| Correct direction word (exactly one, right one) | 100.0% (36/36) |
| Leaked the secret number | 0.0% (0/36) |
| Correct direction AND no leak | 100.0% (36/36) |
| **Hints, shown to the player (after guardrail, retry, fallback)** | 36 hints |
| Needed a retry | 5.6% (2/36) |
| Fell back to the static hint | 0.0% (0/36) |
| AI hints shown with the correct direction | 100.0% (36/36) |
| AI hints shown that leaked the secret | 0.0% (0/36) |
| Static fallback hints with the correct direction | n/a |
| **Win message** |  |
| Raw replies containing both the secret and the score | 100.0% (7/7) |
| Shown message was AI-written | 100.0% (7/7) |
| Needed a retry | 0.0% (0/7) |
| **Gameplay (binary-search guesser)** |  |
| Games won | 70.0% (7/10) |
| Average guesses to win | 4.43 |
| **API health** | 57 calls |
| Calls with no usable reply | 7.0% (4/57) |
| Error types | 503 UNAVAILABLE: 3, other: 1 |
| Latency mean / p95 | 2.10s / 5.14s |
| **Style of AI hints shown** |  |
| Average words per hint | 14.6 |
| Hints longer than two sentences | 0.0% (0/36) |
| Openings | 18 distinct openings in 36 hints; most common: 'lower. you' x5, 'lower. your' x5 |
| Hints containing "Achievement unlocked" | 0.0% (0/36) |

| Difficulty | Games | Won | Avg guesses to win | Hints needing a retry | Hints using static fallback |
|---|---|---|---|---|---|
| Easy | 4 | 100.0% (4/4) | 4.00 | 16.7% (2/12) | 0.0% (0/12) |
| Normal | 3 | 100.0% (3/3) | 5.00 | 0.0% (0/12) | 0.0% (0/12) |
| Hard | 3 | 0.0% (0/3) | n/a | 0.0% (0/12) | 0.0% (0/12) |

```

## 🚀 Stretch Features

- [ ] [If you choose to complete Challenge 4, describe the Enhanced UI changes here — a screenshot is optional]

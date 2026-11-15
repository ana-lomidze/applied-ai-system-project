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

```
# Paste your pytest output here, e.g.:
# pytest tests/
collected 138 items

tests\test_ai_hints.py ..................................................................... [ 50%]
.................................                                                            [ 73%]
tests\test_game_logic.py ....................................                                [100%]

====================================== 138 passed in 14.88s =======================================
```

## 🚀 Stretch Features

- [ ] [If you choose to complete Challenge 4, describe the Enhanced UI changes here — a screenshot is optional]

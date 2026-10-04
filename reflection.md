# 💭 Reflection: Game Glitch Investigator

Answer each question in 3 to 5 sentences. Be specific and honest about what actually happened while you worked. This is about your process, not trying to sound perfect.

## 1. What was broken when you started?

- What did the game look like the first time you ran it?

Answer: It felt very buggy. I tried playing multiple rounds and it was very frustrating becasue it was so buggy that I felt like I couldn't so anything. It was like where do I even start.

- List at least two concrete bugs you noticed at the start  
  (for example: "the hints were backwards").
1. Unable to start a new game when clicking 'New Game' button. The Secret number is set to a different number and Attempts is set to 0, but the History and Score in the Developer Debug Info section stays the same.
2. Scoring is weird. When guessing the number correctly on first try, player don't get 100 (score of 70 on first try guess). The Score shown in Developer Debug Info and the Score shown to the player doesn't match up. Ex: Guessed on the 3rd attempt; score on the Dev section says -10, player gets the message of Final score: 40. (If we assume that 70 is the highest player can get, 70 - 10 = 60 not 40).
After looking at the code, the score is calculated so weird!
3. Hints are given incorrectly. They say the opposite of what the player needs.
4. Each mention of "Attempts" shows something different. Ex: upon first running the game (Normal Difficulty by default), in Settings it shows 8 Attempts, on the instructions of the game right under "Make a guess" it says "Guess a number between 1 and 100. Attempts left:  7", and on the Developer Debug Info tab it said the player has 1 Attempt (no guessing has been done yet).
5. When a user guesses a number outside of 1-100 there is no error message for that. The game reads it as a regular guess.
6. Difficulty isn't working as intended. The code shows that the secret number should be in between different ranges, but the game doesn't account for this (Ex: Difficulty: Hard (Max should be 50); Secret: 54). The Settings bar on the side shows the expected range, but the info banner under "Make a guess" doesn't show the new range, even though the number of allowed attempts on the banner gets updated upon difficulty change.
7. The app doesn't account for if the player submits the same guess. (Let the player know they already guessed this number; don't add an attempt)
8. The Developer Debug Info tab is lagged behind. So if player wins on second try, the stats shown in the dev tab are one guess behind.
9. Changing the difficulty doesn't automatically start a new game. Ex: once launching the game the difficulty is normal, secret number is 90. I change the difficulty to easy, the secret number is still 90.

**Bug Reproduction Log**

Document at least 3 bugs you found. Add rows as needed.

| Input | Expected Behavior | Actual Behavior | Console Output / Error |
|-------------------------|-------------------|-----------------|------------------------|
| Click "New Game" button | All game stats reset (secret number, attempts, history, score) and guessing is possible again | Only 2 of the 4 reset: the secret number changed and attempts went to 0, but History and Score in Developer Debug Info kept their old values | None. No error in the terminal or browser console |
| Guess a number that is too low (e.g. secret is 60, guess 20) | Hint says to go higher | Hint says the opposite, so the player is told to go lower | None. The game runs normally and gives wrong feedback |
| Guess a number outside 1–100 (e.g. 500 or -5) | Error message saying the guess is out of range, and the attempt isn't counted | No error. The guess is treated as a regular guess and uses up an attempt | None. No error is raised |

---

## 2. How did you use AI as a teammate?

- Which AI tools did you use on this project (for example: ChatGPT, Gemini, Copilot)?

Answer: Claude Code

- Give one example of an AI suggestion that was correct (including what the AI suggested and how you verified the result).

Answer: One thing that AI suggested that was correct was how to get pytest to run. When I first had Claude add tests to the test_game_logic.py and ran pytest in the terminal, I got the following error:
ModuleNotFoundError: No module named 'logic_utils'

Claude explained to me that this was happening because pytest didn't have the project root on its import path. Claude suggested adding a pytest.ini file with "pythonpath = ." I was skeptical about adding this so I asked for clarification on what it would do. Claude explained that it only changes how pytest finds modules and doesn't touch the app, so I had Claude add it. I tested this change by running pytest once more on the terminal and tests ran! No errors.

- Give one example of an AI suggestion you did not accept as written (including what the AI suggested, why you rejected or changed it, and how you verified your version). It does not have to be a suggestion that was wrong: over-engineered, out of scope, harder to read, or a poor fit for this codebase all count.

Answer: One of the bug I decided to fix was the hints being incorrectly given. When I got to the writing tests for the bugs I have fixed, I asked Claude (in the session that I used to fix the hint bug) to go through test_game_logic.py and see if our bug fix is being tested and if it is not to add test for our fix (I wanted to see if it would read the frist 3 tests that were in that file). It said that our fix wasn't being tested because the result was only checking the label "Too High" / "Too Low" and not the actual hint, which is a fair point. I asked it why is this not a good enough test and it mentioned the original bugged code (the one we have already fixed) saying that there could be a case where the return could be "Too High", "Go HIGHER!" or "Too Low", "Go LOWER!" so the wrong messages. I asked it ok so is this still present in the code. Claude literally said no the wrong messages are no longer in the code (so the wrong messages aren't possible to get). So I asked it, "Knowing this, does the first 3 tests in test_game_logic.py test our bug fix?" and again it said that they don't test our change and it proposed a test that checked for both the label and the hint.

I understand what Claude meant. But the logic behind the code fix and tests was correct, so I ended up not doing the test change Claude recommended.

---

## 3. Debugging and testing your fixes

- How did you decide whether a bug was really fixed?

Answer: Tested it with different test cases. For example, the New Game button bug. Once the code was fixed, I ended up running the app again and testing the answer (wrong a few times), then starting a new game with the Dev Info expanded and I noticed that Score and History was getting reset!

Another issue with the New Game button was that I wasn't able to actually guess in the new game initially after cloning the repo. But after this bug fix, I tried playing multiple rounds to see if I was now able to actually guess (I was).

- Describe at least one test you ran (manual or using pytest)  
  and what it showed you about your code.

Answer: I hadn't noticed that the Attempts in the Dev Info section counted UP. Since the bugged version of the code started at 1, for some reason I had thought that it was supposed to count DOWN the attempts. I realized my initial assumption was wrong when I started testing the code change for the New Game button.

- Did AI help you design or understand any tests? How?

Answer: Yes, as I have mentioned in a previous answer, Claude helped me understand why I was initially getting an error when trying to run pytest in terminal. Claude recommended creating pytest.ini file with "pythonpath = ."

When I was confused about what this would do, it explained that pytest.ini only changes how pytest finds modules and doesn't touch the app.

In addition, once the pytest ran successfully, the initial tests (that came with the repo) failed. I asked Claude for assistance (different session than the one I mentioned in my previous response regarding these 3 tests). It explained that check_guess returned two things (a tuple) and the test originally compared the whole tuple to just the label - "Win", "Too Low", "Too High".


---

## 4. What did you learn about Streamlit and state?

- How would you explain Streamlit "reruns" and session state to a friend who has never used Streamlit?

Answer: Streamlit works like a script that runs top to bottom every time you click a button or type something. Each rerun starts fresh, meaning that normal variables get reset. If the game stored the secret number in a regular variable, it would pick a new number after every guess.

Session state is Streamlit's memory. It is a dictionary that survives between reruns, so things like the secret number, attempts, score, and guess history can be kept across clicks.

This also explains the New Game button bug. Clicking the button only reset some of the session state values (secret and attempts), not all of them (history and score). Anything stored in session state has to be reset explicitly, or it stays the same across the reruns.


---

## 5. Looking ahead: your developer habits

- What is one habit or strategy from this project that you want to reuse in future labs or projects?
  - This could be a testing habit, a prompting strategy, or a way you used Git.

Answer: When I first started testing the application for existing bugs, I immediately started taking notes of what I was finding. I really liked this approach! Maybe next time, while I do this, I can start looking through the code right away to see what is happening/where the bug is coming from.

I really liked using pytest. I would like to use this in the future if possible.

Laslty, I will use the suggesstion of committing in segments. In the future, I will probably commit after Phase or after I made big changes in the files.

- What is one thing you would do differently next time you work with AI on a coding task?

Answer: I would try to get more comfortable with the existing codebase before prompting Claude.

- In one or two sentences, describe how this project changed the way you think about AI generated code.

Answer: I think it may catch things that the human may have missed upon going through the codebase. However, this can also be true the other way around (Ex: the testing recommendation that Claude gave me, which I rejected using).

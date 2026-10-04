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
- Give one example of an AI suggestion that was correct (including what the AI suggested and how you verified the result).
- Give one example of an AI suggestion you did not accept as written (including what the AI suggested, why you rejected or changed it, and how you verified your version). It does not have to be a suggestion that was wrong: over-engineered, out of scope, harder to read, or a poor fit for this codebase all count.

---

## 3. Debugging and testing your fixes

- How did you decide whether a bug was really fixed?
- Describe at least one test you ran (manual or using pytest)  
  and what it showed you about your code.
- Did AI help you design or understand any tests? How?

---

## 4. What did you learn about Streamlit and state?

- How would you explain Streamlit "reruns" and session state to a friend who has never used Streamlit?

---

## 5. Looking ahead: your developer habits

- What is one habit or strategy from this project that you want to reuse in future labs or projects?
  - This could be a testing habit, a prompting strategy, or a way you used Git.
- What is one thing you would do differently next time you work with AI on a coding task?
- In one or two sentences, describe how this project changed the way you think about AI generated code.

# AI Interactions Log

> **Stretch features only.** Only fill in the sections that apply to stretch features you attempted. If you did not attempt a stretch feature, leave its section blank or delete it. This file is not required for the core project.

---

## Agent Workflow (SF8)

> Document your experience using an AI agent (e.g., Cursor Agent, Claude, Copilot) to make multi-step changes autonomously.

**What task did you give the agent?**

<!-- Describe the goal you asked the agent to accomplish -->

**What did the agent do?**

<!-- List the steps the agent took (files edited, commands run, etc.) -->

**What did you have to verify or fix manually?**

<!-- Describe anything the agent got wrong or that required human review -->

---

## Test Generation (SF7)

> Document how you used AI to help generate or improve tests.

| Edge Case | Prompt Used | AI-Suggested Test | Did It Pass? | Your Reasoning |
|-----------|-------------|-------------------|--------------|----------------|
| Empty and `None` input to `parse_guess` | "Take a look at the current tests in test_game_logic.py and find some edge cases that were missed. What can be tested? What could possibly break the game?" | `test_parse_guess_empty_and_none`: `""` and `None` both return `(False, None, "Enter a guess.")` | Yes | Submitting with a blank box is the most common mistake a player can make. This pins down that it's rejected with a clear message instead of crashing. |
| Non-numeric and whitespace-only input | Same prompt, then "let's try a few parse_guess tests and a few check_guess tests… what tests would you suggest?" | `test_parse_guess_rejects_non_numbers`: `"abc"`, `"12abc"` and `" "` return "That is not a number." (I added the `" "` case myself.) | Yes | Mixed letters and digits like `"12abc"` could slip through a sloppy parser. A whitespace-only string is easy to forget because it isn't `""`, so I added it. |
| Valid ints with surrounding whitespace | Same as above | `test_parse_guess_valid_ints_and_whitespace`: `"42"` returns 42 and `" 7 "` returns 7 | Yes | Players often type a stray space. This confirms it's tolerated, not rejected. |
| Decimal input truncates | Same as above | `test_parse_guess_decimals_truncate`: `"5.9"` gives 5 and `"-0.5"` gives 0 | Yes | This pins the current truncation behavior so a later change is deliberate. It also means 50.9 would win against a secret of 50, which I may want to reconsider. |
| Off-by-one boundaries in `check_guess`, with hint text | Same as above | `test_check_guess_boundaries_and_messages`: 51 vs 50 gives "Too High / Go LOWER!" and 49 vs 50 gives "Too Low / Go HIGHER!" | Yes | Once again Claude suggested testing the full outcome of the check_guess function (I spoke of this happening in one of my reflections.md reponses). I allowed these tests this time. Interesting that this suggesstion was brought up in two different sessions. |
| Out-of-range guess (500 on a 1–100 game) | Same as above | `test_out_of_range_guess_is_rejected`: submit `"500"` and expect an error message | No, expected failure (`xfail`) | The game accepts any integer, so 500 just gets "Too High" and wastes an attempt. I marked it `xfail` instead of fixing it because I haven't decided what the behavior should be yet. It documents a real gap. |

---

## Linting & Style (SF9)

> Document your use of AI for linting or code style improvements.

**Prompt used:**

```
<!-- Paste the prompt you gave the AI -->
```

**Linting output before:**

```
<!-- Paste relevant linter warnings/errors -->
```

**Changes applied:**

<!-- Describe what you changed based on the AI's suggestions -->

---

## Model Comparison (SF11)

> Compare two AI models on the same task.

**Task given to both models:**

<!-- Describe what you asked each model to do -->

| | Model A | Model B |
|-|---------|---------|
| **Model name** | | |
| **Response summary** | | |
| **More Pythonic?** | | |
| **Clearer explanation?** | | |

**Which did you prefer and why?**

<!-- Your conclusion -->

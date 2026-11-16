# Limitations
1. Gemini is not good at being random. At the start of the implementation, Gemini picked 37 for 12 tests in a row. This was partially fixed by code: the code picks a random range for the AI to pick a number from (`randint` is only the fallback if the AI fails). But even with this, I've noticed during my testing that it favors certain numbers.
2. The guardrails are shallow since they specifically check for the words "higher" and "lower." It doesn't check if the hint makes sense or if the context of the hints tells the user how close they are to the secret number.
3. The Gemini API tier I used is the free tier. This caused timeouts (fairly often during testing). In addition, if the model I'm using is retired, the code would have to be updated.

# Misuse
The risks for this project are fairly low, but one thing that could be misused is the AI's tone. This tone is heavily modeled on *Dungeon Crawler Carl*. If the prompt gets changed, the tone may become very aggressive. In my current prompt, I put "PG-13" but this could be removed.

# AI Reliability Testing Reflection
1. I mentioned in this page's Limitations section: Gemini is not good at being random. I was very surprised to find that once the API and prompt were set up and I started testing Gemini's game master abilities, it would pick the same random number over and over again. I also tried changing the temperature, and that didn't help. That is why I ended up using the range method mentioned in the first section.
2. In my tests, Gemini always gave the correct hints. It never told the user to go higher when they should've gone lower with their guesses.

# My Experience Collaborating With AI
**Accepted**

Giving Gemini a random range to pick the secret number from

**Rejected**

When I first mentioned I wanted the AI game master to be like the AI in *Dungeon Crawler Carl*, Claude made the prompt for Gemini so specific to the book that I felt like a regular player of the game would not understand what the hints meant. There were even hints that made zero sense to me. I told Claude to remove certain phrases entirely.
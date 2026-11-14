# PROMPTS.md — AI Usage Log

This file is the record of AI use on this codebase. At the end of every
agent session, direct the agent to write the session log with this prompt:

> Append a session log to PROMPTS.md at the repo root, under today's date,
> newest entry at the top. Record every prompt I gave you this session, in
> order, including any corrections. End the entry with a short summary:
> the outcome, any places where I deviated from a recommended answer or
> asked follow-up questions, and anything that went sideways.

Two rules:

- Entries are added only by that prompt, never unprompted.
- New entries go at the top. Never rewrite or delete an old entry — the
  log is part of your work, and an honest log of a session that went
  sideways is worth more than a tidy one.

Each entry has this shape:

    ## YYYY-MM-DD — <one-line summary>

    ### Prompts
    1. ...

    ### Summary
    - **Outcome:** what was built and what was kept
    - **Deviations:** recommendations overridden, follow-up questions asked
    - **Sideways:** failures, wrong turns, and how they were caught

## 2026-11-14 — Researched free APIs, picked TCGdex, built and verified a console check script

Session started 2026-11-12 (research) and continued 2026-11-14.

### Prompts
1. `/research` Research free external API providers that I could use for a Django project where users can search and save items and add notes or ratings to them. Some ideas for the project include games, movies, books, tv shows, recipes, music, and the like. I have a particular interest in games, especially Pokemon, if there are any APIs that would allow us to build a project around that. However, I am also open to any of the other topics listed or similar topics that would work well for this project. Compare the API providers using official documentation, including available data, free limits, and signup requirements.
2. `/grill-me` I want to use the TCGdex. Please write a short console script that makes a real request to this provider so we can verify access to the API before we start building the project. The script needs to fulfill the following requirements: Accept user input, such as a search phrase or item identifier; Make a meanigful request to the external API; Use my own credentials if the provider requires it; Display selected results clearly in the console; Handle unsuccessful requests and empty results with meaningful messages. For example, the script might allow us to enter the title or number of a Pokemon card and receive matches and details about the card. Something along those lines. This script belongs to a future Django project that will use uv and Python.
   - Grill-me answers, one question at a time:
     1. Input flow: **Search, then pick** (recommended)
     2. HTTP library: **requests** (recommended)
     3. uv setup: **uv project now** (recommended)
     4. Result list: **First 20 + total** (recommended)
     5. Card details: **Core fields** (recommended)
     6. Loop/errors: **Loop until quit** (recommended)
3. Walk through the code. Identify how the API requests get made, retrieved, and displayed in the console.
4. Update PROMPTS.md and commit and push to GitHub
5. (Correction, after rejecting the first edit and commit) Make the suggested edit to PROMPTS.md. When you commit to GitHub, use the message "Research API provider and verify external API access"

### Summary
- **Outcome:** A background agent wrote `docs/research/free-api-providers.md`, a cited comparison of about 25 free APIs. It recommended PokeAPI for Pokemon, with TCGdex as the pick for Pokemon cards. TCGdex was chosen. A uv project was set up (`pyproject.toml`, `uv.lock`, with `requests` as a dependency), and `scripts/tcgdex_check.py` was written. The script searches cards by name, shows the first 20 matches, fetches the picked card's details, and loops until you quit. It was run against the live API, and its error paths were tested: no matches, an invalid pick, no internet connection, a server error (HTTP 500), and a card ID that doesn't exist. TCGdex needs no API key, so the script uses no credentials. A walkthrough of the code was given in chat.
- **Deviations:**
  - Every grill-me recommendation was accepted. Card language defaulted to English without a separate question.
  - The first commit attempt used a commit message Claude wrote. It was rejected and replaced with the user's own message.
- **Sideways:**
  - Research: RAWG was down (HTTP 522) during the research, and Giant Bomb's API is offline, so for those two the report relies on Internet Archive copies of their own pages.
  - Research: the Pokemon TCG API (pokemontcg.io) turned out to be deprecated.
  - Testing: the first test run sent input through PowerShell, which added a hidden byte-order mark to the first line, and the sample answers were in the wrong order. The run was redone through Bash and passed.
  - Testing: the timeout error message was never triggered.
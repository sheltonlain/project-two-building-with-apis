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

## 2026-11-15 — Implemented Phase 2: Account page

### Prompts
1. `/implement @prd/pokedex-card-collection.md @plans/pokedex-card-collection.md Implement phase 2`
2. "yes, approved" (approved the two TDD behaviors)
3. "yes, make it pass" (behavior 1: a signed-in user can update their username and email)
4. "yes, move on to behavior 2"
5. "yes, make it pass" (behavior 2: a taken username or email, ignoring case, is rejected and nothing is saved)
6. "yes, continue with the rest of the phase"
7. "what is the username/password for user A?"
8. "all manual steps check out"
9. "Is this a  feature-specific business rules or does it predict commands or  project structure? We don't want anything like that in CLAUDE.md, and we want to keep this file very straightforward without verbose explanations."

### Summary
- **Outcome:**
  - `/account/` is now an edit form for the signed-in user's username and email. It always edits `request.user` (there's no id in the URL), and it shows "Your details were saved." after a save. A "Change password" card links to Django's password-change flow, which got its own DaisyUI templates (`password_change_form.html`, `password_change_done.html`) instead of the admin-styled defaults.
  - The case-insensitive email check is now shared by sign-up and the Account page (`ensure_email_available`). On the Account page it ignores the user's own row, so the error appears under the Email field.
  - TDD covered two behaviors: updating username and email, and rejecting a taken username or email. Normal tests cover keeping your own email (or changing its case), showing only your own details, ignoring another user's id in the POST, the save confirmation, a successful password change that keeps you signed in, a wrong old password, and sign-in being required for password change. 30 tests pass; Ruff is clean.
  - All four Phase 2 acceptance criteria are ticked in the plan, backed by tests and the user's manual checks. CLAUDE.md was not changed.
- **Deviations:**
  - The user asked which username and password "user A" meant in the manual steps. Claude explained there was no preset account, found the existing local `example` user, and gave three options: sign in as it, reset its password with `changepassword`, or sign up a new account.
  - Claude suggested adding the case-insensitive email rule to CLAUDE.md. The user asked whether it was a feature-specific rule; Claude agreed it was and added nothing.
- **Sideways:**
  - Behavior 2's RED failed for two different reasons. The username error was already caught but not shown, because the Account template still had the placeholder and didn't render the form. The case-insensitive email error landed in the non-field errors (from the expression constraint) instead of under Email. Both were fixed by the same GREEN step.
  - The "keep your own email" test first expected `Ash@Example.com` to be saved as typed. Django lowercases the domain part on save, so the expected value was corrected to `Ash@example.com`.

## 2026-11-15 — Implemented Phase 1: project skeleton and sign up / sign in / sign out

### Prompts
1. `/implement @prd/pokedex-card-collection.md @plans/pokedex-card-collection.md Implement Phase 1`
2. "yes, go ahead with those three" (approved the three TDD behaviors)
3. "yes, make it pass" (behavior 1: duplicate email rejected, ignoring case)
4. "add the model-level fix now, then move to behavior 2"
5. "yes, make it pass" (behavior 2: anonymous visitors redirected to sign-in)
6. "yes, move on to behavior 3"
7. "yes, make it pass" (behavior 3: valid sign-up signs the user in and redirects)
8. "yes, continue with the rest of Phase 1"
9. "Evrything passes except I don't understand the instructions in step 7"
10. "step 7 passes too, both files load"
11. "Are any of these  feature-specific business rules or predict commands or project structure? We don't want anything like that in CLAUDE.md, and we want to keep this file very straightforward without verbose explanations."
12. "write the PROMPTS.md entry now, then commit and push"

### Summary
- **Outcome:**
  - Built the `pokedex` project with the `accounts`, `catalog`, `collection` and `api` apps. Settings come from environment variables (`.env`, git-ignored; `.env.example` committed). Also set up the database cache, Tailwind + DaisyUI through django-tailwind-cli, HTMX 2.0.4 from a CDN, and pytest and Ruff configuration in `pyproject.toml`.
  - The custom User model is in the first migration. Email is required and unique ignoring case, enforced by the sign-up form and a database constraint.
  - Built sign-up (signs the user in and goes to the collection), Django's sign-in and sign-out, and placeholder Collection, Wishlist and Account pages behind sign-in. The base layout's navigation changes when signed in.
  - TDD covered three behaviors: duplicate email rejected ignoring case, anonymous redirects to sign-in, and valid sign-up signing the user in. Normal tests cover duplicate usernames, sign-in and sign-out, the layout and nav, and environment-based settings. 20 tests pass; Ruff is clean.
  - The README has setup steps. All seven Phase 1 acceptance criteria are ticked in the plan, backed by tests and the user's manual checks. CLAUDE.md was not changed.
- **Deviations:**
  - After behavior 1, Claude pointed out that the email check only lived in the form. The user asked for the database-level fix right away instead of waiting for Phase 2.
  - The user didn't understand manual step 7 (Network tab check). Claude re-explained it with a simpler "view page source" method plus step-by-step dev-tools instructions.
  - Claude offered five possible CLAUDE.md additions. The user asked whether they were feature rules, commands or project structure; Claude agreed they all were (or were tooling notes) and added none.
  - The implement skill says to update PROMPTS.md, but PROMPTS.md says entries are added only by its own prompt. Claude asked, and the user said to write the entry.
- **Sideways:**
  - A Bash `cd` into `.venv/.../django_tailwind_cli` to inspect the package carried over as the working directory. It was caught and reset before creating the project.
  - The Grep tool found nothing in `.venv` (it's git-ignored), so Bash `grep` was used to find the DaisyUI setting.
  - `ruff format .` reformatted the earlier `scripts/tcgdex_check.py`, which also has lint errors. The change was reverted and `scripts/` was excluded from Ruff.
  - The first migration was regenerated, not added to, when the case-insensitive email constraint was introduced, since nothing had been committed or shared.
  - Emptying the app stub files with `Set-Content -Encoding utf8NoBOM` failed on Windows PowerShell 5.1; the fallback `WriteAllText` did the job.
  - In the server smoke test, PowerShell couldn't read the `/collection/` redirect header. The redirect was already covered by tests and later confirmed manually.

## 2026-11-15 — Turned the PRD into a 14-phase tracer-bullet plan

### Prompts
1. `/prd-to-plan`
2. "I'm okay with th4 granularity and order. If we combined 14 and 15, would that make 14 a lot heavier than it is now?"
3. "yes, merge them and write the plan"
4. "Log this session to PROMPTS.md and commit and push changes to GitHub with the message "Made plan with prd-to-plan skill""

### Summary
- **Outcome:**
  - Claude read `prd/pokedex-card-collection.md` and checked the repo, which has no Django code yet. It proposed the durable decisions and 15 vertical-slice phases, each mapped to PRD user stories.
  - The user accepted the granularity and order. The two API phases (token + collection API, wishlist API) were merged into one, giving 14 phases.
  - The plan was written to `plans/pokedex-card-collection.md`. Its header records the stack, the four apps, the models and how they relate, the URL patterns, sign-in and per-user data ownership, the TCGdex client rules and the shared services module. Each phase has its user stories, a description of what to build and acceptance criteria.
- **Deviations:**
  - The user asked whether merging Phases 14 and 15 would make Phase 14 much heavier. Claude estimated about 20–30% more work, because the wishlist API reuses Phase 14's setup, and recommended the merge. The user accepted.
  - Claude's other suggested options were not taken: merging Phases 3+4 or 7+8, moving notes earlier, and splitting wish fulfillment into two phases.
- **Sideways:**
  - Nothing went wrong.
  - The URL paths in the plan header (such as `/search/card/<tcgdex_id>/` and `/account/`) were proposed by Claude. The PRD doesn't specify them.

## 2026-11-14 — Grilled the Pokedex design (30 questions, 3 prototypes) and wrote the PRD

### Prompts
1. `/grill-me @project-idea.md`
   - Q1, how a card is stored locally: "a" (a shared Card table plus a per-user link table, which was recommended)
   - Q2, collection vs. wishlist: "Option A and we'll explore the second copy more in the next question" (one model with a status field, which was recommended)
2. `/prototype let's prototype the logic from this question and from the previous question, which asked about having a card just in the wishlist and just in the saved collection, not in both. I want to compare these features to see what makes the most user friendly experience to collectors`
3. "I like option C the most, but I do have some questions. Does every card in the API come preloaded with a variant, or is this something the user would have to input themselves?" (Q3: picked one entry per copy with a variant)
4. "Let's go with option A. I do also have a quick side note that I forgot to add in to project-idea.md -- I want card price to be a detail that we show for the cards, user collections, etc. I also want them to be able to track the total value of their card collection using our web application. We don't have to stop and address this right now, but I do want it to be added to project-idea.md and addressed during this grill-me session." (Q4: the simple five variant types, limited to what each card supports)
5. "Let's go with option B" (Q5: optional condition field)
6. "Let's go with option B, no condition on wishes" (Q6: a wish names a variant or "Any variant")
7. "I like option A with the Undo link. Is there also a way we can add a message to let the user know the card was removed from their wishlist since it was added to their collection?" (Q7: automatic wish fulfillment)
8. `/prototype prototype the UI for these options for me` (Q8: what Undo undoes)
9. "The search is not working"
10. "no cards are being displayed, so I cannot add them to the collection or wishlist"
11. "I like placement 3, inline on the wishlist row, and option C" (Q8: notice inline on the wishlist row, with both Undo and "Keep it on my wishlist" links)
12. `/prototype prototype the ui for these options` (Q9: what the user sees when adding from a page that doesn't show the wishlist)
13. "I like option B, but I do have one suggestion. I don't like the undo button too much. I like everything else we have decided as far as the "keep on wishlist" option. Instead of the undo button, can we have an add to collection button that shows the quantity that we own on the card. Like a plus/minus situation that keeps count and easily let's us remove something if we didn't mean to add it?"
14. "I like option B. One quick note, I don't like that the card condition does not change the price. Since we can't really calculate this, I think we should just get rid of the condition placeholder altogether." (Q10: which copy "−" removes)
15. "B, and keep them as two models" (Q11: one row per user, card and variant, with a quantity)
16. "Option A" (Q12: TCGplayer USD prices only)
17. "Option B" (Q13: stored prices, refreshed when a card is fetched, plus a Refresh button)
18. "Option A" (Q14: a CardVariant model holding prices)
19. "Option C" (Q15: search tiles load their details through HTMX)
20. "I like option A, and I'm okay with rule #2. Would rule #1 make our application very slow?" (Q16: set and rarity dropdowns)
21. "What I really meant in my last question is would it make our application very slow if we did not implement rule #1? For this question, I do like option B if it is actually viable and does not slow down our app." (Q17: search pagination)
22. "Let's just implement rule #1 so our application does not slow down and use our original option B with the cache."
23. "I no longer want to have the public sharing feature as it seems too broad for the scope of this project. Let's remove that requirement from project.idea.md." (asked in reply to Q18, what users can make public)
24. "If I go with your recommendation for now, can I add the email verification later?" (Q19: sign-up and sign-in method)
25. "Option B" (Q20: username, email and password at sign-up)
26. "Option B" (Q21: account info plus notes on cards)
27. "Option A" (Q22: one collection tile per card and variant)
28. "Option A and change the default." (Q23: sort options, with the default changed to date added)
29. "Option B, same controls on wishlist" (Q24: collection and wishlist filters)
30. "Option A" (Q25: Django REST Framework)
31. "Option A" (Q26: DRF token authentication)
32. "Option A, and the rules are fine" (Q27: API endpoints and create behavior)
33. "Option C" (Q28: timeouts plus a 60-second "TCGdex down" flag)
34. "Let's go with your recommendation" (Q29: hotlinked images with a placeholder)
35. "Option C" (Q30: local now, but deploy-ready)
36. `/to-prd`
37. "update PROMPTS.md"

### Summary
- **Outcome:**
  - A 30-question grill-me session settled the full Pokedex design:
    - **Data model:** custom User, Card, CardVariant (with stored TCGplayer USD prices), OwnedCard (with quantity) and Wish (with "Any variant" and `fulfilled_at`).
    - **Wishlist and collection behavior:** automatic wish fulfillment, plus a − N owned + stepper on search cards.
    - **Search:** works through HTMX, with cached lists of result IDs for real page numbers. A search needs at least one filter.
    - **Collection and wishlist pages:** filter and sort on local data.
    - **API:** Django REST Framework with token authentication.
    - **Failure handling:** a TCGdex circuit breaker.
    - **Setup:** deploy-ready settings.
  - `project-idea.md` was edited twice. Card prices and collection value were added as a new requirement. Public sharing was removed, and the requirements were renumbered #1–#12.
  - Three throwaway prototypes were built in `prototypes/`:
    - `collection-wishlist-models.html`: a logic comparison of three data models.
    - `wish-fulfilled-notice.html`: notice placements and link options.
    - `add-from-anywhere-notice.html`: multi-page navigation, later updated with the stepper.
  - The PRD was written to `prd/pokedex-card-collection.md`. It has 92 user stories, the implementation decisions, an out-of-scope list and a table mapping requirements to user stories.
  - Several design facts were checked against the live TCGdex API instead of assumed:
    - variant flags and per-variant prices exist on every sampled card
    - search results contain only ID, name and image
    - the set, rarity and pagination filters work, but responses include no total count
    - there are 221 sets, 21 series and 44 rarities
    - response sizes and times for broad and blank searches
  - Nothing was committed.
- **Deviations:**
  - **Q3:** after the logic prototype, the user picked per-copy entries with variants (C) over the recommended quantity field (B).
  - **Q5:** the condition field (B) was chosen, then removed entirely in prompt 14 because it couldn't affect price.
  - **Q8–Q9:** the recommended options were accepted (both links, then the card note plus the persistent wishlist row). The user then replaced Undo with a − N owned + stepper.
  - **Q10:** B was picked over the recommended A. Removing condition then made the question moot.
  - **Q16–Q17:** the user asked whether rule #1 would slow the app. Claude first answered a slightly different question, then re-answered with measured numbers. The user kept rule #1 and the cached page-number pagination.
  - **Q18:** the user dropped public sharing from the requirements instead of choosing an option.
  - **Q19:** the user asked whether email verification could be added later before accepting the recommendation.
  - **Q23:** A was chosen over the conditional recommendation B, and the user accepted Claude's suggested change of default to "Date added."
  - Every other question took the recommended option.
- **Sideways:**
  - **Prototype 2 search box:** it was a read-only placeholder, so the user reported search as "not working." Claude made it a working local filter.
  - **Prototype 2 rendered no cards at all.** The Tailwind browser CDN script declares a global named `go`, which collided with the prototype's own `go` function and threw a SyntaxError, so the whole script failed. This was also the real reason search looked broken. It was found by loading the page in headless Edge and reading the console errors, then fixed by wrapping the script in its own scope. Later prototypes were checked in headless Edge before hand-off.
  - **Headless Edge setup:** the first two attempts returned no output because Edge's output can't be captured directly in PowerShell. Redirecting output through `Start-Process` fixed it.
  - **TCGdex outage:** TCGdex returned "no available server" on all requests during a timing test, then recovered within a minute. The incident was used to justify the circuit-breaker design (Q28).
  - **Result counts:** in two PowerShell checks the counts printed wrong (as 1) because of a display quirk. The byte sizes were used instead, and a later check counted IDs with a regex.
  - **Outdated prototype:** `add-from-anywhere-notice.html` still shows the condition dropdown, which was removed from the design after the prototype was built.
  - **Undiscussed PRD details:** the PRD includes three details that were never asked about directly, and they were flagged for review: wishlist sort options, search results not creating Card rows, and showing only the oldest "as of" date on the collection total.

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
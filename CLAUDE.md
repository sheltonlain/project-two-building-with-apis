# Pokedex

A Django web app where signed-in collectors track the Pokémon cards they own and want, using card data and prices from the TCGdex API.

## Stack

- Python 3.14, managed with **uv** (package manager)
- Django, SQLite
- Tailwind CSS + DaisyUI via django-tailwind-cli; HTMX for partial page updates
- Django REST Framework (token + session auth) for the app's own API
- Ruff for linting and formatting; pytest + pytest-django for tests, with `responses` to fake TCGdex

## Architecture decisions

- One Django project, `pokedex`, with four apps: `accounts`, `catalog`, `collection`, `api`.
- Custom user model (extends `AbstractUser`) from project start.
- Business rules live in one shared services module; website views and the API both call it.
- A single TCGdex client module is the only code that talks to TCGdex, and it raises its own exceptions.
- TCGdex filters are contains matches; prefix a value with `eq:` for an exact match.
- While the TCGdex circuit breaker is open, automatic calls fail fast; a user-requested retry (`X-User-Retry: 1` header → `probe=True`) sends one real request and clears the breaker if it works.
- A failed search or filter list re-submits the current form by itself after a countdown (no user-retry header, replaces the history entry).
- Caching uses Django's database cache backend (SQLite).
- After a tile action, the tile is drawn from the stored Card (`Card.as_detail()`), so actions don't depend on TCGdex.
- Every user-owned query is scoped to the signed-in user; other users' objects return 404.
- Settings are deploy-ready: secret key, debug and allowed hosts come from environment variables, loaded locally from a git-ignored `.env`.
- Tests never call the real TCGdex API.
- User-facing error messages describe what happened and what to try next, without assuming whose fault it is.
- On SQLite, calculated decimals (annotations, aggregates) come back unrounded; round them to cents in the service or format them in the template.
- Collection and wishlist Undo records (last 20 removals each) are kept in the session, not the database.
- Every wish names a specific variant (no "Any variant"); one active wish per user and variant, enforced in the database.
- Restoring or keeping a wish never makes a second active wish for a variant; the older fulfilled wish is deleted instead.
- Notes can't be saved blank; clearing a note is a separate Delete note action.
- Wishlist actions that move a wish between sections (Got it, Keep, OK) re-render the whole wishlist body.
- Wishlist filters apply to the Got it section too, but sort and pagination apply only to active wishes.
- Links inside search tiles use `hx-boost="false"` so they open full pages.
- Collection actions don't reorder the list live; when an entry moves in a quantity or value sort, a Re-sort toast offers a reload.
- Refresh prices runs one card per HTMX request and skips the card cache (`card_detail(fresh=True)`); tile views refresh stored cards from cached details.
- When TCGplayer has no price date, the "as of" date is when the card was fetched.
- Demo data: `manage.py seed_demo` creates users `demo` and `misty`, password `pokedex-demo` (DEBUG only).
- HTMX views return a fragment for HTMX requests but a full page for history-restore requests, and swapped fragments include any form inputs whose values should survive the Back button.
- HTMX fragment responses carry `Vary: HX-Request` and are never cached (`pokedex/middleware.py`), so Back never shows a bare fragment.
- The card detail page falls back to the stored Card (`Card.as_detail()`) when TCGdex is down.
- Card page links to the collection and wishlist filter them by `q` (card name) and `set`.
- Notes actions called with `?from=card` answer with just the card page's note area, and without HTMX return to the card page.
- Signed-in pages are `no-store`, so Back/Forward never shows a stale copy.

## References

- PRD: `prd/pokedex-card-collection.md`
- Implementation plan: `plans/pokedex-card-collection.md`
- Prototypes (throwaway; the PRD wins where they differ): `prototypes/`

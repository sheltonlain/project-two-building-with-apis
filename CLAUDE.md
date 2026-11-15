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
- Caching uses Django's database cache backend (SQLite).
- Every user-owned query is scoped to the signed-in user; other users' objects return 404.
- Settings are deploy-ready: secret key, debug and allowed hosts come from environment variables, loaded locally from a git-ignored `.env`.
- Tests never call the real TCGdex API.
- User-facing error messages describe what happened and what to try next, without assuming whose fault it is.
- HTMX views return a fragment for HTMX requests but a full page for history-restore requests, and swapped fragments include any form inputs whose values should survive the Back button.

## References

- PRD: `prd/pokedex-card-collection.md`
- Implementation plan: `plans/pokedex-card-collection.md`
- Prototypes (throwaway; the PRD wins where they differ): `prototypes/`

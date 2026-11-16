# Pokedex

A Django web app where signed-in collectors track the Pokémon cards they own and want, using card
data and prices from the [TCGdex](https://tcgdex.dev) API.

## Running locally

Requires [uv](https://docs.astral.sh/uv/) (Python 3.14 is installed by uv if needed).

```sh
uv sync                                   # install dependencies
cp .env.example .env                      # then set DJANGO_SECRET_KEY in .env
uv run python manage.py migrate
uv run python manage.py createcachetable  # database cache table
uv run python manage.py tailwind build    # downloads the Tailwind + DaisyUI CLI on first run
uv run python manage.py runserver
```

During development, `uv run python manage.py tailwind runserver` rebuilds the CSS as templates
change.

### Demo data

```sh
uv run python manage.py migrate    # always first after pulling: new commits may add tables
uv run python manage.py seed_demo
```

Run `migrate` before `seed_demo` whenever you pull new commits. For example, phase 9 added the
wishlist table, and `seed_demo` fails with "no such table: collection_wish" until it exists.

This creates two users you can sign in as:

| Username | Password       | Seed data                                                     |
|----------|----------------|---------------------------------------------------------------|
| `demo`   | `pokedex-demo` | 30 collection entries and 5 wishes                            |
| `misty`  | `pokedex-demo` | 3 entries and 1 wish, for checking users can't see each other |

These are local demo accounts only. Re-running `seed_demo` resets their passwords, collections and
wishlists. It only runs with `DJANGO_DEBUG=true` and makes no TCGdex calls.

## Checks

```sh
uv run pytest
uv run ruff check .
uv run ruff format .
```

## Docs

- PRD: `prd/pokedex-card-collection.md`
- Implementation plan: `plans/pokedex-card-collection.md`

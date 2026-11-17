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

## API

`/api/collection/` and `/api/wishlist/` list, create, retrieve, update (PATCH) and delete the
signed-in user's own entries. Copy your token from the Account page and send it in a header:

```sh
curl -H "Authorization: Token <your token>" http://127.0.0.1:8000/api/collection/
curl -H "Authorization: Token <your token>" -H "Content-Type: application/json" \
  -d '{"card_id": "sv03.5-025", "variant": "normal", "quantity": 1}' \
  http://127.0.0.1:8000/api/collection/
```

In Windows PowerShell, `curl` is `Invoke-WebRequest`; use `Invoke-RestMethod` instead:

```powershell
$headers = @{ Authorization = "Token <your token>" }
Invoke-RestMethod http://127.0.0.1:8000/api/collection/ -Headers $headers
Invoke-RestMethod http://127.0.0.1:8000/api/collection/ -Method Post -Headers $headers `
  -ContentType "application/json" -Body '{"card_id": "sv03.5-025", "variant": "normal"}'
```

Variants are `normal`, `reverse`, `holo`, `first_edition` and `w_promo`. Lists take `search`, `set`,
`rarity`, `variant`, `ordering` (for example `name`, `-price`, `-value`) and `page`. A PATCH may
change `quantity` (0 deletes the entry) and `notes` on collection entries, and `notes` on wishes.
While signed in on the website, the same URLs open DRF's browsable API.

## Checks

```sh
uv run pytest
uv run ruff check .
uv run ruff format .
```

## Docs

- PRD: `prd/pokedex-card-collection.md`
- Implementation plan: `plans/pokedex-card-collection.md`

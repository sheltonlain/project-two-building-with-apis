# Plan: Pokedex, a Pokémon card collection tracker

> Source PRD: `prd/pokedex-card-collection.md`

## Architectural decisions

Durable decisions that apply across all phases:

- **Stack**: Python 3.14 (uv), Django, SQLite, Tailwind CSS + DaisyUI via django-tailwind-cli, HTMX, Django REST Framework, Ruff, pytest + pytest-django, `responses` for faking every TCGdex call.
- **Project and apps**: one Django project `pokedex` with four apps:
  - `accounts`: custom User, sign-up, Account page, API token management.
  - `catalog`: TCGdex client, Card and CardVariant, search page.
  - `collection`: OwnedCard and Wish, collection and wishlist pages, and the shared services module that holds all business rules.
  - `api`: DRF serializers, views and routing.
- **Configuration**: secret key, debug flag and allowed hosts come from environment variables (local `.env`, git-ignored). Django's database cache backend stores search ID lists, card details, set/series/rarity lists and the outage flag.
- **Models**:
  - **User**: extends AbstractUser; email required and unique; sign-in by username.
  - **Card**: one row per TCGdex card, shared by all users; unique TCGdex card ID (e.g. `sv03.5-025`), name, set ID/name, series, rarity, local number, base image URL. Created only when a user saves a card; never deleted when unreferenced.
  - **CardVariant**: FK Card; variant is one of Normal, Reverse holo, Holo, 1st Edition, W Promo; unique on (card, variant); nullable Decimal USD market price; price-updated timestamp. A card's CardVariant rows are its allowed variants.
  - **OwnedCard**: FK User, FK CardVariant; positive quantity; notes (≤ 500 chars); created/updated timestamps; unique on (user, variant); deleted at quantity 0.
  - **Wish**: FK User, FK Card; nullable FK CardVariant (null = "Any variant"); notes (≤ 500 chars); created timestamp; nullable fulfilled-at; nullable FK to the OwnedCard that fulfilled it.
- **URLs** (app-namespaced, named):
  - `/accounts/signup/`, `/accounts/login/`, `/accounts/logout/`, `/accounts/password_change/`
  - `/account/` (profile, API token)
  - `/search/` and per-tile fragments keyed by TCGdex card ID (e.g. `/search/card/<tcgdex_id>/`)
  - `/collection/` and `/wishlist/`, with entry actions keyed by pk
  - `/api/collection/` and `/api/wishlist/`, each with list, create, retrieve, partial update and delete
- **Authentication / authorization**: Django auth views for sign-in, sign-out and password change. Every collection, wishlist, account and card-management view requires sign-in. Every query is scoped to `request.user`, so other users' objects return 404. The API uses DRF Token authentication and Session authentication and rejects unauthenticated requests.
- **TCGdex boundary**: one client module is the only code that talks to TCGdex. It uses a 3 s connect / 5 s read timeout, no retries, and a 60 s circuit-breaker flag stored in the cache. It raises its own exceptions ("provider unavailable", "not found"), which views and the API turn into user-facing messages or HTTP 503/404 responses.
- **Business rules**: all add/remove/fulfill/restore logic lives in the `collection` services module and is called by both web views and the API.

---

## Phase 1: Project skeleton and sign up / sign in / sign out

**User stories**: 1, 2, 3, 4, 5

### What to build

Set up the `pokedex` project with its four apps, environment-driven settings, the database cache, Tailwind/DaisyUI, HTMX, Ruff and pytest. Create the custom User model before the first migration. Add a base layout with navigation that changes depending on whether the visitor is signed in. A visitor can sign up with username, email and password, sign in, and sign out. Placeholder collection, wishlist and account pages exist and redirect anonymous visitors to sign-in.

### Acceptance criteria

- [x] Settings read secret key, debug and allowed hosts from the environment; `.env` is git-ignored.
- [x] The custom User model is in place in the first migration; email is required and unique.
- [x] Sign-up shows clear errors for a duplicate username or email.
- [x] Sign-in, sign-out and post-login redirect work.
- [x] Anonymous requests to `/collection/`, `/wishlist/` and `/account/` redirect to the sign-in page.
- [x] Tailwind/DaisyUI styles and HTMX load on the base layout.
- [x] `pytest` and `ruff` run cleanly, and tests cover sign-up validation and the login-required redirects.

---

## Phase 2: Account page

**User stories**: 6, 7

### What to build

Add an Account page at `/account/` where a signed-in user edits their username and email, with uniqueness validation, and follows a link to Django's password-change flow.

### Acceptance criteria

- [ ] A user can update their username and email; taken values are rejected with a clear message.
- [ ] Password change works and keeps the user signed in.
- [ ] The page only ever shows and edits the signed-in user's own details.
- [ ] Tests cover the update flow and uniqueness errors.

---

## Phase 3: Name search through a fail-safe TCGdex client

**User stories**: 9, 13, 14, 15, 16, 18, 19, 70, 71, 73

### What to build

Build the TCGdex client (timeouts, circuit breaker, custom exceptions) and a `/search/` page with a name box. A name search fetches the full list of matching card IDs once per filter combination, caches it for 24 hours, and paginates it locally. The page shows the total count, numbered pages and tiles with image and name. An empty submission shows "Pick a name, set or rarity to start" and makes no request. An HTMX loading indicator shows while a search runs. If TCGdex fails, the page shows the provider-unavailable message with a Retry button. Search never creates Card rows.

### Acceptance criteria

- [ ] Partial name matches return results with a "N cards found" count and numbered pages.
- [ ] A repeat search with the same filters is served from the cache and makes no network call.
- [ ] An empty search shows the guidance message and makes no TCGdex call.
- [ ] Any failure (timeout, connection error, 5xx, malformed response) sets the 60 s outage flag; while it is set, calls fail immediately without a network request; after it expires, the network is tried again.
- [ ] A failed search shows the unavailable message and a Retry button that repeats the same query.
- [ ] Tile images use the low-quality webp URL suffix.
- [ ] Tests (with `responses`) cover the circuit breaker, timeout handling, the empty-search rule and pagination of cached ID lists.

---

## Phase 4: Set and rarity filters

**User stories**: 10, 11, 12, 75

### What to build

Add a set dropdown grouped by series (newest series first) and an alphabetical rarity dropdown to the search form. Their options come from TCGdex and are cached for 24 hours. Name, set and rarity can be combined, and each filter alone counts as a valid search. If the option lists can't be loaded, the dropdowns show the unavailable message instead of empty or broken controls.

### Acceptance criteria

- [ ] Set options appear under series headings, newest series first; rarity options are alphabetical.
- [ ] Set-only, rarity-only and combined searches each work and get their own cached ID list.
- [ ] Filter selections are kept in the query string across result pages.
- [ ] When TCGdex is down, the filter area shows the unavailable message and the page still renders.
- [ ] Tests cover combined filter query building and the dropdown fallback.

---

## Phase 5: Lazy tile details

**User stories**: 17, 22, 23, 61, 65, 72, 74

### What to build

Each search tile's lower half loads through its own HTMX request to the tile-fragment URL. The response is the card detail, cached for 24 hours, and shows set, rarity, a variant dropdown with only the card's real variants (preselected and fixed when only one exists), and the TCGplayer USD market price for the selected variant or "No price". If one tile's request fails, only that tile shows "Details unavailable" with Retry. Images that fail to load show a placeholder with the card name and number.

### Acceptance criteria

- [ ] Tiles render image and name first; details fill in afterwards.
- [ ] The variant dropdown lists only variants that the TCGdex flags allow; a single-variant card is preselected and fixed.
- [ ] The price matches the selected variant's TCGplayer market price; a missing price shows "No price".
- [ ] One failing tile shows its own Retry while the other tiles load normally.
- [ ] A broken image shows the name and number placeholder.
- [ ] Tests cover variant-flag mapping, price extraction (including missing prices) and per-tile failure.

---

## Phase 6: Add to collection and the stepper

**User stories**: 8, 21, 24, 25, 26, 27, 28, 29, 30, 31

### What to build

Introduce Card, CardVariant and OwnedCard, plus the services module's add and remove operations. A signed-in user presses "Add to collection" on a tile. The service looks up or creates the Card and its CardVariants (fetching from TCGdex if the card is new locally), rejects variants the card doesn't have, and increments the user's OwnedCard. The tile's lower half is swapped for a "− N owned +" stepper, a "You own: 2 Normal, 1 Reverse holo" summary and a short confirmation. "−" decrements, and the row is deleted at zero. Switching the variant dropdown re-requests the lower half so the price and owned count follow the selection.

### Acceptance criteria

- [ ] The first add creates Card and CardVariant rows with Decimal prices and timestamps, and an OwnedCard with quantity 1.
- [ ] "+" and "−" change the quantity; reaching zero deletes the OwnedCard row (Card rows remain).
- [ ] Unsupported variants are rejected by the service.
- [ ] The owned summary and confirmation update after each action, and switching variant shows that variant's price and count.
- [ ] Add and step actions require sign-in and only ever touch the requester's rows.
- [ ] Tests cover variant validation, quantity-zero deletion and owner scoping.

---

## Phase 7: Collection page, stepper and collection value

**User stories**: 46, 47, 55, 56, 62, 63, 64, 65, 66, 74

### What to build

The `/collection/` page lists one entry per OwnedCard: image, name, set, rarity, variant, quantity, price, value (price × quantity) and notes, newest first. The page uses local data only, so it works while TCGdex is down. Each entry has the stepper and a remove action. A summary shows the total value (database aggregate), the count of entries with no price, and the oldest "as of" date among stored prices.

### Acceptance criteria

- [ ] The page renders correctly with the TCGdex client forced unavailable.
- [ ] The default order is date added, newest first.
- [ ] Stepper and remove work from the collection page.
- [ ] The total value is computed in the database and excludes unpriced entries, and "N cards have no price" shows when relevant.
- [ ] Each price shows its "as of" date; missing prices show "No price".
- [ ] Requests for another user's entry return 404.
- [ ] Tests cover the value aggregate with no-price entries, offline rendering and 404 ownership.

---

## Phase 8: Collection search, filter, sort and pagination

**User stories**: 48, 49, 50, 51, 52, 53

### What to build

Add a search box (card name or notes, case-insensitive contains), plus set, rarity and variant dropdowns that list only values present in the user's own rows. Add sorting by name, price, value, quantity or date added, in either direction, with unpriced entries last when sorting by price or value. Pagination uses 24 entries per page with numbered pages, and filters and sort are kept in the query string.

### Acceptance criteria

- [ ] Search matches both card names and notes.
- [ ] Filter dropdowns list only values from the user's own collection.
- [ ] All sort keys work in both directions; null prices sort last for price and value.
- [ ] Pages hold 24 entries, and moving between pages keeps the filters and sort.
- [ ] Tests cover null-last ordering, value sorting and filter option scoping.

---

## Phase 9: Wishlist basics

**User stories**: 20, 32, 33, 34, 35

### What to build

Introduce the Wish model. From a search tile, a user can add a wish for the selected variant or for "Any variant", including for cards they already own. Saving a wish creates Card and CardVariant rows if needed. A basic `/wishlist/` page lists active wishes with a remove action. Search tiles show a badge when the card is wished for, naming the wished variant or "Any variant". The navigation shows the count of active wishes.

### Acceptance criteria

- [ ] Wishes can be created with a specific variant or as "Any variant", whether or not the card is owned.
- [ ] Removing a wish deletes it.
- [ ] Tile badges reflect the user's wishes and the variant wished for.
- [ ] The nav shows the active wish count.
- [ ] The wishlist works offline and is scoped to the owner (404 for others).
- [ ] Tests cover wish creation rules and owner scoping.

---

## Phase 10: Wish fulfillment

**User stories**: 36, 37, 38, 39, 40, 41, 42, 43, 44, 45

### What to build

Extend the services module's add and remove operations. After an add, the service fulfills at most one active wish: an exact-variant wish first, otherwise an "Any variant" wish for that card. It sets fulfilled-at and links the OwnedCard. A wish for a different variant stays open. The tile confirmation says when a wish was fulfilled and links to the wishlist. On the wishlist, fulfilled wishes appear crossed out with a "Got it" badge, the fulfilled date, and "Keep it on my wishlist" (reopens the wish, keeps the copy) and "OK" (deletes the wish) buttons. Active wishes get a "Got it" button that adds the wished variant, or the card's first variant for "Any variant", through the same logic. "−" on an OwnedCard restores the most recently fulfilled wish linked to it. The navigation shows a separate badge for fulfilled wishes awaiting dismissal.

### Acceptance criteria

- [ ] An exact-variant wish is fulfilled before an "Any variant" wish, and only one wish is fulfilled per copy added.
- [ ] Adding a different variant leaves a specific-variant wish active.
- [ ] The tile notice links to the wishlist when a wish was fulfilled.
- [ ] Keep, OK and Got it behave as described.
- [ ] "−" restores the most recently fulfilled wish linked to that OwnedCard.
- [ ] The nav badge counts fulfilled-but-not-dismissed wishes.
- [ ] Tests cover matching priority, wrong-variant non-fulfillment, restore on "−", Keep and OK.

---

## Phase 11: Wishlist search, filter, sort and pagination

**User stories**: 54

### What to build

Give the wishlist page the same controls as the collection: a name/notes search, set, rarity and variant filters drawn from the user's own wishes (the variant filter includes "Any variant"), sorting by name, date added, and price where a specific variant is wished for, and 24-per-page numbered pagination that keeps the query string.

### Acceptance criteria

- [ ] The "Any variant" filter value selects wishes with no variant.
- [ ] Price sort puts wishes without a priced variant last.
- [ ] Filters and sort are kept across pages.
- [ ] Tests cover the "Any variant" filter and option scoping.

---

## Phase 12: Notes

**User stories**: 57, 58, 59, 60

### What to build

Let users add, edit and clear plain-text notes (up to 500 characters) on collection entries and wishes, inline through HTMX or with a small form on both pages. Notes that are too long are rejected with a clear message.

### Acceptance criteria

- [ ] Notes can be added, edited and cleared on both pages.
- [ ] More than 500 characters shows a validation message and saves nothing.
- [ ] Notes are shown as plain text (escaped).
- [ ] Only the owner can edit notes (404 for others).
- [ ] Tests cover length validation and ownership.

---

## Phase 13: Price refresh

**User stories**: 67, 68, 69

### What to build

When a search tile's detail fetch succeeds for a card already stored locally, update its stored Card data and CardVariant prices and timestamps in the same step. Add a "Refresh prices" button on the collection page that refreshes every distinct card the user owns, one detail call per card, and reports progress through HTMX ("Refreshing 12 of 40…"). If the circuit breaker trips, the refresh stops, shows the unavailable message and keeps all existing prices.

### Acceptance criteria

- [ ] Viewing a tile for a stored card updates its prices and "as of" timestamps.
- [ ] The refresh shows progress and finishes with updated totals.
- [ ] An outage mid-refresh stops it, shows the message and leaves the remaining prices unchanged.
- [ ] Tests cover the automatic update, refresh progress and outage preservation.

---

## Phase 14: The app's own REST API

**User stories**: 76, 77, 78, 79, 80, 81, 82, 83, 84, 85, 86, 87, 88, 89, 90, 91, 92

### What to build

Add DRF with Token and Session authentication. The Account page shows the user's API token and has a "Regenerate token" action. `/api/collection/` and `/api/wishlist/` each support list (paginated, with the same search, set, rarity, variant and ordering options as the web pages), create, retrieve, partial update and delete, all scoped to the requesting user.

- **Collection create** takes a TCGdex card ID, a variant, a quantity (default 1) and optional notes, and goes through the services module (fetch if new, validate the variant, fulfill wishes). The response includes nested card details, the variant, quantity, price, price-updated time, notes and the fulfilled wish or null.
- **Collection partial update** may change quantity and notes only; quantity 0 deletes the entry.
- **Wishlist create** takes a TCGdex card ID, an optional variant (empty = "Any variant") and optional notes.
- **Wishlist partial update** may change notes only.

Errors: 400 with field errors for an unknown card ID, an unsupported variant, a note that is too long or an invalid quantity; 503 with a provider-unavailable message when TCGdex is down and the card isn't stored locally; 404 for other users' IDs; unauthenticated requests are rejected.

### Acceptance criteria

- [ ] The token is visible on the Account page, and regenerating it invalidates the old one.
- [ ] Token-header and session-authenticated requests both work; the browsable API is usable while signed in.
- [ ] Both list endpoints paginate and support the website's filter and ordering options.
- [ ] Collection create fulfills matching wishes and returns the documented response shape.
- [ ] Quantity 0 through PATCH deletes the entry; changing the variant is not allowed.
- [ ] Wishlist create supports "Any variant"; wishlist PATCH changes notes only.
- [ ] Unknown card or unsupported variant returns 400; TCGdex down for an unstored card returns 503.
- [ ] Other users' entries return 404; unauthenticated requests are rejected.
- [ ] Tests cover token authentication, 503 on create, quantity-zero deletion, variant validation and owner-only 404 on both endpoints.

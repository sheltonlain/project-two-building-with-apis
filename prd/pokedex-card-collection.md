# PRD: Pokedex, a Pokémon card collection tracker

## Problem Statement

Pokémon card collectors have no simple, personal place to keep track of what they own, what they still want, and what their collection is worth. Card data lives on public sites and marketplaces, but those sites don't know which cards a particular collector owns, which variant they have (Normal, Reverse holo, Holo, and so on), how many copies they hold, or what notes they keep about each card ("pulled from my first booster box", "trade target").

Collectors run into several practical problems:

- Finding a specific card means searching a catalog of roughly 24,000 cards across 221 sets. That is hard without filters for name, set and rarity.
- A wishlist kept in a notebook or spreadsheet drifts out of date. When a wanted card finally arrives, nothing tells the collector it can come off the list.
- Collectors care about variants, and a "Reverse holo Pikachu" is a different item from a "Normal Pikachu". Most simple trackers ignore that difference.
- Collectors want to know roughly what their collection is worth, and that number changes over time.
- Online card databases are sometimes unavailable. A collector's own records should not disappear when the card database goes down.

## Solution

Pokedex is a Django web application where a signed-in collector can:

- Search the TCGdex card catalog by name, set and rarity. Each result shows the card image, its available variants and its current market price.
- Add cards to a personal **collection**, choosing the exact variant and adjusting quantity with a simple **− N owned +** stepper.
- Keep a **wishlist** of cards they don't own yet. Each wish names the exact variant they want, just as collection entries do.
- Have wishes fulfilled automatically. When they add a card that matches a wish, the wish is marked as fulfilled. It stays visible, crossed out, on the wishlist page, where the user can choose to keep wishing for it or dismiss it.
- See the price of every card and the **total value** of their collection, based on TCGplayer market prices in USD, with an "as of" date and a button to refresh prices.
- Browse, search, filter, sort and page through their collection and wishlist. These operations use data stored in the app itself, so they keep working when TCGdex is unavailable.
- Add personal notes to cards in their collection and on their wishlist, and edit their own account details.
- Use the app's own REST API from another program to list, create, update and delete their collection and wishlist entries, authenticated with a personal API token.

When TCGdex is slow or down, the app says so clearly, offers a Retry option, and continues to serve everything already stored locally.

## User Stories

### Accounts and personal information

1. As a new visitor, I want to sign up with a username, email address and password, so that I can start tracking my cards.
2. As a visitor, I want to be told clearly when a username or email is already taken, so that I can pick a different one.
3. As a registered user, I want to sign in with my username and password, so that I can reach my collection and wishlist.
4. As a signed-in user, I want to sign out, so that nobody else using my device can change my data.
5. As a visitor who is not signed in, I want to be sent to the sign-in page when I try to open my collection, wishlist, account or card-management features, so that my data is never exposed or changed without signing in.
6. As a signed-in user, I want an Account page where I can edit my username and email address, so that my details stay up to date.
7. As a signed-in user, I want to change my password from the Account page, so that I can keep my account secure.
8. As a signed-in user, I want to be sure that no other user can see or change my collection, wishlist or notes, so that my records are private.

### Searching the card catalog

9. As a collector, I want to search cards by name using a partial match (for example "pika"), so that I can find a card without knowing its exact title.
10. As a collector, I want to filter a search by set using a dropdown grouped by series and ordered newest first, so that I can find a card from a specific set among 221 sets.
11. As a collector, I want to filter a search by rarity using a dropdown, so that I can narrow results to, for example, only Common cards.
12. As a collector, I want to combine name, set and rarity filters, so that I can narrow a search precisely.
13. As a collector, I want the search to ask me to pick at least one filter when I submit an empty search, so that I'm guided toward useful results instead of a meaningless list of every card.
14. As a collector, I want to see how many cards matched my search (for example "246 cards found"), so that I know whether to narrow it further.
15. As a collector, I want search results split into numbered pages, so that I can move through large result sets and jump to a specific page.
16. As a collector, I want search results to show each card's image and name immediately, so that the page feels fast.
17. As a collector, I want each search result to fill in its set, rarity, available variants and price a moment later, so that I get full details without waiting for the whole page.
18. As a collector, I want a loading indicator while a slow search is running, so that I know the app is working and not frozen.
19. As a collector, I want repeat searches to be fast, so that going back and forth between pages and searches doesn't feel slow.
20. As a collector, I want to see a badge on a search result when that card is already on my wishlist, including which variant I wished for, so that I recognize cards I'm looking for.

### Variants

21. As a collector, I want to choose a card's variant (Normal, Reverse holo, Holo, 1st Edition or W Promo) when adding it, so that my records match the physical card I have.
22. As a collector, I want the variant dropdown to list only the variants that card actually exists in, so that I can't record an impossible variant.
23. As a collector, I want the variant to be chosen automatically when a card exists in only one variant, so that I don't have to make a pointless choice.
24. As a collector, I want the price and owned count on a search card to update when I switch the variant dropdown, so that I see the numbers for the exact variant I'm looking at.

### Managing my collection from search

25. As a collector, I want an "Add to collection" button on each search result, so that I can save a card in one click.
26. As a collector, I want the Add button to turn into a "− N owned +" stepper once I own that card and variant, so that I can see how many I have and add more.
27. As a collector, I want to press "+" to add another copy of the selected variant, so that I can record duplicates.
28. As a collector, I want to press "−" to remove one copy of the selected variant, so that I can fix an accidental add immediately.
29. As a collector, I want the card to be removed from my collection when its count reaches zero, so that my collection only contains cards I actually own.
30. As a collector, I want a short "You own: 2 Normal, 1 Reverse holo" summary on a search card, so that I see all my variants of that card at a glance.
31. As a collector, I want a brief confirmation on the card after I add or remove a copy, so that I know the action worked.

### Wishlist

32. As a collector, I want to add a card to my wishlist with a specific variant, so that I can track exactly the version I'm hunting for.
33. *(Removed 2026-11-15: every wish names a specific variant, as collection entries do.)*
34. As a collector, I want to wish for a card I already own (for example a second copy, or a different variant), so that my wishlist reflects what I still want.
35. As a collector, I want to remove a card from my wishlist, so that I can drop cards I no longer want.
36. As a collector, I want a "Got it" button on wishlist entries, so that I can move a wished-for card into my collection directly from the wishlist.

### Wish fulfillment

37. As a collector, I want a matching wish to be fulfilled automatically when I add a copy to my collection, so that my wishlist stays accurate without extra work.
38. *(Removed 2026-11-15: every wish names a specific variant, as collection entries do.)*
39. As a collector, I want a wish for a specific variant to stay open when I add a different variant of the same card, so that receiving the wrong version doesn't wrongly clear my wish.
40. As a collector, I want the search card to tell me when an add fulfilled a wish, with a "View on wishlist" link, so that I notice even though the wishlist isn't on screen.
41. As a collector, I want fulfilled wishes to stay on the wishlist page, crossed out with a "Got it" badge and the date fulfilled, until I dismiss them, so that I can review what was fulfilled even after leaving the search page.
42. As a collector, I want a "Keep it on my wishlist" button on a fulfilled wish, so that I can keep the copy I added and still keep wishing for that card.
43. As a collector, I want an "OK" button on a fulfilled wish, so that I can dismiss it once I've seen it.
44. As a collector, I want the wish to come back automatically when I press "−" on the copy that fulfilled it, so that undoing an accidental add also restores my wishlist.
45. As a collector, I want a count of fulfilled-but-not-dismissed wishes shown in the navigation, so that I know there is something to review on my wishlist page.

### Browsing my collection and wishlist

46. As a collector, I want my collection page to list one entry per card and variant, showing image, name, set, rarity, variant, quantity, price and notes, so that each row matches what I physically own.
47. As a collector, I want my collection to open sorted by date added, newest first, so that the card I just added is at the top.
48. As a collector, I want to sort my collection by name, price, value (price × quantity), quantity or date added, in either direction, so that I can view it the way I need.
49. As a collector, I want cards with no price to sort after priced cards when sorting by price or value, so that missing prices don't clutter the top of the list.
50. As a collector, I want a search box on my collection that matches card names and my notes, so that I can find, for example, every card I noted as a trade target.
51. As a collector, I want set, rarity and variant filter dropdowns that list only values found in my own collection, so that the choices are short and relevant.
52. As a collector, I want my collection split into pages of 24 entries, with numbered pages, so that large collections stay easy to browse.
53. As a collector, I want my filters, sort order and page to be kept as I move between pages of results, so that I don't lose my place.
54. As a collector, I want my wishlist page to offer the same search, filter, sort and pagination controls as my collection, so that I only have to learn one set of controls.
55. As a collector, I want to adjust quantity and remove entries from my collection page, so that I can manage my collection without returning to search.
56. As a collector, I want my collection and wishlist to load and work even when TCGdex is down, so that my records are always available.

### Notes

57. As a collector, I want to add a personal note (up to 500 characters) to a card in my collection, so that I can record where I got it or what I plan to do with it.
58. As a collector, I want to add a personal note to a wishlist entry, so that I can record why I want it or where I might find it.
59. As a collector, I want to edit or clear my notes later, so that they stay accurate.
60. As a collector, I want a clear message if my note is too long, so that I can shorten it.

### Prices and collection value

61. As a collector, I want to see the TCGplayer market price (USD) for the selected variant on each search result, so that I know what a card is worth before I add it.
62. As a collector, I want to see each owned entry's price and its value (price × quantity), so that I understand where my collection's value comes from.
63. As a collector, I want to see the total value of my collection, so that I can track what it's worth.
64. As a collector, I want the total to tell me how many entries have no price (for example "2 cards have no price"), so that I understand the total is incomplete.
65. As a collector, I want cards without a TCGplayer price to show "No price" instead of a made-up number, so that I can trust the values I see.
66. As a collector, I want each price to show when it was last updated ("as of" date), so that I know how current it is.
67. As a collector, I want prices on my saved cards to refresh automatically whenever the app fetches those cards from TCGdex anyway, so that prices stay reasonably current without effort.
68. As a collector, I want a "Refresh prices" button on my collection page with a progress message, so that I can update all my prices on demand.
69. As a collector, I want refresh to tell me if TCGdex is unavailable and keep my existing prices, so that a failed refresh doesn't wipe out my data.

### Handling TCGdex failures

70. As a collector, I want a clear message when TCGdex is unavailable or a request fails, so that I know the problem isn't my fault and what to expect.
71. As a collector, I want a Retry button when a search or a single search result fails to load, so that I can try again without retyping my search.
72. As a collector, I want one search result that fails to load to show its own "unavailable" message while the others still load, so that one failure doesn't break the whole page.
73. As a collector, I want the app to fail fast during an outage instead of making me wait on every card, so that the site stays responsive when TCGdex is down.
74. As a collector, I want a tidy placeholder showing the card name and number when a card image can't load, so that my collection is still readable without images.
75. As a collector, I want the search filter dropdowns to show the unavailable message if their choices can't be loaded, so that I'm not left with empty or broken controls.

### The app's own API

76. As a developer writing another program, I want to authenticate with a personal API token sent in the request header, so that my program can access my data without a browser login.
77. As a signed-in user, I want to view my API token on the Account page, so that I can use it in another program.
78. As a signed-in user, I want to regenerate my API token, so that I can cut off a token that may have leaked.
79. As a signed-in user exploring the API in a browser, I want my website session to authenticate me in the browsable API, so that I can try endpoints without copying my token.
80. As an API client, I want to list my collection entries with pagination, so that I can read my whole collection in chunks.
81. As an API client, I want to filter and sort the collection list with the same options as the website (search, set, rarity, variant and ordering), so that my program can find specific entries.
82. As an API client, I want to create a collection entry by sending a TCGdex card ID, a variant, a quantity and optional notes, so that my program can save cards using IDs it gets from TCGdex.
83. As an API client, I want the create response to include the full card details, the price and any wish it fulfilled, so that my program knows exactly what happened.
84. As an API client, I want creating an entry to follow the same rules as the website (valid variants only, automatic wish fulfillment), so that data is consistent however it was entered.
85. As an API client, I want a clear validation error when I send an unknown card ID or a variant that card doesn't have, so that I can fix my request.
86. As an API client, I want a 503 response with a helpful message when TCGdex is unavailable and the card isn't stored locally yet, so that my program knows to try again later.
87. As an API client, I want to update an entry's quantity and notes, so that my program can keep records current.
88. As an API client, I want setting quantity to zero to delete the entry, so that the API behaves like the website's stepper.
89. As an API client, I want to delete a collection entry, so that my program can remove cards.
90. As an API client, I want to list, create, update (notes) and delete wishlist entries, so that my program can manage my wishlist too.
91. As an API client, I want any entry that belongs to another user to return "not found", so that the API never reveals or changes other users' data.
92. As an API client, I want requests without a valid token or session to be rejected, so that the API is never open to the public.

## Implementation Decisions

### Stack and project setup

- Python 3.14 managed with uv; Django; SQLite; Tailwind CSS with DaisyUI through django-tailwind-cli; HTMX for partial page updates; Ruff for linting and formatting; pytest with pytest-django for tests.
- One Django project named `pokedex`, split into four apps:
  - **accounts:** the custom user model, sign-up, the Account page and API token management.
  - **catalog:** the TCGdex client, the Card and CardVariant models, and the search page.
  - **collection:** the OwnedCard and Wish models, the collection and wishlist pages, and a shared services module that holds the business rules.
  - **api:** the Django REST Framework serializers, views and routing.
- Configuration is "deploy-ready" from the start. The secret key, debug flag and allowed hosts come from environment variables, loaded locally from a `.env` file that is excluded from git.
- Django's **database cache** backend stores cached search results, card details and the outage flag in SQLite. It behaves the same in development and in any later deployment, and it survives server restarts.

### Data model

- **User:** a custom user model that extends Django's AbstractUser, created at project start. Email is required and unique but not verified yet. Users sign in with their username.
- **Card:** one row per TCGdex card, shared by all users. It stores the TCGdex card ID (for example `sv03.5-025`), name, set ID and set name, series, rarity, local card number and the base image URL. Card rows are created the first time any user saves the card, and they are kept even when no one references them any more, so they also act as a cache.
- **CardVariant:** one row per card and variant, unique on that pair. The variant is one of five fixed choices: Normal, Reverse holo, Holo, 1st Edition, W Promo. Each row stores a nullable market price (a decimal in USD, never a float) and a price-updated timestamp. The set of CardVariant rows for a card is its list of allowed variants, so a separate allowed-variants field is not needed. Rows are created from TCGdex's simple per-card variant flags.
- **OwnedCard:** belongs to a user and points at one CardVariant. Stores a quantity (a positive whole number), optional notes (plain text, at most 500 characters) and created/updated timestamps. Unique on user and variant. The row is deleted when its quantity reaches zero.
- **Wish:** belongs to a user and points at one CardVariant, like OwnedCard. A user has at most one active wish per variant. Also stores optional notes (plain text, at most 500 characters), created timestamp, a fulfilled-at timestamp (empty while the wish is active) and an optional pointer to the OwnedCard row that fulfilled it.
- OwnedCard and Wish are deliberately separate models, because they have different fields (quantity versus fulfillment).
- Item condition (Mint, Near Mint and so on) is not tracked, because it cannot affect price with the available data.

### Business rules (shared services module)

All rules live in one services module that both the website views and the API call, so the two always behave the same.

- **Adding a copy:** look up or create the Card and its CardVariants, fetching from TCGdex if the card is new locally. Reject variants that the card doesn't have. Add one to the quantity of the user's OwnedCard row for that variant, creating the row if needed.
- **Wish matching:** after an add, find the user's active wish for the same variant. If there is one, mark it fulfilled: set the fulfilled-at timestamp and link it to the OwnedCard row. Only one wish is fulfilled per copy added.
- **Removing a copy ("−"):** subtract one from the quantity and delete the row at zero. If any wish was fulfilled by that OwnedCard row, restore the one fulfilled most recently by clearing its fulfilled-at timestamp and link.
- **Keep it on my wishlist:** clear the wish's fulfilled-at timestamp and link. The copy stays.
- **Dismiss (OK):** delete the fulfilled wish.
- **Got it (from the wishlist):** add a copy of the wished variant. This goes through the same add-and-fulfill logic.
- **Variant data:** use TCGdex's simple flags only (normal, reverse, holo, firstEdition, wPromo). The detailed variant data (stamps, foils, subtypes) is ignored.

### TCGdex client

- A single client module is the only code that talks to TCGdex. It covers card search, card detail, the set list, the series list and the rarity list.
- Every request uses a 3-second connect timeout and a 5-second read timeout. There are no automatic retries.
- **Circuit breaker:** any failure (timeout, connection error, server error, malformed response) stores a "TCGdex down" flag in the cache for 60 seconds. While the flag is set, every automatic client call fails immediately with a provider-unavailable error and makes no network request. After the flag expires, the next call tries the network again.
- **User retries:** a retry the user asks for (a Retry or "Try now" button) sends one real request even while the flag is set. If it succeeds, the flag is cleared for everyone; if it fails, the 60-second wait starts again. One click costs at most one failed request.
- The client raises its own small set of exceptions, for example "provider unavailable" and "not found". Views and the API turn these into user-facing messages or HTTP 503 and 404 responses.
- Image URLs from TCGdex have no file extension. The app adds the low-quality webp suffix for tiles and the high-quality one where a larger image is shown.

### Search page

- The search form has a name text box and two dropdowns, set and rarity. Set options are grouped by series under headings, newest series first. Rarity options are alphabetical. The set, series and rarity lists come from TCGdex and are cached for 24 hours.
- **Rule #1:** at least one filter is required. An empty submission shows a "Pick a name, set or rarity to start" message and makes no API call.
- **Pagination:** for each distinct filter combination, the app fetches the full list of matching card IDs from TCGdex once and caches it for 24 hours. The list contains only ID, name and image, so it is small; a name search for "pikachu" was about 23 KB. The app then paginates this list itself, which gives a total count and numbered pages. Very broad searches (rarity-only "Common" was about 1.1 MB, around 1.2 s) are slow only the first time they run.
- An HTMX loading indicator shows while a search request is in flight.
- **Tiles:** each result tile renders the image and name immediately. Its lower half (set, rarity, variant dropdown, price, Add button or stepper, wishlist badges, owned summary) loads through a separate HTMX request triggered on load. That request returns the card detail, cached for 24 hours.
- When a tile's detail fetch succeeds for a card that is already stored locally, the stored card data and variant prices are updated in the same step. This is the automatic price refresh.
- If a tile's detail request fails, only that tile shows "Details unavailable" with a countdown to when the circuit breaker closes, then retries by itself; a "Try now" link retries at once. A banner above the results counts the failed tiles, shows the same countdown and offers "Retry all now", which checks TCGdex with one tile and retries the rest only if that works. If the search request itself fails, the page shows the provider-unavailable message with a Retry button.
- **Stepper:** add, "+" and "−" requests swap only that tile's lower half through HTMX. The returned fragment includes the updated count, the owned-variants summary and a short confirmation. When a wish was fulfilled, the confirmation says so and links to the wishlist page.
- **Variant dropdown:** changing it re-requests the tile's lower half for that variant, so the price and owned count follow the selection. A card with only one variant has its variant preselected and fixed.
- Search results do not create Card rows. Rows are created only when a user saves a card to their collection or wishlist.

### Collection and wishlist pages

- These pages run entirely on local data and work while TCGdex is down.
- The collection lists one entry per OwnedCard row (card plus variant).
- **Collection sort options:** name, price, value (price × quantity, computed in the database query), quantity and date added, ascending or descending. The default is date added, newest first. Entries with no price sort last when sorting by price or value.
- **Search and filters:** the search box matches card name or notes (case-insensitive contains). The set, rarity and variant dropdowns list only values present in that user's own rows.
- Pagination uses Django's paginator at 24 per page with numbered pages. The current filters and sort are kept in the query string across pages.
- The wishlist page uses the same controls. Its sort options are those that apply to wishes (name, date added and price).
- The wishlist page shows active wishes with a "Got it" button and fulfilled-but-not-dismissed wishes crossed out with a "Got it" badge, the fulfilled date, and "Keep it on my wishlist" and "OK" buttons.
- The navigation shows the count of active wishes, plus a separate badge for fulfilled wishes awaiting dismissal.
- **Collection value:** the total of price × quantity for the user's rows, computed with a database aggregate. It is shown with the count of entries that have no price, and the oldest "as of" date among the stored prices.
- **Refresh prices:** a button on the collection page refreshes the stored prices for every card the user owns, one detail call per distinct card. It reports progress through HTMX ("Refreshing 12 of 40…"). It stops and shows the unavailable message if the circuit breaker trips, and keeps all existing prices.
- Notes are edited inline (HTMX) or through a small form on both pages. They are plain text with a 500-character limit enforced by validation.
- **Images:** card images link directly to TCGdex's image server. When an image fails to load, a placeholder showing the card name and number is displayed instead.

### Accounts

- Django's built-in authentication views handle sign-in, sign-out and password change.
- A sign-up view uses a form based on Django's user creation form, extended with the required, unique email field.
- The Account page lets the user edit their username and email (with uniqueness validation), links to password change, and shows the API token with a "Regenerate token" action.
- Every collection, wishlist, account and card-management view requires sign-in. Every query is scoped to the signed-in user. Requesting another user's object returns 404.

### The app's own API

- Built with Django REST Framework. DRF's token authentication (one token per user) and session authentication are both enabled. Session authentication makes the browsable API usable while signed in on the website.
- **Resources:** a collection endpoint and a wishlist endpoint. Each supports list, create, retrieve, partial update and delete.
- **Collection create** accepts a TCGdex card ID, a variant, a quantity (default 1) and optional notes. It goes through the shared services module, so it fetches the card from TCGdex when it isn't stored locally, validates the variant and fulfills matching wishes. The response includes nested card details, the variant, quantity, market price, price-updated time, notes and the fulfilled wish (or null).
- **Wishlist create** accepts a TCGdex card ID, a variant and optional notes.
- **Partial updates** may change only quantity and notes on collection entries, and only notes on wishes. Changing a variant requires deleting and re-creating the entry. Setting a collection entry's quantity to zero deletes it.
- **List endpoints** are paginated and support the same search, set, rarity, variant and ordering options as the web pages.
- Every endpoint is limited to the requesting user's own rows. Other users' IDs return 404, and unauthenticated requests are rejected.
- **Errors:** a 400 with field errors for invalid input (unknown card ID, unsupported variant, note too long, invalid quantity). A 503 with a provider-unavailable message when TCGdex is down and the card isn't stored locally.

### Testing approach

- pytest with pytest-django. Every TCGdex call is faked with the `responses` library, so tests never reach the real API.
- **Key behaviors to test:**
  - Wish matching on the exact variant, and wrong-variant non-fulfillment.
  - "−" restoring the most recently fulfilled wish.
  - Quantity-zero deletion on both the website and the API.
  - "Keep it on my wishlist" and "OK".
  - The circuit breaker: one failure sets the flag, and calls fail fast until it expires.
  - Timeout handling.
  - Rule #1 empty-search rejection.
  - Pagination of cached ID lists.
  - Collection value, including no-price entries.
  - Owner-only access returning 404, on both the website and the API.
  - API token authentication, and API create returning 503 when TCGdex is down.
  - Variant validation.
  - Note length validation.

## Out of Scope

- **Public sharing** of collections or wishlists, including viewing other users' collections and copying other users' cards into a wishlist. This was removed from the requirements.
- **Email verification and password-reset emails.** Emails are collected and unique, so either can be added later, but neither is built now.
- **Social login** (Google, GitHub) and JWT or expiring API tokens.
- **"Any variant" wishes.** Every wish names a specific variant (removed 2026-11-15).
- **Card condition** (Mint, Near Mint, and so on) and any condition-based price adjustment.
- **Detailed variants** such as stamps, foil patterns and print subtypes (for example "shadowless" or "1st-edition stamp"). Only the five simple variant types are supported.
- **Cardmarket (EUR) prices, currency conversion** and mixing currencies.
- **Storing or downloading card images** locally. Images are hotlinked with a placeholder fallback.
- **Caching the whole TCGdex catalog locally** or searching it offline. Catalog search requires TCGdex to be available.
- **A pass-through card search endpoint** in the app's own API. The API covers saved entries only.
- **Scheduled background price refreshes** (cron, Celery).
- **Sorting by set release date** or by card number within a set.
- **Type-ahead or autocomplete** search inputs. Plain dropdowns are used; type-ahead is a possible later upgrade.
- **A price-range filter** on the collection page.
- **Profile extras** such as a display name, bio, favorite Pokémon or avatar upload.
- **Production deployment** itself. The app is built deploy-ready, but choosing and configuring a host is not part of this PRD.
- **Supporting languages** other than English card data.

## Further Notes

- **Requirement mapping (numbering as in `project-idea.md` after public sharing was removed):**

  | # | Requirement | Covered by user stories |
  |---|---|---|
  | 1 | Collection | 25–31, 46 |
  | 2 | Wishlist | 32–45 |
  | 3 | Filter the collection | 50–54 |
  | 4 | Catalog search | 9–15 |
  | 5 | TCGdex | 9–20 |
  | 6 | Works offline | 56, 74 |
  | 7 | Edit own information | 6–7, 57–60 |
  | 8 | Browse, sort and paginate locally | 46–56 |
  | 9 | Sign-in and ownership | 1–8, 91–92 |
  | 10 | Own API | 76–92 |
  | 11 | Failure handling | 69–75, 86 |
  | 12 | Prices and value | 61–69 |

- **Facts verified against the live TCGdex API on 2026-11-12 and 2026-11-14:**
  - No API key is required.
  - Search results contain only ID, local ID, name and image. Set, rarity, variants and prices come only from the card detail endpoint.
  - Filters are contains matches by default, including `set.id` and `rarity` (`set.id=sv03` also returns `sv03.5`). Prefixing the value with `eq:` makes it an exact match (checked 2026-11-15).
  - Pagination parameters work, but responses include no total count.
  - There are 221 sets in 21 series, 44 rarities and about 23,900 cards.
  - Every sampled card had variant flags.
  - TCGplayer per-variant prices (normal, reverse-holofoil, holofoil) are present on most cards but missing on some, for example the 1st Edition Base Set Charizard.
  - A brief real outage ("no available server") was observed during design. This confirmed that the failure handling is needed.
- **Known data caveats:** TCGdex variant flags may sometimes be wrong. For example, `xy1-1` Venusaur EX is listed as Normal only. A "my variant isn't listed" fallback could be added later if this becomes a problem.
- **Unverified:** TCGdex's image licensing and hotlinking terms are not published on its assets page. This is one reason images are hotlinked rather than copied.
- **Prototypes from design** are in the `prototypes/` folder and are throwaway: the collection/wishlist data-model comparison, the wish-fulfilled notice placements, and the add-from-anywhere page with the stepper. The final design differs from them in places. For example, condition was removed after the prototypes were built, and the Undo link was replaced by the stepper.
- **Upgrade paths:**
  - Email verification can be added with Django's token generator or django-allauth.
  - Local image storage can be added as a self-contained change.
  - Type-ahead set search can replace the set dropdown without backend changes.

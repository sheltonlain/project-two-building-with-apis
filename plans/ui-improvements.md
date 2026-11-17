# Plan: UI Improvements

> Source PRD: `prd/ui-improvements.md` (follow-up to `prd/pokedex-card-collection.md`; this one wins where they differ)

## Architectural decisions

Durable decisions that apply across all phases:

- **URLs**:
  - `/card/<card_id>/` → `catalog:card_detail`, the new card detail page (TCGdex card ID, e.g. `sv03.5-025`; no pk).
  - `/card/<card_id>/add/`, `/card/<card_id>/remove/`, `/card/<card_id>/wish/` → the detail page's actions. POST `variant`; each returns the detail page's variants section.
  - `/` → `home` stays at the same path and name. It becomes a view (public) instead of a bare template.
  - Existing notes URLs (`collection:entry_notes`, `collection:entry_notes_delete`, `collection:wish_notes`, `collection:wish_notes_delete`) are reused from the detail page. They learn to respond to it rather than gaining new URLs.
  - `collection:wish_keep` is reused by the toast's Keep on wishlist. `collection:wish_dismiss` (OK) is removed.
  - Search keeps its existing query parameters (`name`, `set`, `rarity`, `page`). The typeable filters submit exactly the same values.
- **Models**: no new models, fields or migrations. A fulfilled wish (fulfilled-at set) is simply never shown on the website. "Hidden" means "fulfilled". Fulfilled rows keep their link to the OwnedCard, so "−" still restores them.
- **Owning app**:
  - **catalog:** the card detail page and its actions, the home view, and the TCGdex client's new "newest main expansion" lookup (set detail cached for 24 hours).
  - **collection:** the wishlist and nav changes, toast responses from collection actions, and detail-page awareness in the notes actions.
  - All business rules stay in the shared services module.
- **Auth**: the card detail page and its actions require sign-in. Home is public. Signed-out clicks from the home page reach sign-in through the normal login-required redirect with `next`. Every user-owned query stays scoped to the signed-in user (other users' items are 404).
- **TCGdex**:
  - All calls go through the TCGdex client and the circuit breaker.
  - Automatic retries are ordinary requests (no `X-User-Retry`), timed from `outage_seconds_left()` plus a random spread. Retry buttons send `X-User-Retry: 1`.
  - Tests fake every TCGdex call with `responses`.
- **Front end**:
  - HTMX for partial updates. One small dependency-free script provides the typeable filters, as an enhancement of a real `<select>` that is opted in by an attribute.
  - Toasts arrive as out-of-band swaps into a single toast container in the base layout and live only in the page.

---

## Phase 1: Search auto-retry

**User stories**: 1, 2, 3, 4, 5, 6

### What to build

When a search fails because TCGdex is unavailable, the search panel shows the warning with a countdown ("Trying again in Ns…") plus the existing Retry button. When the countdown reaches zero, the panel re-submits the search form as it currently stands, so text typed while waiting is kept. This swaps the panel like a normal search but replaces the current history entry instead of pushing one. A failure loading the Set/Rarity lists behaves the same way. The delay comes from the outage flag's remaining seconds plus a small random spread, matching the tiles.

### Acceptance criteria

- [x] A provider-unavailable search response includes a retry delay, and the page shows a live countdown next to Retry.
- [x] At zero, the form is re-submitted automatically with its current values and without the user-retry header.
- [x] An automatic retry doesn't add a browser history entry, so Back still returns to the previous page.
- [x] Failed Set/Rarity lists show the same countdown and retry. Chosen set and rarity values are kept across the retry.
- [x] Retry still sends `X-User-Retry: 1` and works while the breaker is open.
- [x] Error text follows the project's style: what happened and what to try next.
- [x] Tests cover the retry delay in the failure response and the absence of probing on automatic retries.

---

## Phase 2: Typeable Set and Rarity filters (search, collection, wishlist)

**User stories**: 7, 8, 9, 10, 11, 12, 13, 14

### What to build

A small script that turns an opted-in `<select>` into a combobox. Typing filters options with a case-insensitive contains match. Series (optgroup) headings show only above matching sets. Arrow keys move, Enter chooses, Escape closes and restores the current value, and the "Any set" / "Any rarity" option is always available. The real select stays in the form and is what gets submitted, and without JavaScript the plain select shows. It initializes on page load and on every HTMX swap, so the search panel (swapped and history-restored) keeps working. It's applied to Set and Rarity on the search, collection and wishlist pages. Variant and Sort stay plain.

### Acceptance criteria

- [ ] Typing "151" in the search page's Set filter shows the 151 set under its series heading. Non-matching series headings are hidden.
- [ ] Rarity filters the same way.
- [ ] Choosing an option and submitting produces the same URL as the plain select did.
- [ ] The current choice shows on page load, after an HTMX swap, and after Back (history restore).
- [ ] Full keyboard use works and follows the ARIA combobox/listbox pattern.
- [ ] With JavaScript disabled, the plain selects work.
- [ ] Collection and wishlist Set and Rarity filters behave the same. Variant and Sort are unchanged.

---

## Phase 3: Card detail page (read-only)

**User stories**: 25, 27, 28, 29, 38, 39

### What to build

A new sign-in-required page at `/card/<card_id>/`.
- **Shows:** a large image, the card's name, number, set and rarity, and every variant with its market price and price date.
- **Data:** the cached card detail. Opening the page refreshes the stored Card when one exists, the same as tiles.
- **When TCGdex is unavailable:** if the card is stored locally, the page draws from the stored Card with a note that prices may be out of date. If it isn't stored, the page shows an unavailable message with an auto-retry countdown and a Retry button.
- **Unknown card ID:** a not-found page.

Search tiles link the image and name to this page (links keep `hx-boost="false"`).

### Acceptance criteria

- [ ] Signed-in users see the card's image, name, number, set, rarity and per-variant prices and dates. Signed-out users are redirected to sign in with `next`.
- [ ] A stored card is shown from the database when TCGdex is down, with the out-of-date note.
- [ ] An unstored card shows the unavailable message with a countdown and Retry when TCGdex is down.
- [ ] An unknown ID returns 404 with a friendly page.
- [ ] Search tile images and names open the detail page as a full page load. Tile buttons still work in place.
- [ ] Tests fake TCGdex for the success, outage (stored and unstored) and not-found cases.

---

## Phase 4: Detail page owned and wished status, with actions

**User stories**: 30, 31, 32, 33, 34

### What to build

Each variant row on the detail page shows how many the user owns, with Add or a "− N owned +" stepper, and whether it's on their wishlist, with Add to wishlist.
- **Actions:** POST to the detail page's add, remove and wish URLs, call the same shared services as the search tiles, and swap only the variants section. After an action, the section is drawn from the stored Card, so it doesn't depend on TCGdex.
- **Confirmations, errors and the nav count** behave as on the tiles. Adding when TCGdex is unavailable shows the usual message and retry.
- **Links:** "View in my collection" and "View on my wishlist" appear when the user has matching entries, and link to those pages filtered to this card.

### Acceptance criteria

- [ ] Owned counts and wishlist status are correct per variant and scoped to the signed-in user.
- [ ] Add, "+", "−" and Add to wishlist update the variants section in place and update the nav's active-wish count.
- [ ] "−" removing the last copy deletes the entry and restores any wish it fulfilled, as everywhere else.
- [ ] An unsupported variant shows the existing error, and an outage shows the existing message and retry.
- [ ] Collection and wishlist links appear only when relevant, and open the filtered pages.
- [ ] Tests cover each action, user scoping and the outage path.

---

## Phase 5: Detail page notes

**User stories**: 35, 36, 37

### What to build

Each variant row shows the note on the user's collection entry for that variant (when owned) and on their active wish for it (when wished). Each has Add/Edit/Delete note controls. The existing notes actions and form are reused, with the same rules (at most 500 characters, never blank, cleared only by Delete note). They learn when a request comes from the detail page. They then respond with just that note's area, and without HTMX they return to the detail page instead of the list page. When "−" removes the last copy, that entry's note controls disappear with it.

### Acceptance criteria

- [ ] Notes for owned variants and wished variants show on the detail page with the right controls.
- [ ] Adding, editing, cancelling and deleting a note swaps only that note's area. The rest of the page is unchanged.
- [ ] Blank and over-500-character notes show the existing validation errors in place.
- [ ] Without HTMX, saving or deleting returns to the detail page.
- [ ] The same actions still behave exactly as before on the collection and wishlist pages.
- [ ] Another user's entry or wish is a 404.

---

## Phase 6: Links from collection and wishlist

**User stories**: 23, 24, 26

### What to build

On collection and wishlist pages, each card's image and name link to its detail page. Steppers, Got it, Remove, Delete and notes controls sit outside the links and keep working in place.

### Acceptance criteria

- [ ] Clicking a collection entry's image or name opens its card's detail page.
- [ ] Clicking a wish's image or name opens its card's detail page.
- [ ] Every button and notes control on those cards still works without navigating.
- [ ] Links work after HTMX swaps of entries and of the wishlist body.

---

## Phase 7: Home page newest set

**User stories**: 15, 16, 17, 18, 19, 20, 21, 22

### What to build

The home page becomes a public view.
- **What it shows:** below the welcome banner, a "Newest set" section with the newest main expansion's name and release date, its first 12 cards (image and name, in card-number order) and a "See all N cards" button that opens search filtered to that set.
- **Picking the set:** the TCGdex client gains a lookup that takes the newest set from the cached set groups, skipping the TCG Pocket series and promo sets. Its detail (release date, card count) is cached for 24 hours. The cards come from the existing cached search by set.
- **Links:** cards link to the detail page. Signed-out visitors reach sign-in through the normal redirect and continue afterwards.
- **When TCGdex is unavailable:** the section shows a short message with an auto-retry countdown, and the rest of the home page renders.

### Acceptance criteria

- [ ] Signed-in and signed-out visitors see the newest main expansion's name, release date and first 12 cards.
- [ ] TCG Pocket and promo sets are never featured.
- [ ] "See all N cards" opens search filtered to that set, and card clicks open the detail page. Signed-out visitors are sent to sign in, then on to the target.
- [ ] The section's data is cached, so repeat home page loads don't call TCGdex.
- [ ] During an outage the home page still loads, with the section's message and retry.
- [ ] Tests fake TCGdex for the selection rules (Pocket/promo skipped), success and outage.

---

## Phase 8: Fulfilled-wish toast and wishlist cleanup

**User stories**: 40, 41, 43, 44, 45, 46, 47, 48, 49, 50

### What to build

**The toast:**
- The base layout gains a toast container.
- When a search tile Add/"+" or wishlist **Got it** fulfills a wish, the response includes a toast swapped out-of-band into that container. It names the card and variant and has **Keep on wishlist** and **✕**. Its buttons sit inside the toast and are vertically centered with its text.
- **✕** removes the toast in the browser. Reloading or leaving the page drops it.
- **Keep on wishlist** posts to the existing keep action. The toast becomes a short "Kept on your wishlist" confirmation, the nav's active-wish count updates out-of-band, and on the wishlist page the wishlist body refreshes.

**The wishlist and nav:**
- The wishlist shows active wishes only. The Got it section, fulfilled card styling, Keep and OK buttons on wish cards, the dismiss action and URL, and the fulfilled-wish nav badge and its context value are removed.
- Wishlist filter options and the "has wishes" check consider active wishes only.
- Search tile confirmations no longer say "That fulfilled a wish".

**Docs:** `CLAUDE.md` rules about the Got it section and Got it/Keep/OK are updated, and the new toast rule is added.

### Acceptance criteria

- [ ] Adding a wished variant from a search tile shows the toast on the search page. Adding a non-wished variant doesn't.
- [ ] Got it on the wishlist removes the wish from the list and shows the toast.
- [ ] Keep on wishlist makes the wish active again (or deletes the fulfilled one if an active wish already exists). It confirms in the toast and updates the nav count. On the wishlist page the wish reappears.
- [ ] ✕ closes the toast. After a reload, no toast shows and the fulfilled wish isn't on the wishlist.
- [ ] "−" on the copy that fulfilled a wish restores it to the wishlist after the toast is gone.
- [ ] The nav shows only the active-wish count. The dismiss URL no longer exists.
- [ ] The toast's buttons are inside the toast and centered with its text.
- [ ] Existing fulfillment, keep and restore tests are updated, and tests for Got it section and dismiss behavior are removed or replaced.
- [ ] `CLAUDE.md` reflects the new behavior.

---

## Phase 9: Toast on the other add points

**User stories**: 42

### What to build

The detail page's Add/"+" and the collection page's "+" include the same out-of-band toast when they fulfill a wish, with the same Keep on wishlist and ✕ behavior. The collection page's "+" confirmation no longer mentions the fulfilled wish, since the toast covers it.

### Acceptance criteria

- [ ] Adding a wished variant from the detail page shows the toast there.
- [ ] "+" on a collection entry that fulfills a wish shows the toast there.
- [ ] Keep on wishlist from either page restores the wish and updates the nav count. On the detail page, the variant's wishlist status updates too.
- [ ] Tests cover the toast on both add points.

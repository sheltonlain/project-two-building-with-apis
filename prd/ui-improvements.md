# PRD: UI Improvements (search retry, typeable filters, home catalog, card detail page, fulfilled-wish toasts)

Follow-up to the main PRD (`prd/pokedex-card-collection.md`). Where the two differ, this one wins. Source notes: `project-ui-idea.md`. Prototype: `prototypes/wish-fulfilled-warning.html` (variant B, "hidden" mode, was chosen).

## Problem Statement

Collectors using the Pokedex app run into several rough edges:

- When a search fails because TCGdex didn't respond, the search just stops with a Retry button. Card tiles already retry by themselves on a countdown, so this feels inconsistent, and the user has to keep coming back to press Retry.
- The Set dropdown lists every set TCGdex has, grouped by series. Finding one set, such as "151", means scrolling a very long list. The Rarity list and the collection and wishlist filters have the same problem on a smaller scale.
- The home page is a welcome banner and nothing else. It gives visitors no sense of the cards the app covers and no starting point for browsing.
- A card can't be opened anywhere. Cards on the collection and wishlist pages are summaries, with no page that shows everything about a card in one place: all variants and prices, and what the user owns and wants of it.
- After a wish is fulfilled, it waits in a "Got it" section on the wishlist, and a nav badge counts it, until the user presses OK or Keep. It feels like a chore: the user must clear a flag for something that already happened.

## Solution

- **Search retries on its own.** A failed search, or failed Set/Rarity lists, shows a countdown ("Trying again in Ns…") and tries again when it reaches zero, like a card tile does. A Retry button stays for trying right away.
- **Set and Rarity filters are typeable.** On the search, collection and wishlist pages, the user can type into the Set and Rarity filters to narrow the list. Typing "151" shows the set named 151 at once; the series headings stay as group labels.
- **The home page shows the newest set.** Below the welcome banner, a "Newest set" section shows the newest main expansion's name, release date and first 12 cards. A "See all N cards" button opens search filtered to that set. Everyone sees it; signed-out visitors are asked to sign in when they click a card or "See all".
- **Every card has a detail page.** Clicking a card's image or name on the home page, search results, collection or wishlist opens a page for that card. It shows a large image, set, rarity, card number and every variant with its price. For each variant it shows what the user owns and whether it's on their wishlist, with Add, "+", "−" and wishlist buttons, plus links to the card on the user's collection and wishlist pages.
- **A fulfilled wish is announced once, then leaves quietly.** When adding a copy fulfills a wish, a toast pops up on the page the user is on, saying which wish was fulfilled. Its buttons are **Keep on wishlist** and **✕**. The toast disappears when the user closes it, reloads or leaves the page, and the wish is off the wishlist from then on. The "Got it" section, its OK button and the fulfilled-wish nav badge are gone. Pressing "−" on the copy that fulfilled a wish still brings the wish back.

## User Stories

### Search retry

1. As a collector, I want a failed search to try again by itself after a short countdown, so that I don't have to keep pressing Retry while TCGdex is having trouble.
2. As a collector, I want to see how many seconds remain until the next try, so that I know the app is still working on it.
3. As a collector, I want a Retry button next to the countdown, so that I can try right away instead of waiting.
4. As a collector, I want the Set and Rarity lists to retry themselves the same way when they fail to load, so that the filters come back without my help.
5. As a collector, I want an automatic retry to use what's currently in the search form, so that it doesn't throw away a name I typed while waiting.
6. As a collector, I want automatic retries not to add extra entries to my browser history, so that Back still takes me to the page I was on before.

### Typeable filters

7. As a collector, I want to type part of a set's name into the Set filter and see only matching sets, so that I can find "151" without scrolling through every set.
8. As a collector, I want matching sets to stay grouped under their series heading, so that I can tell apart sets with similar names.
9. As a collector, I want to type part of a rarity's name into the Rarity filter and see only matching rarities, so that I can pick one quickly.
10. As a collector, I want the same typeable Set and Rarity filters on my collection and wishlist pages, so that every filter works the same way across the app.
11. As a collector, I want to use the typeable filters entirely from the keyboard (type, arrow keys to move, Enter to choose, Escape to close), so that I don't need a mouse.
12. As a collector, I want an "Any set" / "Any rarity" choice to stay available, so that I can clear a filter.
13. As a collector, I want the filter to show the set or rarity I already chose when the page loads or when I go Back, so that my search is never silently changed.
14. As a collector, I want the filters to still work as plain dropdowns if JavaScript doesn't load, so that I can always search.

### Home page catalog

15. As a visitor, I want the home page to show the newest Pokémon TCG expansion, so that I can see what the app covers before signing up.
16. As a collector, I want to see the newest set's name and release date, so that I know what I'm looking at.
17. As a collector, I want to see the first 12 cards of the newest set with their images and names, so that I can browse new cards right away.
18. As a collector, I want a "See all N cards" button that opens search filtered to that set, so that I can explore the full set and everything else in the catalog.
19. As a collector, I want to click a card in the newest-set section to open its detail page, so that I can see its prices and add it.
20. As a signed-out visitor, I want clicking a card or "See all" to take me to sign in and then on to where I was going, so that I don't lose my place.
21. As a collector, I want the featured set to be a main expansion rather than a TCG Pocket or promo set, so that the home page shows the physical cards I collect.
22. As a collector, I want the home page to still load when TCGdex is down, with a short message in place of the newest-set section, so that I can still reach the rest of the app.

### Card detail page

23. As a collector, I want clicking a card's image or name on my collection page to open that card's detail page, so that I can see everything about it.
24. As a collector, I want clicking a card's image or name on my wishlist to open that card's detail page, so that I can check its variants and prices.
25. As a collector, I want clicking a card's image or name in search results to open its detail page, so that I can see more than fits on a tile.
26. As a collector, I want buttons on collection and wishlist cards (−, +, Got it, Remove, notes) to keep working without opening the detail page, so that I don't open it by accident.
27. As a collector, I want the detail page to show a large image of the card, so that I can see it clearly.
28. As a collector, I want the detail page to show the card's name, number, set and rarity, so that I can identify exactly which card it is.
29. As a collector, I want the detail page to list every variant the card comes in with its market price and price date, so that I can compare variants.
30. As a collector, I want to see how many copies of each variant I own, so that I know what I already have.
31. As a collector, I want to see which variants are on my wishlist, so that I know what I'm hunting for.
32. As a collector, I want to add a copy, add one more ("+") or remove one ("−") for each variant from the detail page, so that I can update my collection while looking at the card.
33. As a collector, I want to add any variant to my wishlist from the detail page, so that I can wish for the exact version I want.
34. As a collector, I want links from the detail page to this card on my collection page and my wishlist page, so that I can jump to my entries and their notes.
35. As a collector, I want to see, add, edit and delete the note on my collection entry for each variant I own, right on the detail page, so that I don't have to find the card on my collection page first.
36. As a collector, I want to see, add, edit and delete the note on my wish for each variant I'm wishing for, right on the detail page, so that I can update why I want it while looking at the card.
37. As a collector, I want notes on the detail page to follow the same rules as everywhere else (at most 500 characters, can't be saved blank, cleared with a separate Delete note action), so that notes behave the same wherever I edit them.
38. As a collector, I want the detail page to still show a card I own or wish for when TCGdex is down, using the copy saved in the app, so that my own cards are always viewable.
39. As a collector, I want a clear "card not found" page for an unknown card ID, so that a bad link doesn't look like an outage.

### Fulfilled-wish toast

40. As a collector, I want a toast to appear on the page I'm on when adding a copy fulfills one of my wishes, so that I notice right away.
41. As a collector, I want the toast to name the card and variant whose wish was fulfilled, so that I know which wish it was.
42. As a collector, I want the toast to appear wherever I added the copy (a search tile, the card detail page, the "+" on my collection page or "Got it" on my wishlist), so that it works the same everywhere.
43. As a collector, I want a "Keep on wishlist" button in the toast, so that I can keep wishing for that variant (for example, to get a second copy).
44. As a collector, I want to close the toast with ✕, so that I can get it out of the way.
45. As a collector, I want the toast to go away by itself when I reload or leave the page, so that I never have to dismiss anything.
46. As a collector, I want a fulfilled wish to leave my wishlist once the toast is gone unless I chose Keep, so that my wishlist only shows what I still want.
47. As a collector, I want the toast's buttons to sit neatly inside the toast, lined up with its text, so that it looks finished.
48. As a collector, I want the wish to come back automatically when I press "−" on the copy that fulfilled it, even after the toast is gone, so that undoing an accidental add also restores my wishlist.
49. As a collector, I want the nav to show only my count of active wishes, so that there's nothing extra to review.
50. As a collector, I want pressing "Got it" on my wishlist to move the card into my collection, take it off the list, and show the toast, so that I can still choose to keep wishing for it.

## Implementation Decisions

### Search auto-retry

- When the search request or the Set/Rarity lists fail with a provider-unavailable error, the search panel gives a retry delay: the outage flag's remaining seconds plus a small random spread, the same calculation tiles use.
- The panel shows a countdown and, when it reaches zero, re-submits the search form as it currently stands (so newly typed text is kept), swapping the panel as a normal search does. Automatic retries are ordinary requests (no user-retry header), so they never probe an open circuit breaker. They replace the current history entry rather than pushing a new one.
- The existing Retry button stays and still sends the user-retry header (`probe=True`).
- The countdown script lives with the search page's existing tile-countdown script and survives HTMX swaps of the panel.

### Typeable Set and Rarity filters

- A small, dependency-free "combobox" script enhances an ordinary `<select>`: the select stays in the form (visually hidden) and is what gets submitted, so URLs, query parameters and server code do not change. Without JavaScript, the plain select is shown.
- Matching is a case-insensitive "contains" on the option's label. For Set, the series (optgroup) heading is shown above any matching sets and hidden when none match.
- It follows the ARIA combobox/listbox pattern: arrow keys move, Enter chooses, Escape closes and restores the current value, and a clear option ("Any set" / "Any rarity") is always present.
- It enhances any select marked with an opt-in attribute and re-initializes on HTMX swaps, so the search panel's selects (which are swapped and restored from history) keep working.
- Applied to Set and Rarity on the search, collection and wishlist pages. Variant and Sort stay plain selects.

### Home page newest-set section

- The home page becomes a view rather than a bare template. It is public; the newest-set section shows for everyone.
- The TCGdex client gains a function that picks the newest main expansion: the newest set in the cached set groups, skipping the TCG Pocket series and promo sets. It returns the set's ID, name, release date and card count (from the set's detail, cached for 24 hours like the other options).
- The section's 12 cards come from the existing search by set (cached for 24 hours), in card-number order. Tiles show image and name only. No per-tile details are loaded.
- Card links go to the card detail page and "See all N cards" goes to search filtered by the set. Both require sign-in, so signed-out visitors are sent to sign in (with `next`) by the usual login-required redirect.
- If TCGdex is unavailable, the section shows a short message with the same auto-retry countdown as search. The rest of the home page renders normally.

### Card detail page

- A new page in the catalog app at `/card/<card id>/`, requiring sign-in.
- Data comes from the cached card detail. If TCGdex is unavailable but the card is stored locally (the user owns or wished for it), the page shows the stored card with a note that prices may be out of date. If neither is available, it shows an "unavailable" message with an auto-retry countdown. An unknown card ID returns a not-found page.
- Opening the page refreshes the stored card from the detail, the same automatic refresh tiles do.
- Each variant row shows its price and price date, the user's owned count with Add, or a "− N owned +" stepper, and its wishlist status with an "Add to wishlist" button. The actions call the same shared services as the search tiles and swap only the variants section through HTMX. As with tiles, after an action the section is drawn from the stored Card.
- **Notes:** each variant row shows the note on the user's collection entry for that variant (when they own it) and on their active wish for it (when they wish for it). Each note has the same add/edit/Delete note controls as the collection and wishlist pages, with the same rules (at most 500 characters, never saved blank, cleared only by Delete note). The existing entry and wish notes actions (and their form, validation and user scoping) are reused, but today they respond with the whole collection or wishlist card and, without HTMX, redirect to that list page. They gain a way to know the request came from the detail page. Then they respond with just that note's area on the detail page, and the no-HTMX fallback returns to the detail page. After a note action, only that note's area is swapped. The rest of the page is unchanged. When "−" removes the last copy, or a wish is fulfilled, that note's controls disappear with the entry, just as on the other pages.
- "View in my collection" and "View on my wishlist" link to those pages filtered to this card. They appear only when the user has a matching entry.
- Links to the detail page are added to the image and name of: collection entries, wishlist entries, search tiles and the home page's newest-set cards. Action buttons, steppers and notes controls are not inside the link. Links inside search tiles keep `hx-boost="false"` so they open full pages.

### Fulfilled-wish toast

- **Model behavior:** a fulfilled wish (its fulfilled-at timestamp is set) is no longer shown on the wishlist at all. "Hidden" simply means "fulfilled": no new field or migration is needed. The fulfilled row and its link to the OwnedCard are kept, so "−" on that copy restores the wish exactly as today.
- **Toast:** any HTMX response for an add that fulfilled a wish includes a toast fragment, swapped out-of-band into a toast container in the base layout. The toast names the card and variant and has a "Keep on wishlist" button and a ✕ button. Toasts live only in the page. Reloading or leaving the page drops them, and ✕ removes one in the browser without a request.
- **Where adds happen:** search tile Add/"+", card detail page Add/"+", collection page "+", and wishlist "Got it". Each of these responses includes the toast when a wish was fulfilled.
- **Keep on wishlist:** posts to the existing keep action (the wish becomes active again; if an active wish for that variant already exists, the fulfilled one is deleted instead). The toast is replaced by a short "Kept on your wishlist" confirmation. The nav's active-wish count updates out-of-band, and on the wishlist page the wishlist body is refreshed so the kept wish reappears.
- **Layout:** the toast's buttons sit inside the toast and are vertically centered with its text, unlike the prototype.
- **Wishlist page:** shows active wishes only. The "Got it" section, the fulfilled wish card styling (crossed out, badge, fulfilled date), Keep and OK buttons on wish cards, and the dismiss (OK) action and its URL are removed. "Got it" still adds a copy through the shared add-and-fulfill logic. It re-renders the wishlist body (the wish leaves the list) and includes the toast.
- **Filters:** wishlist filter options and the "has wishes" check consider active wishes only.
- **Search tile notice:** the tile's confirmation no longer says "That fulfilled a wish" or links to the wishlist, since the toast covers it.
- **Nav:** only the active-wish count badge remains. The fulfilled-wish count badge and its context value are removed.
- **Existing data:** fulfilled wishes already waiting for OK in the database simply become hidden. No data migration is needed.

## Out of Scope

- **Sorting search results** (including by price). TCGdex search results don't include prices, so a price sort would mean fetching every matching card's details. Dropped.
- Featuring more than one set on the home page, or any home page pagination.
- Typeable Variant and Sort selects.
- A history of fulfilled wishes, or any way to see hidden fulfilled wishes on the website.
- Showing the toast for wishes fulfilled through the REST API.

## Further Notes

- `CLAUDE.md` rules that change with this PRD and must be updated during implementation:
  - "Wishlist actions that move a wish between sections (Got it, Keep, OK) re-render the whole wishlist body." There's only one section now. Got it and Keep still re-render the body, and OK is gone.
  - "Wishlist filters apply to the Got it section too…": the Got it section is gone.
  - Add: a fulfilled wish is hidden from the wishlist and announced once by a toast in the page where it was fulfilled.
- The main PRD's user stories 40–43 and 45 and its wishlist-page and nav decisions are replaced by this PRD's fulfilled-wish toast section. Story 44 ("−" restores the wish) is unchanged.
- Phase 14 (REST API) is not built yet. Its wishlist endpoint should list active wishes only, matching the website. The collection create response still reports any wish it fulfilled.
- Tests must keep faking TCGdex (no real calls), including the new set-detail request for the home page and the card detail page.

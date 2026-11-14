# Free External API Providers for a Search / Save / Notes / Ratings App

Research for CIDM 3312 "Project Two: Building with APIs" (Django). Compiled 2026-11-12.

**Method.** Every factual claim below comes from a primary source: the provider's own docs, terms, pricing or signup page, its official GitHub repo, or a live request to the API on 2026-11-12. Where the live site could not be reached, I used an Internet Archive snapshot of the provider's own page and say so. Third-party lists and blogs were used only to find candidates. Anything I could not confirm at a primary source is marked **UNVERIFIED**.

---

## 1. Summary and recommendation

### Pokemon pick: PokeAPI (with TCGdex as a strong second)

**PokeAPI** (https://pokeapi.co) is the best fit for a Pokemon app:

- No signup, no API key and no rate limit. The fair-use policy only asks you to cache locally. [1]
- Rich JSON data for every Pokemon, with sprite and official-artwork image URLs. [1][live]
- It is stable, and the static REST API has had no rate limiting since November 2018. [1]

There is one catch. **PokeAPI has no text-search endpoint.** You can look a Pokemon up by its exact name or ID, or page through a list with `limit` and `offset` (the edge firewall allows only those two query parameters). [1] The usual fix works well:

1. Fetch the full name list once, with `GET https://pokeapi.co/api/v2/pokemon?limit=2000`. On 2026-11-12 it returned all 1,351 entries in one response. [live]
2. Keep that list in the Django cache or in a small table, and refresh it daily. The API sends `Cache-Control: public, max-age=86400`. [live]
3. Do the search yourself with `icontains` or a Python filter.

This also satisfies the "cache locally" fair-use rule. [1]

**How the search / save / notes / ratings flow maps to PokeAPI:**

| App step | PokeAPI call / Django piece |
|---|---|
| Search box ("pika") | Filter the cached list from `GET /api/v2/pokemon?limit=2000` (`[{name, url}]`) by name; the ID is the last segment of `url`. [1][live] |
| Search result card | Build the image URL from the ID, or call the detail endpoint for a few results only. The sprite format is `https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/{id}.png`. [live] |
| Detail page | `GET /api/v2/pokemon/{name-or-id}` returns `id, name, height, weight, types, abilities, stats, sprites` (including `sprites.other["official-artwork"].front_default`). [live] Flavor text is at `GET /api/v2/pokemon-species/{id}`. [1] |
| Save to account | A `SavedPokemon` model with `user` (FK), `pokeapi_id`, `name`, `sprite_url` and `saved_at`, plus `unique_together(user, pokeapi_id)`. Copy the few fields you display, so list pages need no API calls. That is caching, which the fair-use policy requires. [1] |
| Notes / rating | Fields on `SavedPokemon` (`notes` TextField, `rating` 1-5 PositiveSmallIntegerField), or a separate `Note` model. The API stays read-only. PokeAPI is "consumption-only", GET only. [1] |

**Alternative Pokemon pick, TCGdex** (https://tcgdex.dev), if you'd rather work with **Pokemon cards**:

- It has real server-side search: `GET https://api.tcgdex.net/v2/en/cards?name=pikachu` does a case-insensitive "contains" match. That request returned 246 cards on 2026-11-12. [3][live]
- No API key, and it is free to use. [4]
- High-quality card images. [5]
- Card detail at `GET /v2/en/cards/{id}` includes `name, rarity, hp, types, attacks, set, illustrator, pricing` and more. [live]

The image URL in the response has no file extension. You append `/{low|high}.{webp|png|jpg}`, for example `.../swsh3/136/low.webp`. [5][live] The save / notes / ratings flow maps the same way, keyed on the card `id` (for example `swsh3-136`).

**Avoid the Pokemon TCG API (pokemontcg.io).** It is deprecated:

- New account registrations are closed, and existing keys work only "through March 1, 2027". [6]
- Its successor, **Scrydex**, has no free tier. Plans start at $29/month. [7]

### Non-Pokemon alternatives

1. **TVmaze** (TV shows), the easiest non-Pokemon option:
   - No key needed. [11]
   - True fuzzy search with `GET https://api.tvmaze.com/search/shows?q=...`. [11]
   - Images are included, and hotlinking is explicitly allowed. [11]
   - Limit of at least 20 calls per 10 seconds per IP. [11]
   - CC BY-SA license; a link back to TVmaze satisfies attribution. [11]
2. **TMDB** (movies and TV), the richest data:
   - Needs a free account and an API key, and you must accept the terms. [8]
   - Search with `GET /3/search/movie?query=...`; responses include `poster_path` and `backdrop_path`. [9]
   - Free for non-commercial use, with TMDB attribution and logo required. [10][10b]
   - Data may be cached for up to 6 months. [10b]

If a games topic is required, **IGDB** is now the only big, free, actively working general game database in this list (see the surprises below). It has a real `search` keyword and is free, but setup is harder: you need a Twitch account with 2FA and an OAuth client-credentials token. [14]

### Surprises and changes found

- **Giant Bomb API is offline.** Giant Bomb's own API page (archive snapshot of 2026-11-02) says that after separating from Fandom, the API endpoints for Games, Characters, Companies, People and more are "not currently available". [17] The live page was behind a bot challenge on 2026-11-12.
- **RAWG was unreachable on 2026-11-12.** `rawg.io/apidocs`, `rawg.io/tos_api` and `api.rawg.io/api/games` all returned Cloudflare HTTP 522 ("origin unreachable") on several tries. RAWG's own docs (archive snapshot of 2026-10-21) still list a free plan. [15][16] This may be temporary, but it is risky for a class project. **UNVERIFIED whether this is an outage or a shutdown.**
- **Pokemon TCG API (pokemontcg.io) is deprecated.** Registrations are closed and keys end March 1, 2027. Scrydex, its replacement, is paid only. [6][7]
- **Spotify Web API is effectively off-limits for student projects.** Since 11 Feb 2026, a new Development Mode app needs the owner to hold **Spotify Premium**. Apps are capped at 5 users, search `limit` max dropped from 50 to 10, and many endpoints and fields were removed. [27][28]
- **Edamam has no free plan anymore.** The cheapest Recipe Search plan is $9/month. [24]
- **TMDB terms ban AI/ML training use** and limit caching to 6 months (terms last updated 2023-10-20). [10b]

---

## 2. Comparison table

Legend: "Search" means a server-side text search by name or title. "Key" means a free API key from signup. CC stands for credit card.

| Provider | Topic | Auth / signup | Free limits | Text search | Images | Key caveats |
|---|---|---|---|---|---|---|
| **PokeAPI** | Pokemon (games data) | None [1] | No rate limit; fair use; cache locally [1] | **No.** Exact name/ID lookup plus `limit`/`offset` list [1] | Yes, sprites and official artwork on GitHub raw [live] | IP ban for fair-use violations; GraphQL beta limited to 100 calls/h [1][2] |
| **TCGdex** | Pokemon TCG cards | None, "free to use" [4] | "No published hard rate limits"; cache [4] | **Yes.** `?name=` contains-match [3] | Yes, high/low webp/png/jpg [5] | Not affiliated with Nintendo/TPC; DB is MIT licensed [18] |
| **Pokemon TCG API** | Pokemon TCG cards | Key; **new registrations closed** [6] | 20,000/day with key; 1,000/day and 30/min without [19] | Yes (per docs; **UNVERIFIED** detail) | Yes (**UNVERIFIED**) | **Deprecated**; keys end 2027-03-01 [6] |
| **Scrydex** | TCG (successor) | Paid account [7] | **No free tier**; $29/mo for 5,000 credits [7] | n/a | n/a | Paid only |
| **IGDB** | Video games | Twitch account + 2FA; OAuth client credentials [14] | 4 req/s; 8 open requests [14] | **Yes.** `search "Halo";` [14] | Yes, `images.igdb.com` [14] | Server-side only (no CORS) [14]; Twitch Developer Agreement [14] |
| **RAWG** | Video games | Key [15] | 20,000 req/month [15] | Yes (`search=`; **UNVERIFIED**, docs unreachable) | Yes (**UNVERIFIED**) | **Unreachable (522) on 2026-11-12**; active backlink required [15][16] |
| **Giant Bomb** | Video games | Key (historical) | n/a | Historically `/api/search/` [17b] | Historically yes | **API endpoints "not currently available"** [17] |
| **CheapShark** | PC game deals | None; descriptive User-Agent required [20] | Unpublished; 429 with temporary block [20] | **Yes.** `games?title=` [20] | Thumbnails (**UNVERIFIED** field) | Must use CheapShark deal links; no bulk catalog building [20] |
| **FreeToGame** | Free-to-play games | None [21] | Under 10 req/s [21] | **No.** Filters by platform/category/sort only [21] | Yes, `thumbnail` [live] | Attribution with active hyperlink required [21] |
| **TMDB** | Movies / TV | Account + key; accept terms [8] | About 40 req/s upper bound [8b] | **Yes.** `/search/movie?query=` [9] | Yes, `image.tmdb.org` [9b] | Non-commercial only; logo + disclaimer; cache up to 6 months; no AI training [10][10b] |
| **OMDb** | Movies | Key by email [12b] | 1,000/day free [12b] | **Yes.** `s=` [12] | Poster URLs **UNVERIFIED**; Poster API is patrons-only [12] | CC BY-NC 4.0 content [12] |
| **TVmaze** | TV shows | None [11] | At least 20 calls / 10 s / IP [11] | **Yes.** `/search/shows?q=` (fuzzy) [11] | Yes; hotlinking allowed [11] | CC BY-SA; link back to TVmaze [11] |
| **Open Library** | Books | None; `User-Agent` + email recommended [22] | 1 req/s (3 req/s if identified) [22]; covers 100 / 5 min / IP for non-ID keys [22c] | **Yes.** `search.json?q=` [22b] | Yes, covers API [22c] | No bulk downloads [22] |
| **Google Books** | Books | API key or OAuth token required as identifier [23] | Quota not stated on page (**UNVERIFIED** numbers) [23] | **Yes.** `volumes?q=` with `intitle:` [23] | Yes, `imageLinks` [23] | "Powered by Google" branding required; no charging users [23b][23c] |
| **Gutendex** | Public-domain books | None (not mentioned) [25] | Not published; the authors say "run your own server" [25][25b] | **Yes.** `?search=` [25] | Cover via `formats["image/jpeg"]` [live] | Project Gutenberg books only |
| **TheMealDB** | Recipes | Test key `1` for dev/education [26] | Not stated [26] | **Yes.** `search.php?s=` [26] | Yes, `strMealThumb` [26][live] | Must become a paid supporter to release publicly on an app store [26] |
| **Spoonacular** | Recipes | Account + key; no CC on own platform [29] | 50 points/day; 1 req/s [29] | Yes (**UNVERIFIED** endpoint) | Yes (**UNVERIFIED**) | Backlink required; cache 1 hour max [29] |
| **Edamam** | Recipes | Paid plan [24] | **No free plan**; from $9/mo [24] | n/a | n/a | Attribution required [24] |
| **MusicBrainz** | Music metadata | None for reads; meaningful User-Agent required [30] | About 1 req/s per IP [31] | **Yes.** `/ws/2/{entity}?query=` with `fmt=json` [32] | Not in core API (Cover Art Archive **UNVERIFIED**) | Non-commercial use is free [30] |
| **Deezer** | Music | None for public search [live] | **UNVERIFIED** | **Yes.** `api.deezer.com/search?q=` [live] | Yes (cover / `md5_image`) [live] | No storing audio; terms need login to accept [33][33b] |
| **Last.fm** | Music | API account / key [34] | Unpublished, "enforced" [35] | Yes, `artist.search` / `album.search` / `track.search` [34] | **No image rights** under the terms [35] | Non-commercial only; "powered by AudioScrobbler" attribution [35] |
| **Spotify** | Music | OAuth app; **owner needs Premium** [27] | 5 users per dev app; search max 10 per page [28] | Yes, `GET /search` [28] | Yes (**UNVERIFIED** in this pass) | 2026 restrictions; not recommended [27][28] |
| **Jikan** | Anime (MyAnimeList) | None | 3 req/s, 60 req/min [36] | Yes (`/anime?q=`; live test timed out) | Yes (**UNVERIFIED** field) | Unofficial scraper of MAL; 24h cache [36][37] |
| **Scryfall** | Magic cards | None; User-Agent + Accept headers required [38] | `/cards/search` 2/s; most others 10/s [39] | **Yes.** `/cards/search` [39] | Yes | No paywalling data; WotC Fan Content Policy [38] |
| **Open Food Facts** | Food products | None for reads; User-Agent [40] | 10 searches/min; 15 product reads/min [40] | Structured filters only; no full-text in v2 [40] | Yes (CC BY-SA) [40] | ODbL [40] |

---

## 3. Per-provider details

### 3.1 Pokemon

#### PokeAPI (https://pokeapi.co)

- **Data:** Pokemon, species, moves, abilities, types, items, berries, evolution chains, locations and more. All of it is JSON at `https://pokeapi.co/api/v2/`. [1]
- **Images:** `sprites.front_default` gives a GitHub raw URL such as `https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/25.png`. `sprites.other["official-artwork"].front_default` gives larger art. [live: `GET /api/v2/pokemon/pikachu`]
- **Search:** None. Named resources take `{id or name}`, and lists return 20 per page by default, paged with `limit` and `offset`. The edge firewall blocks malformed query strings, and "Only `limit` and `offset` parameters are allowed." [1] A single `?limit=2000` request returned all 1,351 Pokemon on 2026-11-12. [live]
- **Auth:** None. "All resources are fully open and available." Only GET, HEAD and OPTIONS are allowed. [1]
- **Rate limits / fair use:** Rate limiting was removed in November 2018 with the move to static hosting. Users should still "limit the frequency of requests" and "Locally cache resources whenever you request them." Breaking fair use can lead to a permanent IP ban. [1] Responses carry `Cache-Control: public, max-age=86400` and `Access-Control-Allow-Origin: *`. [live]
- **GraphQL (beta):** `https://graphql.pokeapi.co/v1beta2` is in beta, "subject to changes", and runs on a free-tier machine. It is rate limited to **100 calls/h per IP** and reboots daily around 1 AM UTC. [2] GraphQL could in principle do name filtering, but **UNVERIFIED**: the docs page does not say whether `_ilike` filters work. With a limit of 100/h, I would not build search on it anyway.
- **Terms / ownership:** The About page says "Pokémon and Pokémon character names are trademarks of Nintendo" and states no data license. It is community-run, and its data comes largely from Veekun. [1b]
- **Fit:** Excellent. Name search is done locally against a cached list. See section 1.

#### TCGdex (https://tcgdex.dev)

- **Data:** Pokemon TCG cards, sets and series in 10 languages. It also covers TCG Pocket and TCG Live, and has a markets/prices section. [13] Card detail includes `name, rarity, hp, types, attacks, weaknesses, set, illustrator, variants, pricing`. [live: `GET /v2/en/cards/swsh3-136`]
- **APIs:** REST (`https://api.tcgdex.net/v2/{lang}/...`) and GraphQL, plus official SDKs, including Python. [13][18]
- **Search:** `?name=abo` is a case-insensitive "laxist" contains-match. There are also `eq:`, `like:` and `not:` operators, numeric `gte`/`lte` comparisons, and pagination. [3] A request for `?name=pikachu` returned 246 results. [live]
- **Images:** `https://assets.tcgdex.net/{lang}/{serie}/{set}/{localId}/{quality}.{ext}`, where quality is `high` (600x825) or `low` (245x337) and ext is `png`, `webp` (recommended) or `jpg`. [5] The `image` field in API responses leaves out the `/{quality}.{ext}` suffix, so you must append it. [live]
- **Auth / cost:** "Requires no API key", "free to use." [4]
- **Rate limits:** "There are no published hard rate limits"; please cache responses locally. [4]
- **Terms:** The card database is MIT licensed, and the repo says it is "not produced, endorsed, supported or affiliated with Nintendo or The Pokémon Company." [18] Image licensing or hotlinking terms are **not stated** on the assets page. [5] The FAQ also notes the API is "costly to run" and asks for sponsorship. [13]
- **Fit:** Excellent for a card-collection app. Search, save and annotate map directly onto it.

#### Pokemon TCG API (pokemontcg.io) and Scrydex

- **Status:** The docs say "The Pokémon TCG API is deprecated. Please migrate your application to Scrydex." Existing keys work "through March 1, 2027", and "New account registrations are no longer available." [6] The pokemontcg.io homepage says the API "is now part of Scrydex". [6b]
- **Limits (legacy):** 20,000 requests/day with a key; 1,000/day and 30/min without one. [19]
- **Scrydex:** There is **no free tier**. Starter is $29/month for 5,000 credits, Growth is $99/month and Professional is $399/month. [7] Trial and credit-card details are **not stated**. [7]
- **Fit:** Poor. It is shutting down, and the replacement is paid.

### 3.2 Video games

#### IGDB (https://api-docs.igdb.com)

- **Signup:** You need a Twitch account with two-factor authentication. You register an app in the Twitch Developer Console (Client Type "Confidential", with `localhost` as the OAuth redirect) and generate a Client Secret. [14]
- **Auth:** `POST https://id.twitch.tv/oauth2/token?client_id=...&client_secret=...&grant_type=client_credentials` returns an `access_token` with an `expires_in` value. Every request then sends the `Client-ID` and `Authorization: Bearer` headers. Most requests are **POST** with an Apicalypse body sent to `https://api.igdb.com/v4/{endpoint}`. [14]
- **Search:** `search "Halo"; fields name,release_dates.human;` on `/games`. A separate `/search` endpoint covers characters, collections, games, platforms and themes. [14]
- **Images:** `https://images.igdb.com/igdb/image/upload/t_{size}/{image_id}.jpg`. [14]
- **Limits:** "4 requests per second", up to 8 open requests; going over returns 429. [14]
- **Terms:** "Free for non-commercial usage under the terms of the Twitch Developer Service Agreement." The FAQ also says the API "is free for both non-commercial and commercial projects", with commercial partners asked for attribution. Caching is welcome: "we prefer if you store and serve the data to your end users." [14]
- **Other:** Browsers get CORS errors, so it must be called from the server, which suits Django. The docs announce an "Enums to Tables" field migration with a 6-month window. [14]
- **Fit:** Good data and real search, but the most setup of any option here.

#### RAWG (https://rawg.io/apidocs)

- **Status on 2026-11-12:** `rawg.io/apidocs`, `rawg.io/tos_api` and `https://api.rawg.io/api/games?search=pokemon` all returned **HTTP 522** (Cloudflare cannot reach the origin). [live] The details below come from Internet Archive snapshots of RAWG's own pages.
- **Plans (snapshot of 2026-10-21):** Free is "For personal and hobby projects... Non-commercial projects only... up to 20,000 requests per month... Required backlinks to RAWG from pages where the data is used". Business is $149/month. [15]
- **Terms (snapshot of 2026-09-12):** The free plan requires that "you attribute RAWG as the source of the data and/or images and add an active hyperlink from every page where the data of RAWG is used". It is limited to sites with at most 100,000 MAU or 500,000 page views per month. "No data redistribution." [15][16]
- **Search / images:** The docs page shows `GET https://api.rawg.io/api/games?key=YOUR_API_KEY`. The `search=` parameter and the `background_image` field are **UNVERIFIED** in this pass because the live docs were down.
- **Fit:** It would be good if it were up, but availability today is uncertain. Avoid it unless it is confirmed working.

#### Giant Bomb (https://www.giantbomb.com/api/)

- **Status:** On Giant Bomb's own API page (snapshot of 2026-11-02), Giant Bomb says that after the move to independence from Fandom, "the mechanisms by which one could access them are not currently available, and they will change. ... Not currently available are any of the APIs for: Games, Characters, Companies, Concepts, Locations, Objects, Releases, People". [17] The live page served a bot challenge (HTTP 403) on 2026-11-12. [live]
- **Historical:** The documentation (snapshot of 2025-11-28) listed a `/api/search/?api_key=...` endpoint with xml, json or jsonp output and image fields. [17b]
- **Fit:** Not usable right now.

#### CheapShark (https://apidocs.cheapshark.com)

- **Data:** PC game deal prices across Steam, GreenManGaming, Fanatical and other stores. [20]
- **Auth:** "No authorization or API Key is needed." You must send a descriptive `User-Agent`, for example `MyApp/1.0 (contact@example.com)`. [20]
- **Search:** `GET https://www.cheapshark.com/api/1.0/games?title=batman`; lookup with `games?id=612`. [20]
- **Limits:** Not published. Too many requests get a 429 and a temporary block, and bulk catalog building can lead to a permanent block. The API is "designed to be called directly in response to user input". It supports CORS. [20]
- **Terms:** It is free on condition that you "use CheapShark links when sending users to deals", with no own affiliate links. [20]
- **Fit:** Decent for a deal-tracker style app. The data is thin (prices, not game info).

#### FreeToGame (https://www.freetogame.com/api-doc)

- **Data:** Free-to-play games. Fields include `thumbnail`, `short_description`, `genre`, `platform`, `publisher` and `release_date`. [21][live]
- **Auth:** "Currently, no authentication is required." [21]
- **Limits:** "Please avoid doing more than 10 requests per second." [21]
- **Search:** **None.** It filters only by `platform`, `category`/`tag` and `sort-by`. [21] Name search would have to be done locally on the full list.
- **Terms:** "Attribution to FreeToGame required with an active hyperlink." It may be used for personal and commercial purposes. [21]
- **Fit:** Fair. It is small and simple, but lacks search.

### 3.3 Movies and TV

#### TMDB (https://developer.themoviedb.org)

- **Signup:** Create an account, then request a key from Account Settings, then accept the terms of use. Registration is "not optimized for mobile devices". [8]
- **Search:** `GET https://api.themoviedb.org/3/search/movie?query=...` using `Authorization: Bearer`. Results include `id, title, overview, release_date, vote_average, poster_path, backdrop_path`. [9]
- **Images:** `https://image.tmdb.org/t/p/{size}/{file_path}`, for example `.../w500/1E5baAaEse26fej7uHcjOgEE2t2.jpg`. [9b]
- **Rate limits:** The legacy 40-per-10-seconds limit was disabled on Dec 16, 2019. Upper limits now sit "somewhere in the 40 requests per second range"; respect 429 responses. [8b]
- **Terms:**
  - Free for non-commercial use with credit to TMDB. Commercial use needs a license. [10]
  - You must show the TMDB logo and the notice "This product uses the TMDB API but is not endorsed or certified by TMDB." [10]
  - Do not cache "for longer than 6 months". [10b]
  - No AI/ML training use, and TMDB may not be used as an image host for banners or graphics. [10b]
  - Terms last updated October 20, 2023. [10b]
- **Fit:** Excellent. It has everything the app needs, plus a huge catalog.

#### OMDb (https://www.omdbapi.com)

- **Signup:** A free key is emailed to you. The free tier is "FREE! (1,000 daily limit)". [12b]
- **Search:** `s=` for title search (paginated 1-100); `t=`/`i=` for a single title. HTTPS is supported. [12]
- **Images:** The "Poster API is only available to patrons." [12] Whether search results include a `Poster` URL is **UNVERIFIED** in this pass.
- **Terms:** "All content licensed under CC BY-NC 4.0." Not affiliated with IMDb. [12]
- **Fit:** Good and simple, but limited to 1,000 requests a day.

#### TVmaze (https://www.tvmaze.com/api)

- **Auth:** None for the public API. [11]
- **Search:** `/search/shows?q=` is fuzzy and relevance-ordered. `/singlesearch/shows?q=` returns one result or none. [11] A live request returned shows with `image.medium` and `image.original`. [live]
- **Limits:** "At least 20 calls every 10 seconds per IP address"; 429 when exceeded. Responses are cached for 60 minutes. [11]
- **Terms:** CC BY-SA. Linking back to TVmaze satisfies attribution. "You are free to directly link ('hotlink') to our image CDN", and images "can safely be cached indefinitely." [11]
- **Fit:** Excellent, and the lowest-friction option of all (no key at all).

### 3.4 Books

#### Open Library (https://openlibrary.org/developers/api)

- **Auth:** None. Identify your app with `User-Agent: MyApp (contact@example.org)` and register your use case. [22]
- **Limits:** 1 req/s unidentified, 3 req/s identified. No bulk metadata downloads (use the data dumps instead). [22]
- **Search:** `https://openlibrary.org/search.json?q=...` (also `title=` and `author=`) with `fields`, `limit` and `page`. Docs include `key`, `title`, `author_name`, `first_publish_year` and `cover_i`. [22b]
- **Covers:** `https://covers.openlibrary.org/b/{key}/{value}-{S|M|L}.jpg`. Lookups by keys other than CoverID or OLID are limited to 100 per 5 minutes per IP. Use covers.openlibrary.org as the `src` on public pages. [22c]
- **License:** The Internet Archive "does not assert any new copyright" over the database contents. [22d]
- **Fit:** Very good, with no key.

#### Google Books API (https://developers.google.com/books)

- **Auth:** Public-data requests "must be accompanied by an identifier, which can be an API key or an access token". Searching itself needs no OAuth. [23]
- **Search:** `GET https://www.googleapis.com/books/v1/volumes?q=...`, with operators like `intitle:`. `imageLinks` offers `smallThumbnail`, `thumbnail` and larger sizes. [23]
- **Limits:** Not stated on the usage page. **UNVERIFIED:** daily quota numbers, which are shown in the Google Cloud Console.
- **Terms:**
  - "Google attribution is required"; the "powered by Google" graphic "must always be displayed alongside any search modules or results". [23b]
  - "You may not charge users any fee for the use of your application." [23c]
- **Fit:** Good, but it needs a Google Cloud project and key, and has branding rules.

#### Gutendex (https://gutendex.com)

- **Data:** JSON catalog of Project Gutenberg's public-domain books. [25]
- **Search:** `/books?search=dickens%20great` searches author and title words, case-insensitive. [25] Cover URL at `formats["image/jpeg"]`, for example `https://www.gutenberg.org/cache/epub/1400/pg1400.cover.medium.jpg`. [live]
- **Auth / limits:** Neither is mentioned. "For long-term use, please run your own server". [25] The repo is MIT licensed and is itself a Django app. [25b] Note that one live request timed out before a later one succeeded. [live]
- **Fit:** OK for a classic-books app; the catalog is limited.

### 3.5 Recipes

#### TheMealDB (https://www.themealdb.com/api.php)

- **Auth:** Test key `1` is for use "during development of your app or for educational use". You "must become a supporter if releasing publicly on an appstore." [26]
- **Search:** `search.php?s=Arrabiata`; detail at `lookup.php?i=52772`. [26] A live search for "chicken" returned 25 meals with `strMealThumb` image URLs. [live]
- **Limits:** Not stated. Some endpoints are premium-only (random selection, latest, multi-ingredient filter). [26]
- **Terms:** "The API and site will always remain free at point of access." [26]
- **Fit:** Very good for a class project, since educational use is explicitly allowed.

#### Spoonacular (https://spoonacular.com/food-api)

- **Free plan:** 50 points/day, 1 req/s, 2 concurrent. No credit card when signing up directly (RapidAPI requires one). "Backlink Required." Requested data may be cached "for a maximum of 1 hour." [29]
- **Search / images:** The `complexSearch` endpoint and image fields are **UNVERIFIED** in this pass.
- **Fit:** Workable, but the 50-points/day budget is tight.

#### Edamam (https://developer.edamam.com/edamam-recipe-api)

- **No free plan.** EnterpriseBasic is $9/month (10,000 calls, 10-day trial), and plans run up to $399/month. Attribution is required, and "Not providing attribution is considered breach of contract." [24]
- **Fit:** Poor, because it is paid.

### 3.6 Music

#### MusicBrainz (https://musicbrainz.org/doc/MusicBrainz_API)

- **Auth:** None for reads. You "must have a meaningful" User-Agent. [30]
- **Limits:** About 1 req/s per IP; over the limit you get 503. Generic User-Agents are throttled together. [31]
- **Search:** `/ws/2/{entity}?query=<Lucene>`, `limit` 1-100, `fmt=json`. [32]
- **Images:** Not part of the core API. Cover Art Archive integration is **UNVERIFIED** in this pass.
- **Terms:** "Non-commercial use of this web service is free." [30]
- **Fit:** Good metadata, but no images and strict 1 req/s.

#### Deezer (https://developers.deezer.com/api)

- **Auth:** None needed for public search. `GET https://api.deezer.com/search?q=eminem` returned tracks with `title`, `artist`, `album`, `preview` (30-second MP3) and `md5_image`. [live]
- **Terms:** "You have to login to accept the terms and conditions of the simple API." [33] Storing audio locally is "strictly forbidden". [33b]
- **Limits:** **UNVERIFIED.** No official rate-limit page could be read.
- **Fit:** Usable, but the terms are only viewable after login.

#### Last.fm (https://www.last.fm/api)

- **Auth:** An API account and key are required. Requests without one returned an error. [34][live]
- **Search:** `artist.search`, `album.search`, `track.search`. [34]
- **Terms:**
  - "Solely for non-commercial purposes."
  - Use a "powered by AudioScrobbler" button.
  - Cache according to HTTP headers.
  - "You will not use any audio, audiovisual, images and/or artwork" (clause 5.1.8). [35]
- **Fit:** Weak for a visual app, because images are excluded by the terms.

#### Spotify Web API

- **2026 policy:** From 11 Feb 2026, new Development Mode Client IDs require the owner to have "an active Spotify Premium subscription", with a limit of 5 authorized users per app. Existing apps were migrated on March 9. [27][28] The Client ID limit was 1, raised to 25 as of July 2026. [28]
- **Search:** `GET /search` remains, but the max `limit` dropped from 50 to 10 and the default from 20 to 5. Fields such as `popularity` were removed. [28]
- **Fit:** Not recommended, because it costs money (Premium) and is heavily restricted.

### 3.7 Optional extras

#### Jikan (https://jikan.moe), anime and manga

- **What it is:** An "Unofficial MyAnimeList.net REST API" that "scrapes the website"; it is "not affiliated with MyAnimeList.net". MIT licensed. [37]
- **Limits:** 3 requests/s, 60/min, unlimited per day; MAL may also rate limit. All requests are cached for 24 hours. [36]
- **Live test:** A request to `api.jikan.moe/v4/anime?q=pokemon` timed out twice on 2026-11-12. [live]
- **Fit:** Good data, but its reliability depends on scraping.

#### Scryfall (https://scryfall.com/docs/api), Magic: The Gathering

- **Headers:** User-Agent and Accept headers are required. HTTPS only (TLS 1.2+). [38]
- **Limits:** `/cards/search` and `/cards/named` allow 2/s; other methods 10/s. A 429 locks you out for 30 seconds. [39]
- **Terms:** Under the WotC Fan Content Policy. You "may not 'paywall' access", and must not imply endorsement. [38]
- **Fit:** Excellent if the topic were Magic cards.

#### Open Food Facts

- **Auth:** Reads need no auth, only a custom `AppName/Version (email)` User-Agent. [40]
- **Limits:** 15 product reads/min and 10 searches/min per IP; not for search-as-you-type. [40]
- **Search:** No full-text search in v2. [40]
- **License:** ODbL; images are CC BY-SA. [40]
- **Fit:** Weak, because of the search limits.

---

## 4. Sources

`[live]` means a direct request to the provider's API or CDN on 2026-11-12 (results described inline). Archive snapshots are copies of the provider's own page on web.archive.org.

- [1] PokeAPI docs v2 (fair use, rate limits, pagination, edge policies): https://pokeapi.co/docs/v2
- [1b] PokeAPI About: https://pokeapi.co/about
- [2] PokeAPI GraphQL docs: https://pokeapi.co/docs/graphql
- [3] TCGdex filtering/sorting/pagination: https://tcgdex.dev/rest/filtering-sorting-pagination
- [4] TCGdex FAQ: https://tcgdex.dev/faq
- [5] TCGdex assets: https://tcgdex.dev/assets
- [6] Pokemon TCG API docs (deprecation notice): https://docs.pokemontcg.io/
- [6b] pokemontcg.io homepage: https://pokemontcg.io/
- [7] Scrydex pricing: https://scrydex.com/pricing
- [8] TMDB getting started: https://developer.themoviedb.org/docs/getting-started
- [8b] TMDB rate limiting: https://developer.themoviedb.org/docs/rate-limiting
- [9] TMDB search movie reference: https://developer.themoviedb.org/reference/search-movie
- [9b] TMDB image basics: https://developer.themoviedb.org/docs/image-basics
- [10] TMDB FAQ: https://developer.themoviedb.org/docs/faq
- [10b] TMDB API terms of use: https://www.themoviedb.org/api-terms-of-use
- [11] TVmaze API: https://www.tvmaze.com/api
- [12] OMDb API: https://www.omdbapi.com/
- [12b] OMDb API key signup: https://www.omdbapi.com/apikey.aspx
- [13] TCGdex home: https://tcgdex.dev/
- [14] IGDB API docs: https://api-docs.igdb.com/
- [15] RAWG API docs (live site returned 522; snapshot 2026-10-21): https://rawg.io/apidocs, archived at https://web.archive.org/web/20261021210207/https://rawg.io/apidocs
- [16] RAWG API terms (live returned 522; snapshot 2026-09-12): https://rawg.io/tos_api, archived at https://web.archive.org/web/20260912055721/https://rawg.io/tos_api
- [17] Giant Bomb API page (live returned 403 bot challenge; snapshot 2026-11-02): https://www.giantbomb.com/api/, archived at https://web.archive.org/web/20261102022123/https://giantbomb.com/api
- [17b] Giant Bomb API documentation (snapshot 2025-11-28): https://web.archive.org/web/20251128200808/https://www.giantbomb.com/api/documentation/
- [18] TCGdex cards-database GitHub: https://github.com/tcgdex/cards-database
- [19] Pokemon TCG API rate limits: https://docs.pokemontcg.io/getting-started/rate-limits
- [20] CheapShark API docs: https://apidocs.cheapshark.com/
- [21] FreeToGame API docs: https://www.freetogame.com/api-doc
- [22] Open Library developer API overview: https://openlibrary.org/developers/api
- [22b] Open Library search API: https://openlibrary.org/dev/docs/api/search
- [22c] Open Library covers API: https://openlibrary.org/dev/docs/api/covers
- [22d] Open Library licensing: https://openlibrary.org/developers/licensing
- [23] Google Books API "Using the API": https://developers.google.com/books/docs/v1/using
- [23b] Google Books branding guidelines: https://developers.google.com/books/branding
- [23c] Google Books API terms: https://developers.google.com/books/terms
- [24] Edamam Recipe Search API plans: https://developer.edamam.com/edamam-recipe-api
- [25] Gutendex: https://gutendex.com/
- [25b] Gutendex GitHub: https://github.com/garethbjohnson/gutendex
- [26] TheMealDB API: https://www.themealdb.com/api.php
- [27] Spotify blog, "Update on Developer Access and Platform Security" (2026-02-06): https://developer.spotify.com/blog/2026-02-06-update-on-developer-access-and-platform-security
- [28] Spotify February 2026 migration guide: https://developer.spotify.com/documentation/web-api/tutorials/february-2026-migration-guide
- [29] Spoonacular pricing: https://spoonacular.com/food-api/pricing
- [30] MusicBrainz API: https://musicbrainz.org/doc/MusicBrainz_API
- [31] MusicBrainz rate limiting: https://musicbrainz.org/doc/MusicBrainz_API/Rate_Limiting
- [32] MusicBrainz search: https://musicbrainz.org/doc/MusicBrainz_API/Search
- [33] Deezer API: https://developers.deezer.com/api
- [33b] Deezer guidelines: https://developers.deezer.com/guidelines
- [34] Last.fm API: https://www.last.fm/api
- [35] Last.fm API terms: https://www.last.fm/api/tos
- [36] Jikan v4 OpenAPI spec (rendered at https://docs.api.jikan.moe/): https://raw.githubusercontent.com/jikan-me/jikan-rest/master/storage/api-docs/api-docs.json
- [37] Jikan REST GitHub: https://github.com/jikan-me/jikan-rest
- [38] Scryfall API docs: https://scryfall.com/docs/api
- [39] Scryfall rate limits: https://scryfall.com/docs/api/rate-limits
- [40] Open Food Facts API docs: https://openfoodfacts.github.io/openfoodfacts-server/api/

### Open items (not verified)

- RAWG: whether the 522 outage is temporary; also the `search=` parameter and image fields.
- Pokemon TCG API search syntax and image fields (moot, since it is deprecated).
- Google Books daily quota numbers.
- Deezer rate limits and full terms (login required).
- Spoonacular search endpoint and image fields.
- OMDb `Poster` field availability for free keys.
- MusicBrainz / Cover Art Archive image integration.
- PokeAPI GraphQL name filtering (`_ilike`).
- TCGdex image licensing and hotlinking terms.

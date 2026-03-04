# FeastOptimizer: Complete Technical Blueprint

## Executive Summary

FeastOptimizer is a personal-use web application that generates weekly meal plans optimized for cost and macro targets, integrates Australian loyalty programs (Flybuys, Everyday Rewards) for additional savings, and builds cooking proficiency through a gamified cuisine skill tree with spaced repetition scheduling. The application scrapes daily prices from Coles, Woolworths, and ALDI, parses loyalty offer screenshots via vision models, and uses linear programming to produce the cheapest possible meal plan that meets nutritional goals. A wishlist system tracks prices on staple goods, gifts, and household items across multiple stores, alerting when prices drop below user-defined thresholds.

The stack is Python/Flask on the backend, vanilla HTML/CSS/JavaScript on the frontend, Supabase (PostgreSQL) for data, and Railway for hosting. Total ongoing cost targets less than $10/month with zero paid APIs.

***

## The Idea

### Problem Statement

Weekly meal planning involves several disconnected problems: deciding what to cook, checking whether it fits a budget, hitting nutritional targets, comparing prices across supermarkets, and remembering to take advantage of loyalty promotions. Most people handle these manually or ignore them entirely, leaving significant savings on the table. Separately, learning to cook new cuisines lacks structure — people repeat the same dishes or attempt recipes beyond their skill level.

### Solution

A single application that unifies:

- **Price intelligence** — Daily scraping of Coles, Woolworths, and ALDI prices for ~500 common grocery products
- **Loyalty optimization** — Parsing personalized Flybuys and Everyday Rewards offers from user-uploaded screenshots, converting point multipliers into effective price reductions
- **Meal planning** — Linear programming optimization that selects recipes to minimize total shopping cost while meeting weekly macro constraints (protein, carbs, fat, calories)
- **Skill development** — A cuisine-based progression system with beginner → intermediate → advanced tiers and an SM-2 spaced repetition algorithm that schedules technique practice
- **Wishlist tracking** — Price monitoring and alerting for staple goods, gifts, and household items across multiple Australian retailers

### Design Principles

- **Minimal input required** — Set preferences once, upload screenshots weekly, generate plans in one click
- **No daily tracking burden** — No pantry logging, no calorie diary, no leftover management
- **Zero cost beyond hosting** — All APIs must be free-tier; no paid data sources
- **Personal use first** — No user authentication system, no multi-tenant architecture in MVP

***

## Required Features

### Feature 1: Meal Plan Generator

The core feature. The user provides a weekly budget, daily macro targets, desired meal counts (e.g., 2 breakfasts, 5 lunches, 7 dinners), an optional cuisine focus, and a mode toggle (Learning vs Cost Only). The system returns a 7-day meal plan with recipes, per-serving costs, macro totals, and a consolidated shopping list split by store. In Learning Mode, the optimizer applies a weighting bonus to recipes from the selected cuisine, accepting up to 20% higher cost if the recipe teaches a new technique.

### Feature 2: Price Scraping Pipeline

A daily scheduled job (3 AM AEDT) scrapes product pages from Coles and Woolworths for approximately 500 commonly purchased grocery items. Prices are stored with timestamps to build historical price data. ALDI prices are manually seeded for ~100 staple products. Products are matched across stores using barcode matching (primary) and fuzzy string matching with weight/volume normalization (fallback). Verified matches are cached in a canonical product catalog.

### Feature 3: Loyalty Rewards Integration

The user uploads 2-4 screenshots from the Flybuys and Everyday Rewards mobile apps. A vision model (GPT-4 Vision via OpenRouter) extracts structured offer data: multiplier offers (e.g., 10x points on meat), spend thresholds (e.g., spend $100 earn 3000 points), and category bonuses (e.g., 2000 points on Cadbury). Offers are stored with expiry dates and activation status. The optimizer converts point values to dollar equivalents (2000 points = $10, or 0.5 cents per point) and reduces effective prices accordingly.

### Feature 4: Recipe Database

Recipes are sourced from TheMealDB (free API, 600+ recipes), manual entry of personal favorites, and selective web scraping of sites like RecipeTin Eats. Each recipe stores ingredients (linked to canonical products), per-serving macros (calculated from USDA FoodData Central), cuisine classification, difficulty rating, techniques taught, tier placement, prep/cook time, and an optional YouTube video URL with timestamps.

### Feature 5: Cuisine Skill Tree

Six cuisines at MVP launch: Chinese, Japanese, Italian, Thai, Indian, French. Each cuisine has three tiers (Beginner, Intermediate, Advanced) with 5-10 recipes per tier. Tier progression is gated by recipe completion count and technique mastery. Techniques (e.g., stir-frying, velveting, sauce emulsification) are tracked independently and shared across cuisines where applicable.

### Feature 6: Spaced Repetition for Techniques

After completing a recipe, the user rates their execution of each technique on a 0-5 scale. The SM-2 algorithm calculates a next-review date based on easiness factor and repetition count. Techniques not practiced within the scheduled interval decay in effective skill level. The meal planner prioritizes recipes containing overdue techniques. Maximum review interval is capped at 60 days (cooking skills decay faster than vocabulary).

### Feature 7: Wishlist & Price Tracking

Users add items to a wishlist with a target price and/or percentage-drop threshold. The daily price scraper checks all wishlist items and triggers email notifications when conditions are met. A gift registry extension adds recipient names, occasion dates, and budget ranges, with reminders as occasions approach. Tracked stores include Coles, Woolworths, ALDI, Bunnings, Kmart, Target, Officeworks, and Dymocks.

### Feature 8: Shopping List Generator

After accepting a meal plan, the system generates a shopping list consolidated by store, sorted by cheapest effective price. Items the user already owns (spices, herbs, pantry staples — set once in settings) are excluded. The list shows base price, effective price (after loyalty adjustments), and flags active promotions. Export options include a mobile-friendly web view.

### Feature 9: Video Integration

Recipes display embedded YouTube videos for technique tutorials and full walkthroughs. The YouTube Data API (free tier, 10,000 requests/day) searches for relevant content from preferred channels (Serious Eats, Chinese Cooking Demystified, Kenji López-Alt, RecipeTin Eats). Video timestamps extracted from descriptions are linked to individual recipe steps.

### Feature 10: Theme System

Three visual themes selectable in settings: Bauhaus (modern, clean), 8-Bit Pixel Farm (retro gaming aesthetic), and Retro (vintage with offset shadows). All styling uses CSS custom properties for colors, fonts, spacing, border radius, and shadows, making theme addition trivial.

***

## Technology Stack

| Layer | Technology | Justification |
|-------|-----------|---------------|
| **Backend** | Python 3.11+ with Flask | Lightweight, familiar, sufficient for single-user app |
| **Frontend** | HTML, CSS, JavaScript (vanilla) | No framework overhead; CSS custom properties for theming |
| **Database** | Supabase (PostgreSQL, free tier) | Hosted Postgres with REST API, free for small projects |
| **Hosting** | Railway | Simple Python deployment, cron jobs, ~$5-10/month |
| **Image Storage** | Cloudflare R2 (free tier) | Store uploaded screenshots, zero egress cost |
| **Scraping** | BeautifulSoup + requests | Sufficient for static/semi-static product pages |
| **Vision API** | GPT-4 Vision via OpenRouter | ~$0.01-0.03 per screenshot; ~$0.12/week |
| **Nutrition API** | USDA FoodData Central | Free, comprehensive, API key via email registration |
| **Recipe API** | TheMealDB | Completely free, no key needed, 600+ recipes |
| **Video API** | YouTube Data API v3 | Free tier: 10,000 requests/day |
| **Optimization** | PuLP (Python) | Open-source linear programming solver |
| **Scheduling** | APScheduler | In-process cron-style scheduling for daily jobs |
| **Fuzzy Matching** | fuzzywuzzy + python-Levenshtein | Fast fuzzy string matching for product deduplication |

***

## File Structure

```
feast_optimizer/
│
├── app.py                        # Flask application factory and configuration
├── config.py                     # Environment variables, API keys, constants
├── requirements.txt              # Python dependencies
├── Procfile                      # Railway deployment command
│
├── models/
│   ├── __init__.py
│   ├── product.py                # Canonical product model and store mappings
│   ├── recipe.py                 # Recipe model with ingredients and macros
│   ├── price.py                  # Price history model
│   ├── offer.py                  # Loyalty offer model
│   ├── wishlist.py               # Wishlist item model
│   ├── progress.py               # User cooking progress model
│   └── srs.py                    # SRS card model for technique tracking
│
├── services/
│   ├── __init__.py
│   ├── scraper.py                # Price scraping for Coles, Woolworths, ALDI
│   ├── product_matcher.py        # Cross-store product matching (barcode + fuzzy)
│   ├── nutrition.py              # USDA FoodData Central API client
│   ├── recipe_importer.py        # TheMealDB and web scraping recipe import
│   ├── offer_parser.py           # Vision model screenshot parsing
│   ├── optimizer.py              # Linear programming meal plan optimization
│   ├── srs_engine.py             # SM-2 spaced repetition algorithm
│   ├── wishlist_tracker.py       # Price tracking and alert checking
│   ├── shopping_list.py          # Shopping list generation and store splitting
│   ├── video_search.py           # YouTube API integration
│   └── notifier.py               # Email notification service
│
├── routes/
│   ├── __init__.py
│   ├── dashboard.py              # Dashboard page routes
│   ├── planner.py                # Meal planner form and results routes
│   ├── recipes.py                # Recipe listing, detail, and CRUD routes
│   ├── skills.py                 # Skill tree and progress routes
│   ├── wishlist.py               # Wishlist CRUD and alert routes
│   ├── settings.py               # User settings and preference routes
│   └── api.py                    # JSON API endpoints for AJAX interactions
│
├── templates/
│   ├── base.html                 # Base template with nav, header, theme loader
│   ├── dashboard.html            # Dashboard with stats, alerts, week overview
│   ├── planner.html              # Meal plan generator form and results
│   ├── planner_results.html      # Generated meal plan display
│   ├── recipes.html              # Recipe grid with filters
│   ├── recipe_detail.html        # Single recipe view with video and steps
│   ├── skills.html               # Cuisine skill trees and technique status
│   ├── self_assessment.html      # Post-cooking technique rating form
│   ├── wishlist.html             # Wishlist table with price trends
│   ├── shopping_list.html        # Store-split shopping list
│   ├── settings.html             # All user preferences and loyalty upload
│   └── components/
│       ├── recipe_card.html      # Reusable recipe card partial
│       ├── progress_bar.html     # Reusable progress bar partial
│       ├── stat_box.html         # Reusable stat card partial
│       └── alert.html            # Reusable alert partial
│
├── static/
│   ├── css/
│   │   ├── main.css              # Base styles and CSS custom properties
│   │   ├── themes/
│   │   │   ├── bauhaus.css       # Bauhaus theme overrides
│   │   │   ├── pixel-farm.css    # 8-bit pixel farm theme overrides
│   │   │   └── retro.css         # Retro theme overrides
│   │   └── responsive.css        # Mobile breakpoints and responsive rules
│   ├── js/
│   │   ├── app.js                # Navigation, theme switching, global handlers
│   │   ├── planner.js            # Meal planner form interactions and AJAX
│   │   ├── recipes.js            # Recipe filtering and search
│   │   ├── skills.js             # Skill tree interactions
│   │   ├── wishlist.js           # Wishlist table sorting and filtering
│   │   └── assessment.js         # Self-assessment form submission
│   └── images/
│       ├── pixel-farm-tile.jpeg  # Background tile for pixel farm theme
│       └── logo.svg              # Application logo
│
├── jobs/
│   ├── __init__.py
│   ├── daily_scrape.py           # Scheduled daily price scraping job
│   ├── wishlist_check.py         # Scheduled wishlist price drop check
│   └── offer_expiry.py           # Scheduled expired offer cleanup
│
├── data/
│   ├── cuisine_skill_trees.json  # Cuisine tier definitions and recipe mappings
│   ├── building_blocks.json      # Cooking building blocks (sauces, stocks, techniques)
│   ├── seasonal_produce.json     # Australian seasonal produce calendar
│   └── initial_products.json     # Seed data for canonical product catalog
│
└── tests/
    ├── test_optimizer.py         # Tests for meal plan optimization
    ├── test_product_matcher.py   # Tests for product matching accuracy
    ├── test_srs_engine.py        # Tests for SM-2 algorithm correctness
    └── test_offer_parser.py      # Tests for offer extraction accuracy
```

***

## Function, Argument, and Variable Specifications

### `app.py` — Application Factory

#### `create_app(config_name)`
- **Arguments:** `config_name` (str) — environment name ("development", "production", "testing")
- **Returns:** Configured Flask application instance
- **Purpose:** Initialize Flask app, register blueprints from all route modules, configure Supabase connection, initialize APScheduler with daily jobs, load theme preference from local storage

#### `init_scheduler(app)`
- **Arguments:** `app` (Flask) — application instance
- **Returns:** None
- **Purpose:** Register APScheduler jobs: `daily_scrape` at 03:00 AEDT, `wishlist_check` at 03:30 AEDT, `offer_expiry` at 04:00 AEDT

***

### `config.py` — Configuration

#### Variables
- `SUPABASE_URL` (str) — Supabase project URL from environment
- `SUPABASE_KEY` (str) — Supabase anonymous key from environment
- `OPENROUTER_API_KEY` (str) — OpenRouter API key for GPT-4 Vision
- `USDA_API_KEY` (str) — USDA FoodData Central API key
- `YOUTUBE_API_KEY` (str) — YouTube Data API v3 key
- `CLOUDFLARE_R2_ENDPOINT` (str) — R2 bucket endpoint for image storage
- `NOTIFICATION_EMAIL` (str) — Gmail address for sending alerts
- `EMAIL_PASSWORD` (str) — Gmail app password
- `USER_EMAIL` (str) — Recipient email for notifications
- `SCRAPE_USER_AGENTS` (list[str]) — Rotating user agent strings for scraping
- `MAX_VISION_SCREENSHOTS_PER_WEEK` (int) — Cost cap, default 8
- `POINTS_TO_DOLLAR_RATE` (float) — Loyalty point conversion rate, default 0.005

***

### `models/product.py` — Canonical Product Model

#### Variables (Database Fields)
- `id` (str) — Unique canonical product identifier (e.g., "PROD_chicken_breast")
- `name` (str) — Human-readable product name
- `category` (str) — Product category (e.g., "meat_poultry", "produce", "dairy")
- `base_unit` (str) — Standard unit for this product ("kg", "L", "each")
- `nutrition_per_100g` (dict) — Keys: "protein", "carbs", "fat", "calories", "fiber" — all floats
- `usda_fdc_id` (int) — Link to USDA FoodData Central entry
- `aliases` (list[str]) — Alternative names for fuzzy matching
- `store_mappings` (dict) — Keyed by store name, each value contains "product_id", "name", "barcode", "url"
- `average_weight_per_piece_g` (float or None) — For countable items (e.g., 1 clove garlic = 3g)
- `created_at` (datetime) — Record creation timestamp

#### `get_all_products()`
- **Returns:** list[dict] — All canonical products from database
- **Purpose:** Fetch complete product catalog for optimizer and matcher

#### `get_product_by_id(product_id)`
- **Arguments:** `product_id` (str)
- **Returns:** dict or None
- **Purpose:** Fetch single product with all store mappings

#### `upsert_product(product_data)`
- **Arguments:** `product_data` (dict) — Full product record
- **Returns:** dict — Inserted/updated record
- **Purpose:** Create or update canonical product entry

***

### `models/recipe.py` — Recipe Model

#### Variables (Database Fields)
- `id` (str) — Unique recipe identifier
- `name` (str) — Recipe title
- `cuisine` (str) — Cuisine classification (e.g., "chinese", "italian")
- `difficulty` (int) — 1-5 difficulty rating
- `tier` (str) — Skill tree tier ("beginner", "intermediate", "advanced")
- `prep_time` (int) — Preparation time in minutes
- `cook_time` (int) — Cooking time in minutes
- `servings` (int) — Number of servings the recipe produces
- `techniques_taught` (list[str]) — Technique identifiers this recipe practices
- `key_learnings` (str) — Human-readable description of what the recipe teaches
- `builds_on` (list[str]) — Recipe names that should be completed first
- `ingredients` (list[dict]) — Each dict: "canonical_product_id", "quantity", "unit", "notes"
- `macros_per_serving` (dict) — Keys: "protein", "carbs", "fat", "calories", "fiber"
- `instructions` (list[str]) — Ordered cooking steps
- `video_url` (str or None) — YouTube video URL
- `video_timestamps` (dict or None) — Step index to timestamp mapping
- `source` (str) — Origin: "manual", "themealdb", "scraped"
- `created_at` (datetime)

#### `get_recipes_by_cuisine(cuisine)`
- **Arguments:** `cuisine` (str)
- **Returns:** list[dict] — All recipes for given cuisine, ordered by difficulty

#### `get_recipes_by_technique(technique)`
- **Arguments:** `technique` (str)
- **Returns:** list[dict] — All recipes that teach the given technique

#### `get_recipes_by_tier(cuisine, tier)`
- **Arguments:** `cuisine` (str), `tier` (str)
- **Returns:** list[dict] — Recipes in a specific cuisine tier

#### `search_recipes(filters)`
- **Arguments:** `filters` (dict) — Optional keys: "cuisine", "difficulty_max", "time_max", "technique", "text_query"
- **Returns:** list[dict] — Filtered recipe results

#### `upsert_recipe(recipe_data)`
- **Arguments:** `recipe_data` (dict)
- **Returns:** dict — Inserted/updated record

***

### `models/price.py` — Price History Model

#### Variables (Database Fields)
- `id` (int) — Auto-incrementing primary key
- `product_id` (str) — Foreign key to canonical_products
- `store` (str) — Store name ("coles", "woolworths", "aldi")
- `price` (float) — Raw shelf price
- `unit_price` (float) — Normalized price per base unit (e.g., $/kg)
- `promotion_active` (bool) — Whether a store-side promotion is running
- `promotion_details` (str or None) — Description of promotion
- `timestamp` (datetime)

#### `get_current_price(product_id, store)`
- **Arguments:** `product_id` (str), `store` (str)
- **Returns:** float or None — Most recent price for product at store

#### `get_current_prices_all_stores(product_id)`
- **Arguments:** `product_id` (str)
- **Returns:** dict — Store name to current price mapping

#### `get_cheapest_option(product_id)`
- **Arguments:** `product_id` (str)
- **Returns:** dict — Keys: "store", "price", "unit_price", "promotion_active"

#### `get_price_history(product_id, store, days)`
- **Arguments:** `product_id` (str), `store` (str, optional), `days` (int, default 30)
- **Returns:** list[dict] — Historical price records sorted by timestamp

#### `insert_price(price_data)`
- **Arguments:** `price_data` (dict)
- **Returns:** dict — Inserted record

***

### `models/offer.py` — Loyalty Offer Model

#### Variables (Database Fields)
- `id` (int) — Auto-incrementing primary key
- `program` (str) — "flybuys" or "everyday_rewards"
- `offer_type` (str) — "multiplier", "threshold", "category_bonus", "product_specific"
- `title` (str) — Offer headline text
- `details` (dict) — Type-specific fields (e.g., "multiplier": 10, "category": "Fresh Produce")
- `expiry_date` (date) — When the offer expires
- `activated` (bool) — Whether the offer has been activated in the app
- `created_at` (datetime)

#### `get_active_offers()`
- **Returns:** list[dict] — All non-expired offers

#### `get_offers_by_program(program)`
- **Arguments:** `program` (str)
- **Returns:** list[dict] — Active offers for specific program

#### `insert_offers(offers_list)`
- **Arguments:** `offers_list` (list[dict])
- **Returns:** list[dict] — Inserted records

#### `expire_old_offers()`
- **Returns:** int — Count of offers marked expired
- **Purpose:** Clean up offers past their expiry date

***

### `models/wishlist.py` — Wishlist Item Model

#### Variables (Database Fields)
- `id` (int) — Auto-incrementing primary key
- `product_name` (str) — Item description
- `product_id` (str or None) — Link to canonical product if applicable
- `category` (str) — "grocery_staple", "gift", "cookware", "book", "household"
- `target_price` (float or None) — Desired price point
- `alert_threshold_percent` (int) — Percentage drop that triggers alert, default 10
- `baseline_price` (float) — Price when item was added
- `current_best_price` (float or None) — Latest best price found
- `current_best_store` (str or None) — Store with best current price
- `stores_to_track` (list[str]) — Which stores to monitor
- `recipient` (str or None) — Gift recipient name
- `occasion` (str or None) — Gift occasion description
- `occasion_date` (date or None) — Deadline for gift purchase
- `priority` (str) — "low", "medium", "high"
- `purchased` (bool) — Whether item has been bought
- `created_at` (datetime)

#### `get_active_wishlist()`
- **Returns:** list[dict] — All non-purchased wishlist items

#### `get_upcoming_gifts(days)`
- **Arguments:** `days` (int, default 60)
- **Returns:** list[dict] — Gift items with occasion dates within the window

#### `upsert_wishlist_item(item_data)`
- **Arguments:** `item_data` (dict)
- **Returns:** dict

#### `mark_purchased(item_id)`
- **Arguments:** `item_id` (int)
- **Returns:** dict — Updated record

***

### `models/progress.py` — User Progress Model

#### Variables (Database Fields)
- `id` (int) — Auto-incrementing primary key
- `recipe_id` (str) — Foreign key to recipes
- `cuisine` (str) — Cuisine of the completed recipe
- `completed_date` (datetime)
- `quality_ratings` (dict) — Technique name to quality rating (0-5) mapping
- `notes` (str or None) — User notes about the session

#### `get_completed_recipes(cuisine)`
- **Arguments:** `cuisine` (str, optional)
- **Returns:** list[dict] — Completed recipe records, optionally filtered by cuisine

#### `get_completion_count(recipe_id)`
- **Arguments:** `recipe_id` (str)
- **Returns:** int — Number of times recipe has been completed

#### `get_technique_completion_count(technique)`
- **Arguments:** `technique` (str)
- **Returns:** int — Number of times technique has been practiced across all recipes

#### `insert_completion(completion_data)`
- **Arguments:** `completion_data` (dict)
- **Returns:** dict

***

### `models/srs.py` — SRS Card Model

#### Variables (Database Fields)
- `id` (int) — Auto-incrementing primary key
- `technique` (str) — Unique technique identifier
- `easiness_factor` (float) — SM-2 easiness factor, default 2.5
- `interval` (int) — Days until next review, default 1
- `repetitions` (int) — Successful consecutive repetitions, default 0
- `next_review_date` (datetime)
- `last_practiced` (datetime or None)
- `quality_history` (list[dict]) — Each dict: "date", "quality", "notes"

#### `get_card(technique)`
- **Arguments:** `technique` (str)
- **Returns:** dict or None

#### `get_due_cards(limit)`
- **Arguments:** `limit` (int, default 10)
- **Returns:** list[dict] — Cards where next_review_date is in the past, ordered by most overdue

#### `get_upcoming_reviews(days)`
- **Arguments:** `days` (int, default 7)
- **Returns:** list[dict] — Cards due within the given window

#### `upsert_card(card_data)`
- **Arguments:** `card_data` (dict)
- **Returns:** dict

***

### `services/scraper.py` — Price Scraper

#### `scrape_coles(product_list)`
- **Arguments:** `product_list` (list[dict]) — Each dict has "product_id", "url", "name"
- **Returns:** list[dict] — Each dict: "product_id", "store", "price", "unit_price", "promotion_active", "promotion_details"
- **Purpose:** Fetch current prices from Coles website for all products in the list. Uses requests with rotating user agents. Parses price, unit price, and promotion badges from HTML.

#### `scrape_woolworths(product_list)`
- **Arguments:** `product_list` (list[dict])
- **Returns:** list[dict] — Same structure as scrape_coles
- **Purpose:** Same as scrape_coles but targeting Woolworths product pages

#### `scrape_store(store_name, product_list)`
- **Arguments:** `store_name` (str), `product_list` (list[dict])
- **Returns:** list[dict]
- **Purpose:** Dispatcher that calls the appropriate store-specific scraper

#### `get_random_user_agent()`
- **Returns:** str — Random user agent string from the configured rotation list
- **Purpose:** Avoid detection by varying request headers

#### `rate_limited_request(url, headers, delay_range)`
- **Arguments:** `url` (str), `headers` (dict), `delay_range` (tuple[float, float]) — Min and max delay in seconds
- **Returns:** requests.Response
- **Purpose:** Make HTTP request with random delay between requests to avoid rate limiting

***

### `services/product_matcher.py` — Product Matching

#### `normalize_product_name(name)`
- **Arguments:** `name` (str) — Raw product name from a store
- **Returns:** str — Cleaned name with store branding removed, units standardized, lowercase, extra whitespace stripped
- **Purpose:** Prepare product names for comparison by removing noise

#### `extract_metadata(name)`
- **Arguments:** `name` (str) — Product name
- **Returns:** dict — Keys: "weight" (str or None), "volume" (str or None), "tokens" (list[str])
- **Purpose:** Extract weight/volume and tokenize for matching

#### `find_barcode_match(barcode, store_products)`
- **Arguments:** `barcode` (str), `store_products` (list[dict])
- **Returns:** dict or None — Matching product if barcode found
- **Purpose:** Exact barcode match across stores (handles ~60-70% of products)

#### `find_fuzzy_match(product, candidates, threshold)`
- **Arguments:** `product` (dict) — Source product, `candidates` (list[dict]) — Products from other store, `threshold` (int, default 80) — Minimum match score
- **Returns:** dict or None — Best matching candidate above threshold
- **Purpose:** Multi-level fuzzy matching using fuzz.ratio, fuzz.token_sort_ratio, and fuzz.token_set_ratio. Weight/volume must match. Returns highest-scoring candidate.

#### `match_products_across_stores(coles_products, woolworths_products)`
- **Arguments:** Two lists of store product dicts
- **Returns:** list[dict] — Canonical product entries with store_mappings populated
- **Purpose:** Run barcode matching first, then fuzzy matching on unmatched products. Flag low-confidence matches for manual verification.

#### `verify_match(canonical_product_id, store, store_product_id, confirmed)`
- **Arguments:** `canonical_product_id` (str), `store` (str), `store_product_id` (str), `confirmed` (bool)
- **Returns:** dict — Updated canonical product
- **Purpose:** Allow manual confirmation or rejection of automated matches

***

### `services/nutrition.py` — USDA Nutrition API Client

#### `search_food(query)`
- **Arguments:** `query` (str) — Food name to search
- **Returns:** list[dict] — Search results with fdc_id, description, data_type
- **Purpose:** Search USDA FoodData Central for matching foods. Filter to Foundation and SR Legacy data types for accuracy.

#### `get_nutrition(fdc_id)`
- **Arguments:** `fdc_id` (int) — USDA food data central ID
- **Returns:** dict — Keys: "protein", "carbs", "fat", "calories", "fiber" — all per 100g
- **Purpose:** Fetch and extract macro nutrients from USDA API response

#### `calculate_recipe_macros(recipe)`
- **Arguments:** `recipe` (dict) — Full recipe with ingredients list
- **Returns:** dict — Per-serving macros: "protein", "carbs", "fat", "calories", "fiber"
- **Purpose:** Sum nutrition across all ingredients (converting quantities to grams using base unit conversions), then divide by servings

#### `convert_to_grams(quantity, unit, product)`
- **Arguments:** `quantity` (float), `unit` (str), `product` (dict) — Canonical product with average_weight_per_piece_g
- **Returns:** float — Equivalent weight in grams
- **Purpose:** Convert cups, tablespoons, teaspoons, pieces, cloves, etc. to grams using standard conversion table and product-specific piece weights

***

### `services/recipe_importer.py` — Recipe Import

#### `import_from_mealdb(meal_name)`
- **Arguments:** `meal_name` (str)
- **Returns:** dict — Partially populated recipe dict needing canonical product mapping
- **Purpose:** Search TheMealDB by name, extract ingredients (strIngredient1..20 and strMeasure1..20), instructions, cuisine, and thumbnail

#### `import_from_mealdb_by_cuisine(cuisine)`
- **Arguments:** `cuisine` (str) — TheMealDB area name (e.g., "Chinese", "Italian")
- **Returns:** list[dict] — All recipes for that cuisine
- **Purpose:** Bulk import all recipes for a cuisine from TheMealDB

#### `map_ingredients_to_canonical(ingredients_raw)`
- **Arguments:** `ingredients_raw` (list[dict]) — Each has "name", "measure" from TheMealDB
- **Returns:** list[dict] — Each mapped to "canonical_product_id", "quantity", "unit"
- **Purpose:** Fuzzy match TheMealDB ingredient names to canonical products. Parse measure strings (e.g., "2 cups", "1/2 tsp") into numeric quantities and unit strings.

#### `scrape_recipe_from_url(url)`
- **Arguments:** `url` (str) — Recipe page URL (e.g., RecipeTin Eats)
- **Returns:** dict or None — Recipe data extracted from schema.org JSON-LD markup
- **Purpose:** Extract structured recipe data from websites that use schema.org Recipe markup

#### `parse_measure_string(measure)`
- **Arguments:** `measure` (str) — e.g., "2 1/2 cups", "1 tbsp", "3 cloves"
- **Returns:** tuple[float, str] — (quantity, unit)
- **Purpose:** Parse free-text measurements into numeric quantity and standardized unit

***

### `services/offer_parser.py` — Loyalty Offer Screenshot Parsing

#### `extract_offers_from_screenshots(image_files)`
- **Arguments:** `image_files` (list[FileStorage]) — Uploaded image files from Flask request
- **Returns:** list[dict] — Structured offer objects
- **Purpose:** Encode each image to base64, send to GPT-4 Vision via OpenRouter with a structured extraction prompt, parse JSON response into offer dicts

#### `build_extraction_prompt()`
- **Returns:** str — System prompt instructing the vision model to extract offer type, multiplier/threshold/bonus details, category, expiry date, and activation status as a JSON array
- **Purpose:** Consistent prompt engineering for reliable extraction

#### `parse_vision_response(response_text)`
- **Arguments:** `response_text` (str) — Raw text from vision model (may include markdown code fences)
- **Returns:** list[dict] — Parsed JSON offer objects
- **Purpose:** Strip markdown formatting, parse JSON, validate required fields exist

#### `classify_offer(title, description)`
- **Arguments:** `title` (str), `description` (str)
- **Returns:** tuple[str, dict] — (offer_type, details)
- **Purpose:** Fallback regex-based classifier if vision model returns incomplete typing. Detects multiplier patterns ("10x points on..."), threshold patterns ("spend $X, earn Y points"), and category bonuses.

#### `calculate_offer_value(offer, spend_amount)`
- **Arguments:** `offer` (dict) — Structured offer, `spend_amount` (float) — How much being spent on applicable items
- **Returns:** float — Dollar value of the offer for this spend
- **Purpose:** Convert point-based offers to dollar savings. Multiplier: (multiplier - 1) × spend × 0.005. Threshold: bonus_points × 0.005 if threshold met. Category bonus: bonus_points × 0.005.

***

### `services/optimizer.py` — Meal Plan Optimization

#### `optimize_meal_plan(recipes, products, macros, budget, meal_counts, active_offers, owned_items, cuisine_focus, learning_mode)`
- **Arguments:**
  - `recipes` (list[dict]) — Available recipe pool
  - `products` (list[dict]) — Canonical products with current prices
  - `macros` (dict) — Daily targets: "protein", "carbs", "fat", "calories"
  - `budget` (float) — Maximum weekly spend
  - `meal_counts` (dict) — Keys: "breakfast", "lunch", "dinner" with integer counts
  - `active_offers` (list[dict]) — Current loyalty offers
  - `owned_items` (list[str]) — Canonical product IDs the user already owns
  - `cuisine_focus` (str or None) — If set, weight these recipes higher
  - `learning_mode` (bool) — If true, apply learning bonus to cuisine-focused recipes
- **Returns:** dict — Keys: "meal_plan" (day-to-recipe mapping), "total_cost" (float), "macro_summary" (dict), "shopping_list" (list), "savings_from_offers" (float)
- **Purpose:** Core optimization engine. Sets up PuLP linear programming problem. Decision variables are integer counts of each recipe (0 to max servings). Objective function minimizes total cost (with offer-adjusted effective prices). Constraints enforce minimum weekly macros, maximum budget, and total meal counts. Learning mode applies a 0.8x cost multiplier to cuisine-focus recipes to bias selection.

#### `calculate_recipe_cost(recipe, products, active_offers, owned_items)`
- **Arguments:** `recipe` (dict), `products` (list[dict]), `active_offers` (list[dict]), `owned_items` (list[str])
- **Returns:** float — Total recipe cost after offer adjustments, excluding owned items
- **Purpose:** For each ingredient, find cheapest product option across stores, apply any active offer discounts, skip items in owned_items list, sum total

#### `calculate_effective_price(product, store, active_offers)`
- **Arguments:** `product` (dict), `store` (str), `active_offers` (list[dict])
- **Returns:** float — Price after loyalty offer adjustments
- **Purpose:** Check if any active offers apply to this product's category/brand at this store. If multiplier offer applies: reduce price by (multiplier - 1) × price × 0.005. Return adjusted price.

#### `check_offer_applies(offer, product)`
- **Arguments:** `offer` (dict), `product` (dict)
- **Returns:** bool — Whether the offer applies to this product
- **Purpose:** Match offer category/brand against product category and name using substring and fuzzy matching

#### `generate_shopping_list(meal_plan, products, active_offers, owned_items)`
- **Arguments:** `meal_plan` (dict), `products` (list[dict]), `active_offers` (list[dict]), `owned_items` (list[str])
- **Returns:** dict — Keyed by store name, each value is a list of items with quantity, price, effective_price, promotion flag
- **Purpose:** Aggregate all ingredients from selected recipes, exclude owned items, assign each to cheapest store considering offer adjustments, consolidate quantities

***

### `services/srs_engine.py` — Spaced Repetition Engine

#### `record_practice(technique, quality_rating, notes)`
- **Arguments:** `technique` (str), `quality_rating` (int, 0-5), `notes` (str or None)
- **Returns:** dict — Keys: "new_easiness", "next_review_days", "next_review_date", "mastery_percentage"
- **Purpose:** Core SM-2 algorithm. Update easiness factor: EF' = EF + (0.1 - (5 - q) × (0.08 + (5 - q) × 0.02)). Constrain EF to minimum 1.3. If quality < 3: reset repetitions and interval to 1 day. If quality ≥ 3: increment repetitions; set interval to 1 (first rep), 6 (second rep), or previous_interval × EF (subsequent). Cap maximum interval at 60 days.

#### `get_due_techniques(limit)`
- **Arguments:** `limit` (int, default 10)
- **Returns:** list[dict] — Each with "technique", "days_overdue", "last_practiced", "current_level"
- **Purpose:** Query SRS cards where next_review_date is past, sorted by most overdue first

#### `get_upcoming_reviews(days)`
- **Arguments:** `days` (int, default 7)
- **Returns:** list[dict] — Techniques due for review within the window

#### `calculate_mastery_percentage(technique)`
- **Arguments:** `technique` (str)
- **Returns:** float — 0-100 mastery score
- **Purpose:** Weighted calculation: 50% from repetition count (capped at 30), 25% from easiness factor (normalized from 1.3-2.5 range), 25% from average quality of last 5 ratings

#### `calculate_retention_rate(technique)`
- **Arguments:** `technique` (str)
- **Returns:** float — 0-100 estimated retention percentage
- **Purpose:** Forgetting curve model: R(t) = e^(-t / S) where t is days since last practice and S = easiness_factor × (repetitions + 1) × 7

#### `get_effective_skill_level(technique)`
- **Arguments:** `technique` (str)
- **Returns:** dict — Keys: "base_level" (str from completion count), "effective_score" (float, retention-adjusted), "retention" (float), "needs_practice" (bool, true if retention < 70), "confidence" (str: "high"/"medium"/"low")
- **Purpose:** Combine hard completion thresholds (3 = beginner, 8 = intermediate, 15 = advanced, 30 = expert) with SRS retention decay to produce an effective skill assessment

***

### `services/wishlist_tracker.py` — Wishlist Price Tracking

#### `check_all_wishlist_items()`
- **Returns:** list[dict] — Alert objects for items meeting alert conditions
- **Purpose:** Iterate all active wishlist items. For each, fetch current prices from scraped data. Compare against baseline price and target price. If percentage drop exceeds threshold or target price met, generate alert. Also check if loyalty offers apply to wishlist items.

#### `check_single_item(item)`
- **Arguments:** `item` (dict) — Wishlist item record
- **Returns:** dict or None — Alert object if conditions met, None otherwise
- **Purpose:** Price comparison logic for a single item

#### `calculate_price_trends(item_id, days)`
- **Arguments:** `item_id` (int), `days` (int, default 30)
- **Returns:** dict — Keys: "trend" ("increasing"/"decreasing"/"stable"), "average_price", "lowest_price", "highest_price", "current_price"
- **Purpose:** Analyze historical price data to determine trend direction

#### `send_alerts(alerts)`
- **Arguments:** `alerts` (list[dict])
- **Returns:** None
- **Purpose:** Format and send email notifications for all triggered alerts

***

### `services/shopping_list.py` — Shopping List Generation

#### `generate_from_meal_plan(meal_plan, owned_items)`
- **Arguments:** `meal_plan` (dict) — Day-to-recipe mapping with quantities, `owned_items` (list[str]) — Items to exclude
- **Returns:** dict — Keys: store names, values: lists of shopping items
- **Purpose:** Aggregate ingredients across all recipes in the plan, exclude owned items, assign each ingredient to optimal store, consolidate duplicate items

#### `aggregate_ingredients(meal_plan)`
- **Arguments:** `meal_plan` (dict)
- **Returns:** dict — Canonical product ID to total quantity mapping
- **Purpose:** Sum quantities of each ingredient across all selected recipes for the week

#### `assign_to_stores(aggregated_ingredients, active_offers)`
- **Arguments:** `aggregated_ingredients` (dict), `active_offers` (list[dict])
- **Returns:** dict — Store-grouped shopping items with prices and offer flags
- **Purpose:** For each ingredient, compare effective price across all stores, assign to cheapest option

#### `format_for_display(store_grouped_items)`
- **Arguments:** `store_grouped_items` (dict)
- **Returns:** dict — Same structure but with display formatting (currency strings, promotion labels, store totals)

***

### `services/video_search.py` — YouTube Integration

#### `search_technique_video(technique, duration)`
- **Arguments:** `technique` (str), `duration` (str, default "short") — YouTube duration filter
- **Returns:** list[dict] — Each: "video_id", "title", "channel", "thumbnail", "embed_url"
- **Purpose:** Search YouTube Data API for technique tutorials from preferred channels

#### `search_recipe_video(recipe_name, cuisine)`
- **Arguments:** `recipe_name` (str), `cuisine` (str or None)
- **Returns:** dict or None — Best matching video
- **Purpose:** Search for full recipe walkthrough, prioritizing preferred channels list

#### `extract_timestamps(video_id)`
- **Arguments:** `video_id` (str)
- **Returns:** dict — Step index to {"time": str, "seconds": int, "description": str} mapping
- **Purpose:** Fetch video description, parse timestamp patterns (e.g., "1:23 - Prep vegetables"), return structured timestamp data

#### Variables
- `PREFERRED_CHANNELS` (list[str]) — Ordered list: "Chinese Cooking Demystified", "Serious Eats", "J. Kenji López-Alt", "RecipeTin Eats", "Ethan Chlebowski", "Adam Ragusea", "Internet Shaquille"

***

### `services/notifier.py` — Email Notifications

#### `send_email(subject, html_body)`
- **Arguments:** `subject` (str), `html_body` (str)
- **Returns:** bool — Success/failure
- **Purpose:** Send HTML email via Gmail SMTP using app password

#### `format_price_alert_email(alerts)`
- **Arguments:** `alerts` (list[dict]) — Price drop alerts
- **Returns:** str — HTML email body with product names, old/new prices, store, discount percentage, and active offers

#### `format_gift_reminder_email(gifts)`
- **Arguments:** `gifts` (list[dict]) — Upcoming gift occasions
- **Returns:** str — HTML email body with recipient, occasion, days remaining, current best price

***

### `routes/dashboard.py` — Dashboard Routes

#### `dashboard_view()`
- **Route:** GET /
- **Returns:** Rendered dashboard.html
- **Purpose:** Fetch and display: current week's meal plan, budget stats, skill progress percentages per cuisine, due technique reviews, active wishlist deals, recent alerts

***

### `routes/planner.py` — Meal Planner Routes

#### `planner_form()`
- **Route:** GET /planner
- **Returns:** Rendered planner.html with form defaults loaded from settings

#### `generate_plan()`
- **Route:** POST /planner/generate
- **Arguments (from form):** budget, protein, carbs, fat, calories, meal_counts, cuisine_focus, learning_mode
- **Returns:** Rendered planner_results.html with optimized meal plan, cost breakdown, macro summary, and shopping list

#### `accept_plan()`
- **Route:** POST /planner/accept
- **Arguments (from form):** serialized meal plan
- **Returns:** Redirect to shopping list view
- **Purpose:** Store accepted plan as current week's plan, generate final shopping list

***

### `routes/recipes.py` — Recipe Routes

#### `recipe_list()`
- **Route:** GET /recipes
- **Arguments (query params):** cuisine, difficulty, max_time, search
- **Returns:** Rendered recipes.html with filtered recipe grid

#### `recipe_detail(recipe_id)`
- **Route:** GET /recipes/<recipe_id>
- **Returns:** Rendered recipe_detail.html with full recipe, embedded video, current ingredient prices, technique descriptions

#### `recipe_create()`
- **Route:** POST /recipes/create
- **Arguments (from form):** All recipe fields
- **Returns:** Redirect to new recipe detail page

#### `recipe_complete(recipe_id)`
- **Route:** GET /recipes/<recipe_id>/complete
- **Returns:** Rendered self_assessment.html with technique rating form

#### `recipe_submit_assessment(recipe_id)`
- **Route:** POST /recipes/<recipe_id>/assess
- **Arguments (from form):** Per-technique quality ratings (0-5), notes
- **Returns:** Rendered result page showing level-ups, next review dates, mastery progress updates

***

### `routes/skills.py` — Skill Tree Routes

#### `skills_overview()`
- **Route:** GET /skills
- **Returns:** Rendered skills.html with all cuisines, progress percentages, tier status, technique mastery list, due reviews

#### `cuisine_detail(cuisine)`
- **Route:** GET /skills/uisine>
- **Returns:** Rendered cuisine detail with tier breakdown, completed recipes, available recipes, mastered and in-progress techniques

#### `practice_recommendations()`
- **Route:** GET /skills/recommendations
- **Returns:** JSON list of recommended recipes based on SRS due dates, near-level-up techniques, and decay prevention

***

### `routes/wishlist.py` — Wishlist Routes

#### `wishlist_view()`
- **Route:** GET /wishlist
- **Returns:** Rendered wishlist.html with active items table, price trends, upcoming gift occasions

#### `wishlist_add()`
- **Route:** POST /wishlist/add
- **Arguments (from form):** product_name, target_price, alert_threshold, stores, category, recipient, occasion, occasion_date
- **Returns:** Redirect to wishlist view

#### `wishlist_item_detail(item_id)`
- **Route:** GET /wishlist/<item_id>
- **Returns:** Price history chart data, trend analysis, applicable offers

#### `wishlist_mark_purchased(item_id)`
- **Route:** POST /wishlist/<item_id>/purchased
- **Returns:** Redirect to wishlist view with updated status

***

### `routes/settings.py` — Settings Routes

#### `settings_view()`
- **Route:** GET /settings
- **Returns:** Rendered settings.html with current macro targets, budget, owned items, theme, cuisine preferences, active offers

#### `save_macros()`
- **Route:** POST /settings/macros
- **Arguments (from form):** protein, carbs, fat, calories
- **Returns:** Redirect to settings with success message

#### `save_budget()`
- **Route:** POST /settings/budget
- **Arguments (from form):** weekly_budget, alert_threshold_percent
- **Returns:** Redirect to settings

#### `save_owned_items()`
- **Route:** POST /settings/owned-items
- **Arguments (from form):** items list (comma-separated or individual entries)
- **Returns:** Redirect to settings

#### `upload_offers()`
- **Route:** POST /settings/upload-offers
- **Arguments (from form):** image files (multipart)
- **Returns:** Rendered confirmation page showing extracted offers for user verification

#### `confirm_offers()`
- **Route:** POST /settings/confirm-offers
- **Arguments (from form):** verified offer list (user may have corrected)
- **Returns:** Redirect to settings with updated active offers count

#### `save_theme()`
- **Route:** POST /settings/theme
- **Arguments (from form):** theme_name ("bauhaus", "pixel-farm", "retro")
- **Returns:** JSON response (handled by JavaScript for instant theme switching)

***

### `routes/api.py` — JSON API Endpoints

#### `api_current_prices(product_id)`
- **Route:** GET /api/prices/<product_id>
- **Returns:** JSON with current prices across all stores and offer-adjusted effective prices

#### `api_price_history(product_id)`
- **Route:** GET /api/prices/<product_id>/history
- **Arguments (query params):** days, store
- **Returns:** JSON array of historical prices for chart rendering

#### `api_search_products()`
- **Route:** GET /api/products/search
- **Arguments (query params):** query
- **Returns:** JSON array of matching canonical products (for autocomplete in forms)

#### `api_technique_stats(technique)`
- **Route:** GET /api/techniques/<technique>
- **Returns:** JSON with mastery percentage, retention rate, next review date, completion count, quality history

***

### `jobs/daily_scrape.py` — Scheduled Scraping Job

#### `run_daily_scrape()`
- **Called by:** APScheduler at 03:00 AEDT daily
- **Purpose:** Load product list from database, call scraper for each store, insert new price records, log scrape results (success count, failure count, duration)

***

### `jobs/wishlist_check.py` — Scheduled Wishlist Check

#### `run_wishlist_check()`
- **Called by:** APScheduler at 03:30 AEDT daily
- **Purpose:** Call wishlist_tracker.check_all_wishlist_items(), send notifications for any triggered alerts

***

### `jobs/offer_expiry.py` — Scheduled Offer Cleanup

#### `run_offer_cleanup()`
- **Called by:** APScheduler at 04:00 AEDT daily
- **Purpose:** Call offer model expire_old_offers() to clean up past-due offers

***

### `static/js/app.js` — Global JavaScript

#### `showSection(sectionId)`
- **Arguments:** `sectionId` (str) — ID of the section element to display
- **Purpose:** Hide all sections, show target section, update navigation active state, close mobile menu, scroll to top

#### `toggleMenu()`
- **Purpose:** Toggle mobile hamburger menu open/closed

#### `changeTheme(themeName)`
- **Arguments:** `themeName` (str) — "bauhaus", "pixel-farm", "retro"
- **Purpose:** Set data-theme attribute on body element, save to localStorage, update theme selector UI active states

#### `loadSavedTheme()`
- **Purpose:** On page load, read theme from localStorage, apply to body, sync theme selector UI

***

### `static/css/main.css` — Base Styles and Theme System

#### CSS Custom Properties (Variables)
- `--primary-color` — Main brand color (buttons, headers)
- `--secondary-color` — Secondary accent
- `--accent-color` — Tertiary accent (progress bars, highlights)
- `--background-color` — Page background
- `--surface-color` — Card/component background
- `--text-primary` — Main text color
- `--text-secondary` — Muted/secondary text
- `--border-color` — Borders and dividers
- `--success-color` — Positive indicators
- `--warning-color` — Caution indicators
- `--danger-color` — Negative indicators
- `--font-primary` — Body text font family
- `--font-heading` — Heading font family
- `--spacing-xs` through `--spacing-xl` — Spacing scale
- `--radius-sm` through `--radius-lg` — Border radius scale
- `--shadow-sm` through `--shadow-lg` — Box shadow scale

#### Theme Selectors
- `:root` — Default values (Bauhaus theme)
- `[data-theme="bauhaus"]` — Explicit Bauhaus (same as default)
- `[data-theme="pixel-farm"]` — 8-bit pixel farm: monospace fonts, zero border radius, hard pixel shadows, tiled background image
- `[data-theme="retro"]` — Retro: serif/impact fonts, large border radius, colored offset shadows, warm palette

***

### `data/cuisine_skill_trees.json` — Skill Tree Definitions

#### Structure per Cuisine
- `name` (str) — Display name
- `description` (str) — What mastering this cuisine teaches
- `core_techniques` (list[str]) — Techniques central to this cuisine
- `core_ingredients` (list[str]) — Pantry items to always have on hand
- `tiers` (dict) — "beginner", "intermediate", "advanced", each containing:
  - `description` (str) — What this tier focuses on
  - `unlock_requirements` (dict) — "completed_recipes" (int), "mastered_techniques" (list[str])
  - `recipes` (list[dict]) — Each: "name", "difficulty", "techniques_taught", "key_learnings", "builds_on", "estimated_time"
  - `required_equipment` (list[str])

***

### `data/building_blocks.json` — Cooking Building Blocks

#### Structure
- `sauces` (dict) — Grouped by tradition (French mother sauces, Asian bases), each with components, technique, uses, variations
- `stocks` (dict) — Chicken stock, dashi, etc. with difficulty, time, ingredients, storage tips
- `techniques` (dict) — Grouped by type (knife skills, heat control), each with difficulty, practice instructions, associated recipes
- `flavor_profiles` (dict) — Spice blends (five-spice, garam masala) with components, flavor description, common uses

***

## Deployment Configuration

### `requirements.txt`
```
flask==3.0.*
supabase==2.*
requests==2.*
beautifulsoup4==4.*
fuzzywuzzy==0.18.*
python-Levenshtein==0.25.*
PuLP==2.*
APScheduler==3.*
openai==1.*
Pillow==10.*
gunicorn==22.*
```

### `Procfile`
```
web: gunicorn app:create_app()
```

### Environment Variables Required on Railway
```
SUPABASE_URL
SUPABASE_KEY
OPENROUTER_API_KEY
USDA_API_KEY
YOUTUBE_API_KEY
NOTIFICATION_EMAIL
EMAIL_PASSWORD
USER_EMAIL
FLASK_SECRET_KEY
```

***

## Data Flow Summary

### Weekly User Interaction
1. User uploads loyalty screenshots → `offer_parser.py` extracts offers → stored in `loyalty_offers` table
2. User clicks "Generate Plan" → `optimizer.py` reads current prices, active offers, owned items, recipe pool → runs PuLP optimization → returns meal plan + shopping list
3. User accepts plan → `shopping_list.py` generates store-split list
4. User cooks recipe → navigates to recipe detail → follows instructions with video
5. User marks recipe complete → `self_assessment.html` → quality ratings → `srs_engine.py` updates cards → `progress.py` logs completion

### Daily Automated Jobs
1. 03:00 → `daily_scrape.py` fetches ~500 product prices from Coles and Woolworths
2. 03:30 → `wishlist_check.py` compares new prices against wishlist thresholds → sends email alerts
3. 04:00 → `offer_expiry.py` cleans up expired loyalty offers

### Optimization Pipeline
1. Load recipes from database (filtered by cuisine if in learning mode)
2. Load current prices for all ingredients across all stores
3. Apply active offer adjustments to compute effective prices
4. Remove owned items from cost calculation
5. Build PuLP model: minimize Σ(recipe_count × recipe_effective_cost) subject to macro and budget constraints
6. Solve → extract selected recipes → generate aggregated shopping list → split by store
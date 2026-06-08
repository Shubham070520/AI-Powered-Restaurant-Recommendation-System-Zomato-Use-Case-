# Dataset Notes — ManikaSaini/zomato-restaurant-recommendation

Explored during Phase 1 (51,717 rows, `train` split).

## Raw columns (Hugging Face)

| Column | Example | Mapped to |
|--------|---------|-----------|
| `name` | `Jalsa` | `Restaurant.name` |
| `address` | `942, 21st Main Road, …, Bangalore` | City via `extract_city()` → `Restaurant.location` |
| `location` | `Banashankari` | `attributes.locality` (neighborhood, not city) |
| `cuisines` | `North Indian, Mughlai, Chinese` | `Restaurant.cuisines` (split on `,`) |
| `rate` | `4.1/5`, `-`, `NEW` | `Restaurant.rating` (parsed float or null) |
| `approx_cost(for two people)` | `800` | `Restaurant.cost_for_two`, `budget_tier` |
| `url` | Zomato URL | Stable `id` (hash of url) |
| `online_order`, `book_table` | `Yes` / `No` | `attributes` |
| `rest_type` | `Casual Dining` | `attributes.rest_type` |
| `listed_in(city)`, `listed_in(type)` | various | not used for v1 city filter |

## City / location policy

- User-facing **location** is the **city** (e.g. `Bangalore`), extracted from the last segments of `address`.
- `Bengaluru` / `Bangalore` spellings normalize to `Bangalore`.
- ~95% of rows are Bangalore; Delhi appears rarely in `address` text.
- Rows without a resolvable city are **skipped** (logged in preprocessor stats).

## Budget tiers (architecture defaults)

| Tier | Cost for two (INR) |
|------|---------------------|
| low | ≤ 500 |
| medium | 501 – 1500 |
| high | > 1500 |

Median cost in sample ≈ 400 INR.

## Rating policy

- Parse `4.1/5` → `4.1`.
- `-`, `NEW`, empty → `rating = null` (row kept; excluded from min-rating filter in Phase 2).
- Out of range (< 0 or > 5) → `null`.

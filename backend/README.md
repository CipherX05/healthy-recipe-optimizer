# Recipe substitution backend

Python pipeline, SQLite database and a small read-only API behind the **Recipe database** tab of the web app. Run every `python` command below from this `backend/` folder.

## Quick start

You need Python 3.10 or newer (built and tested with 3.11.9) and Node.js 20.19+ or 22.12+.

```powershell
cd backend
python -m pip install -r requirements.txt
python -m recipe_optimizer build --with-indb --title "butter chicken" --title carbonara --title stroganoff --title "mapo tofu" --title "caesar salad"
python -m recipe_optimizer serve
```

Leave the server running. In a second terminal, at the project root:

```powershell
npm ci
npm run dev        # http://localhost:3000/#demo
```

For the production build use `npm run build` and then `npm run preview` (http://localhost:4173/#demo).

The first build needs internet and takes roughly 7 minutes, mostly because requests are spaced 2 seconds apart. It caches about 81 MB under `data/raw/`. Later builds reuse the cache; add `--offline` to guarantee no network use.

If the API is not running, the web app says so and shows the original five built-in examples.

## Getting each dataset

No source needs an account, an API key or a password. The `build` command downloads everything.

| Source | How it is obtained | Licence |
| --- | --- | --- |
| [USDA FoodData Central](https://fdc.nal.usda.gov/download-datasets/), SR Legacy (April 2018) | Official bulk CSV zip, 6 MB. To update the file address, edit `USDA_SR_LEGACY_URL` in `config.py`. | Public domain (CC0 1.0) |
| [RecipeDB](https://cosylab.iiitd.edu.in/recipedb/) | No documented API and no recipe bulk file was found. Each search-results page embeds 20 recipe records as JSON, which the importer reads. | CC BY-NC-SA 3.0 |
| [FlavorDB2](https://cosylab.iiitd.edu.in/flavordb2/) | No documented API or bulk file. The importer uses two JSON addresses behind the website: `/entities?entity=` and `/entities_json?id=`. | CC BY-NC-SA 3.0 |
| [INDB](https://www.anuvaad.org.in/indian-nutrient-databank/) (optional, `--with-indb`) | Direct Excel download, 1 MB. | **No licence stated** |

**Before you reuse or share the data**

- RecipeDB and FlavorDB2 are licensed for **non-commercial** use, with attribution and share-alike. This applies to `data/recipes.db` too. `data/` is ignored by git; check these terms before you publish it.
- The RecipeDB and FlavorDB2 pages checked on 2026-11-25 stated no rule about automated access, and the server returned no `robots.txt`. That is not permission. Keep imports small, and contact [CoSyLab](https://cosylab.iiitd.edu.in/) for larger or ongoing use. The importer caches responses, waits between requests, limits `--pages` to 25 and identifies itself with a generic name.
- Their addresses are undocumented and can change. If an import returns nothing, check the parsers in `recipe_optimizer/sources/`.
- INDB's workbook holds 1,014 **cooked dishes**, not raw ingredients. It supplies only four chutney entries here. Leave out `--with-indb` if the missing licence is a concern.

USDA Foundation Foods and the FoodData Central web API are not used. SR Legacy has broader ingredient coverage and the household-measure weights needed to convert cups and spoons.

## Environment variables

All are optional, and none is a secret. To change one, copy `.env.example` at the project root to `.env`.

| Variable | Default | Purpose |
| --- | --- | --- |
| `RECIPE_DATA_DIR` | `data/` | Downloads and database. |
| `RECIPE_DB_PATH` | `data/recipes.db` | Database file. |
| `RECIPE_USER_AGENT` | generic importer name | Sent with downloads. Do not add personal details. |
| `RECIPE_REQUEST_DELAY` | `2.0` | Seconds between requests (minimum 1). |
| `RECIPE_REQUEST_TIMEOUT` | `180` | Seconds. |
| `RECIPE_CORS_ORIGINS` | local dev ports | Origins allowed to call the API directly. |
| `RECIPE_API_PROXY` | `http://127.0.0.1:8000` | Set in the shell before `npm run dev` or `preview`. |
| `VITE_API_BASE_URL` | empty | Only if the built app is hosted apart from the API. |

The API has no login and listens on `127.0.0.1` only. Do not expose it publicly as it stands.

## Database and import commands

| Command | What it does |
| --- | --- |
| `python -m recipe_optimizer init-db [--reset]` | Creates an empty schema. `build` does not need this first. `--reset` **deletes all data**. |
| `python -m recipe_optimizer build [options]` | Rebuilds the whole database from all sources. It builds a new file and swaps it in only on success. |
| `python -m recipe_optimizer import-recipes --region Japanese --pages 2` | Adds or updates recipes in an existing database. `--title "dal"` searches titles. |
| `python -m recipe_optimizer report` | Coverage, missing data and the commonest unmatched names. |
| `python -m recipe_optimizer demo --title "Indian-Style Butter Chicken (Murgh Makhani)" --goal satFat` | Prints the full workflow for one recipe. |
| `python -m recipe_optimizer network --ingredient butter` | Writes an interactive Plotly drawing to `data/network.html`. Omit `--ingredient` for the whole network. |
| `python -m recipe_optimizer serve [--port 8000]` | Starts the API. |

`build` options: `--region NAME` (repeatable), `--pages N` (20 recipes per page, default 5), `--title WORDS` (repeatable), `--with-indb`, `--skip-flavordb`, `--offline`, `--refresh`.

`build` replaces the database, so recipes added with `import-recipes` are dropped unless you pass the same `--region` or `--title` options to `build`.

## What the reference build contains (2026-11-25)

| Measure | Value |
| --- | --- |
| Recipes | 982 (about 100 each from nine regions, plus title searches) |
| Recipes with written instructions | **0** |
| Ingredient lines | 11,057 |
| Lines matched to an ingredient | 8,713 (78.8%) |
| Lines with grams **and** nutrition | 7,591 (68.7%) |
| Recipes with at least 70% of lines counted / at least 90% | 498 / 87 |
| Catalog ingredients / with nutrition | 294 / 289 |
| Ingredients with a FlavorDB2 record / with a usable one | 232 / 203 |
| Substitution network | 1,052 links |
| Recipes with an improving swap: saturated fat / calories / protein / fiber | 836 / 656 / 564 / 373 |

A new build can differ, because the live sources can change.

## How a recommendation is made

1. **Match.** `matching.py` strips quantities and preparation words, then needs an **exact** name or synonym from `catalog/ingredients.json`. There is no fuzzy matching. Words such as *dried*, *cooked* and *canned* are kept. Vague names ("milk", "oil") are matched with a stated assumption and lower confidence.
2. **Quantify.** `quantities.py` uses weight units, a printed package size, or USDA's own household measures for that food. Otherwise grams stay unknown. It never assumes the density of water or a typical can size.
3. **Find candidates.** Neighbors in the NetworkX graph: substitutable ingredients with a compatible cooking role.
4. **Filter.** A recommended candidate must:
   - improve the goal on that line by more than 2%;
   - gain at least 10 kcal, 0.5 g saturated fat, 2 g protein or 1 g fiber per 100 g replaced;
   - unless you turn guardrails off, not raise saturated fat by over 25% (and 2 g per 100 g), sodium by over 25% (and 200 mg), or calories by over 50% (and 100 kcal), where that nutrient is not the goal;
   - pass any minimum flavor or cuisine filter you set.
5. **Score.** Each score is from 0 to 1.

| Score | Calculation | Default weight |
| --- | --- | --- |
| Health | gain ÷ larger of (old amount, new amount) for the goal nutrient on that line | 0.30 |
| Flavor | Jaccard similarity of FlavorDB2 molecule IDs. No score if either set has fewer than 10 molecules | 0.35 |
| Cuisine | ln(1 + n) ÷ ln(1 + n_max), where n = imported recipes of this region using the candidate. Needs 20 recipes in the region | 0.25 |
| Role | 1.0 same role; 0.6 related role | 0.10 |

`overall = Σ weight × score`, with weights rescaled to total 1. A score with no data **earns 0**; other weights are not enlarged. The default weights are the original project's. The web app has presets and sliders.

6. **Apply.** Each line's top eligible candidate is chosen independently. A line is *relevant* if its best swap moves the recipe total by at least 1%. Whole-recipe mode keeps ingredients named in the title unless you untick that option.
7. **Compare.** For each nutrient, a line counts only if the value is known for both the original and the replacement. Swaps are **1:1 by weight, labelled as an assumption**; you can change the ratio (ranking is always done at 1:1).

The weights, thresholds, guardrails, role links and the 10-molecule cutoff are **this project's choices**. They are not taken from a database or from dietary guidance. The constants are at the top of `scoring.py` and `network.py`.

## What is external and what is not

| From an external source | Curated or estimated by this project |
| --- | --- |
| Recipes, ingredient lines, quantities, servings, region, processes (RecipeDB) | Ingredient names, synonyms and which source record each means (`catalog/ingredients.json`) |
| Nutrients and household-measure weights (USDA; INDB for four entries) | Cooking roles and which roles are related |
| Flavor molecules (FlavorDB2) | Grams computed from household measures, recipe totals, all scores, 1:1 quantities |

The catalog stores no nutrient or flavor values, and a test enforces this. Stand-in records are marked `proxy` (for example, soybean oil values for "vegetable oil") and shown as such in the app. The database keeps each line's original text, standardized name, source IDs, match method and confidence, gram method and missing-data status.

RecipeDB's own USDA codes are stored for reference but **not used**. In the reference build, all 13 lines it parsed as plain "oil" carried the code for *butter oil*. Its nutrition figures are not imported.

## Adding an ingredient

1. Run `report` to see frequent unmatched names.
2. Add an entry to `catalog/ingredients.json`: `id`, `name`, `role`, `synonyms`, the **exact** SR Legacy description in `usda`, and the exact FlavorDB2 name in `flavordb` (or `null`). Use `assumed` for vague names, `can_ok` for canned records, and `count_hint` or `cup_form` to pick a household measure.
3. Rebuild with `--offline`. A misspelled USDA name stops the build. A new FlavorDB2 name needs one online build.

## Known limitations

- **Coverage.** About 31% of lines are left out of totals: unmatched (including combined lines such as "salt and pepper"), no usable quantity ("to taste", unsized cans) or no nutrition record (such as garam masala). Compare a recipe's coverage before trusting its totals.
- **Estimates.** Raw-ingredient values only. Cooking losses, absorbed frying oil and discarded marinades are ignored, so deep-frying recipes can be badly overstated. Counted items use USDA's size, which may differ from the cook's: its only "piece" of chicken breast is 272 g.
- **Flavor.** FlavorDB2 is very uneven: it listed 1 molecule for ghee and 5 for cream. Several foods share one record (all creams, for example), which the app flags. Shared molecules do not prove similar taste.
- **Cuisine.** It reflects about 100 recipes per region. "0" means not seen in this sample, not unused in that cuisine.
- **Culinary sense.** Roles are coarse. A nutritionally valid swap can still fail in the kitchen, such as egg white for whole egg in baking. Nothing has been cooked or taste-tested, and allergens are not checked.
- **Independence.** Whole-recipe swaps are chosen one at a time, with no search over combinations.
- **Health.** Meeting one goal does not make a recipe healthier overall, and none of this is dietary advice.

## Tests

```powershell
python -B -m unittest discover -s tests -t . -v
```

67 tests cover matching, quantity conversion, nutrition totals, ranking and eligibility, the source parsers, database import and the API. They use made-up values and need no network or database.

## Troubleshooting

| Problem | Fix |
| --- | --- |
| App shows only built-in examples | Start `python -m recipe_optimizer serve`, then click **Try again**. Vite logs proxy errors while the server is off. |
| "The recipe database has not been built yet" | Run `build`. |
| Code changes have no effect | Restart `serve`; it does not reload itself. |
| File-lock or permission errors during `build` | If the project is in a synced folder such as OneDrive, pause syncing, or set `RECIPE_DATA_DIR` to a folder outside it. |
| A download fails | Run `build` again; finished downloads are cached. |

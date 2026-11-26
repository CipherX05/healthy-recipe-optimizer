# Upgrade record: from five hardcoded recipes to a recipe database

Setup, datasets, environment variables, commands and the scoring method are in [backend/README.md](../backend/README.md).

## 1. How the original worked

- A frontend-only React page with no backend or database.
- `src/data/food.ts` held the five recipes, hand-entered nutrition for each ingredient, six hand-assigned flavor values, hand-tuned cuisine affinities, fixed substitute lists and the scoring code.
- The demo drew one button per recipe and recalculated in the browser. The "worked example" section read the same data.
- The LoRA panel replays saved model outputs that exist only for those recipes. `training/` holds a Python copy of the data and rules, with file hashes as training evidence.

**Reused:** page design, selection controls, score bars, ranked list, modified-recipe and comparison layouts, the weighted-score idea and the default weights, FastAPI (already used by the training code), and the `unittest` style.

**Kept unchanged:** `food.ts`, `lora.ts`, the LoRA panel and all of `training/`. The old demo markup moved from `Optimizer.tsx` to `BuiltInDemo.tsx`; a whitespace-insensitive diff showed that only the outer `<section>` closing tag differed at the time of the move. Its footnote text was updated afterwards.

## 2. Migration plan, as carried out

1. Check how each source can really be accessed.
2. Build cached importers and a SQLite schema.
3. Add reviewed ingredient matching and evidence-based unit conversion.
4. Add scoring, eligibility rules, nutrition comparison and a NetworkX graph in Python.
5. Add a read-only FastAPI service.
6. Add a database mode to the React app, with the old demo as offline fallback.
7. Test, then audit the results across all imported recipes.

## 3. Where the result differs from the brief

| Brief | What was built and why |
| --- | --- |
| Cooking instructions "where available" | None of the 982 imported records had them. The app says so, shows RecipeDB's cooking processes and links the original page. |
| INDB for Indian ingredients | Its download has cooked dishes only, so it supplies just four chutneys. It does not improve raw Indian ingredients. Items such as garam masala still lack nutrition. |
| Plotly for comparisons | The web app uses lightweight bars in the existing style, so no charting package was added to the page. Plotly draws the exported network file. |
| USDA | The SR Legacy bulk download only. No API key, and no Foundation Foods. |
| Unified database | SQLite with the suggested entities. `categories` holds ingredient categories, `cuisine_associations` cuisines, and `substitutions` the network links. The API builds its graph from the stored ingredients. |
| Jaccard similarity | Used, but only when both profiles have at least 10 molecules. |
| Streamlit | Not used; the existing React frontend was extended. |

## 4. Files

### Changed

| File | Change |
| --- | --- |
| `src/sections/Optimizer.tsx` | Now a section shell that switches between database mode and built-in examples, and checks the server. |
| `src/sections/Hero.tsx`, `Pipeline.tsx`, `Method.tsx`, `Deliverables.tsx`, `References.tsx`, `Footer.tsx`, `Problem.tsx` | Text only, so the page matches the new system. References now credits the sources and licences. |
| `index.html` | Description text. |
| `vite.config.ts` | Forwards `/api` to the backend in `dev` and `preview`. |
| `.gitignore` | Ignores `/data/` (not `src/data/`) and keeps `.env.example` tracked. |
| `README.md` | Describes the two modes. |

### New: frontend

| File | Purpose |
| --- | --- |
| `src/components/optimizer/BuiltInDemo.tsx`, `shared.tsx` | The original demo and its score bar and gauge. |
| `src/components/database/DatabaseDemo.tsx` | State and requests for database mode. |
| `src/components/database/RecipeSearch.tsx` | Search by title, cuisine and ingredient, with pages. |
| `src/components/database/RecipeDetails.tsx` | Ingredients, grams, line-by-line sources, instructions and processes. |
| `src/components/database/ScoringControls.tsx` | Goal, scope, weights, filters and score explanations. |
| `src/components/database/Recommendations.tsx` | Ranked substitutes, evidence, selection and quantity ratio. |
| `src/components/database/Comparison.tsx` | Modified recipe, nutrition comparison and trade-offs. |
| `src/components/database/NetworkGraph.tsx` | Network drawing. |
| `src/components/database/parts.tsx`, `format.ts` | Small shared elements and formatting. |
| `src/lib/api.ts`, `src/hooks/useAsync.ts`, `useDebounced.ts` | API client and request helpers. |

### New: backend and documents

| File | Purpose |
| --- | --- |
| `backend/recipe_optimizer/sources/recipedb.py`, `usda.py`, `flavordb.py`, `indb.py` | One adapter per source. |
| `backend/recipe_optimizer/fetch.py`, `config.py` | Cached, spaced downloads; settings and source licences. |
| `backend/recipe_optimizer/matching.py`, `quantities.py` | Name matching; quantity-to-gram conversion. |
| `backend/recipe_optimizer/schema.sql`, `db.py`, `pipeline.py` | Database schema, queries and build. |
| `backend/recipe_optimizer/models.py`, `nutrition.py`, `scoring.py`, `network.py` | Calculations, ranking and NetworkX graph. |
| `backend/recipe_optimizer/service.py`, `api.py`, `cli.py`, `__init__.py`, `__main__.py` | Workflow, web API and command line. |
| `backend/recipe_optimizer/sources/__init__.py` | Package marker. |
| `backend/catalog/ingredients.json` | Reviewed names, synonyms, source-record identities and cooking roles. No nutrient values. |
| `backend/tests/` | 67 tests and their toy fixtures. |
| `backend/requirements.txt`, `backend/README.md`, `.env.example`, this file | Dependencies and documentation. |

## 5. Complete workflow: Indian-Style Butter Chicken (Murgh Makhani)

Reproduce with:

```powershell
python -m recipe_optimizer demo --title "Indian-Style Butter Chicken (Murgh Makhani)" --goal satFat
```

In the web app, search the same title and pick the **Indian Subcontinent** result. Choose **Whole recipe** to see steps 5 and 6; the app starts in single-ingredient mode.

**1. Select.** RecipeDB recipe 4040, 3 servings. No written instructions; processes begin mix → stir → melt → cook.

**2. Ingredients.** 16 lines; nutrition covers 15. Garam masala is matched but has no nutrition record, so it is left out of both totals. Examples:

| Original line | Matched to | Grams | Basis |
| --- | --- | --- | --- |
| 1 pound skinless, boneless chicken breast | Chicken breast (raw) | 453.6 | Weight unit |
| 1/2 cup butter | Butter | 113.5 | USDA cup weight |
| 1/4 cup heavy whipping cream | Heavy cream | 59.5 | USDA fluid-cream cup weight |
| 5 Roma tomatoes | Plum (Roma) tomato | 310 | 62 g each, USDA |

**3. Goal.** Reduce saturated fat, with default weights.

**4. Ranking** (top candidates; "n/a" earns no points):

| For | Candidate | Health | Flavor | Cuisine | Role | Overall |
| --- | --- | --- | --- | --- | --- | --- |
| Butter (75.1% of saturated fat) | Olive oil | 0.73 | 0.19 | 0.67 | 0.60 | 0.513 |
| | Vegetable oil | 0.70 | n/a | 0.90 | 0.60 | 0.495 |
| Heavy cream (17.7%) | Plain yogurt (whole milk) | 0.91 | n/a | 0.78 | 0.60 | 0.528 |
| | Half-and-half | 0.69 | n/a | 0.37 | 1.00 | 0.402 |
| Plain yogurt (3.3%) | Greek yogurt (nonfat) | 0.94 | 1.00 | 0.00 | 1.00 | 0.733 |

Flavor is "n/a" for the cream candidates because FlavorDB2 listed only 5 molecules for cream. The yogurt 1.00 comes from both yogurts sharing one FlavorDB2 record.

**5. Apply.** Whole-recipe mode keeps butter and chicken because both are in the title. It swaps:

- 122.5 g plain yogurt → 122.5 g nonfat Greek yogurt
- 59.5 g heavy cream → 59.5 g plain whole-milk yogurt (different cooking role; the app warns about texture)

Both use an **assumed** 1:1 weight.

**6. Compare**, estimated per serving:

| Nutrient | Original | Modified | Change |
| --- | --- | --- | --- |
| Saturated fat (goal) | 25.9 g | 20.9 g | −5.0 g (−19.2%) |
| Calories | 621 kcal | 565 kcal | −56 kcal (−9.0%) |
| Protein | 39.1 g | 41.9 g | +2.9 g (+7.3%) |
| Total fat | 43.8 g | 36.1 g | −7.7 g (−17.5%) |
| Fiber | 4.6 g | 4.6 g | no change |
| Sodium | 1511 mg | 1511 mg | no meaningful change |

Flavor similarity of swapped lines is 1.00 from **one of two** swaps, the shared-record case, so it says little. Cuisine compatibility is 0.26.

**7. Your own choice.** Butter is the largest source. Choosing olive oil for it alone lowers saturated fat by 54.9% from the original, but raises calories by 10.2% at 1:1, which the app shows as a trade-off.

## 6. How it was checked

- **67 backend tests** pass, along with the 7 original policy tests. The frontend type-check and build pass. `eslint src` reports the same 8 errors in untouched `components/ui` files as before.
- **Separate recalculation:** saturated fat, calories and protein for step 6 were recomputed from the raw USDA CSV files without the database or the nutrition code, using the grams above. They matched. This does not check the gram estimates themselves.
- **All recipes:** 982 recipes × 4 goals ran with no errors, no ineligible automatic swap and no applied swap that failed to improve its goal.
- **Browser:** scripted checks in headless Chrome covered the database workflow, the original demo (Butter Chicken cream result, 38.2%), 1280 px and 390 px layouts and the offline fallback. 24 of 25 passed. The other was a console 404 for `favicon.ico`, which the project has never had.
- **Not checked:** a single from-empty `build` after the final code changes (each downloader ran for real during development, and later rebuilds used the cache); other browsers; cooking or taste.

## 7. Problems found by auditing results, and fixed

Passing tests did not catch these. Reading the output across many recipes did.

| Problem | Fix |
| --- | --- |
| 1/4 cup heavy cream used the *whipped* weight, about half | Unusual forms are used only when the line asks for them |
| A cup of walnuts used the in-shell weight (28 g) | Same, plus a stated usual form |
| "1 large carrot" used a 3-inch strip; "1 head cabbage" a leaf | Parts are not treated as sizes; leading count nouns are read |
| Roma tomatoes counted as medium round tomatoes | Separate plum tomato entry |
| An unsized can borrowed a "typical" USDA can | Stays unknown |
| "butter - flavored shortening" matched butter | Spaced compounds are rejoined |
| "Fewer calories" or "more protein" suggested butter for olive oil; "more fiber" suggested honey for sugar | Minimum meaningful gain and guardrails |
| Parmesan → cottage cheese; yogurt → almond milk | Narrower role links |
| Flavor scores from 1 to 5 molecules looked authoritative | 10-molecule minimum and shared-record warning |

Similar errors are likely to remain among ingredients and recipes that were not inspected. Check the line-by-line sources before relying on a particular recipe's numbers.

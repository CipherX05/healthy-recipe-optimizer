# Computational Ingredient Substitution

**Group 34 · Computational Gastronomy mini-project**

This prototype recommends ingredient swaps for lower calories, lower saturated fat, higher protein, or higher fiber. It considers estimated nutrition alongside flavor and cuisine compatibility. The demo uses five built-in recipes, 44 ingredients, and preset candidates.

## Deliverables and evidence

| Deliverable | Implementation | Evidence |
| --- | --- | --- |
| **D1 · Rank substitutes** | `rankCandidates` in [food.ts](src/data/food.ts) ranks preset candidates by flavor, nutrition, cuisine, and ingredient role. | The D1 panel shows factor scores and the recommendation. For Butter Chicken cream, cashew cream ranks first with an overall score of 0.90. |
| **D2 · Modify the recipe** | `optimizeRecipe` uses the highest-ranked eligible swap for each ingredient in scope and keeps the original gram quantities. | The cream-only demo replaces 120 g of heavy cream with 120 g of cashew cream. Whole-recipe mode also replaces butter with avocado purée. |
| **D3 · Evaluate the change** | `recipeNutrition` sums nutrient values by weight. `recipeSimilarity` computes flavor and cuisine proxy scores. The UI compares values per serving. | The cream-only example reduces estimated saturated fat from 15.9 g to 9.8 g per serving, a 38.2% reduction. See report page 2 and presentation slide 4. |
| **D4 · Deliver an interactive app** | [Optimizer.tsx](src/sections/Optimizer.tsx) connects the recipe, ingredient, goal, and scope controls to D1–D3. [LoraPanel.tsx](src/components/LoraPanel.tsx) replays the saved model comparison. | The production build was tested offline at desktop, tablet, and mobile widths. The [demo capture](presentation/cream-only-demo.png) and presentation slide 5 show the workflow. |

## Tech stack and local run

The app uses React 19, TypeScript, Vite 7, Tailwind CSS 3, and bundled JSON and TypeScript data. The optimizer runs in the browser. The LoRA pilot uses Python, PyTorch, Hugging Face Transformers, PEFT, and Accelerate. The notebook includes an optional FastAPI inference script, separate from the browser demo.

Use Node.js **20.19+ on the 20.x line** or **22.12+**. The clean submission build used Node.js 24.22.3.

```powershell
npm ci
npm run build
npm run preview
```

Open [the local demo](http://localhost:4173/#demo) while the preview server runs. The default state is **Butter Chicken → Heavy cream → Reduce saturated fat → Selected ingredient only**. Click **Optimize** to jump to the D1–D3 results. The built app and recorded comparison work offline. Google Fonts fall back to installed fonts if the network is unavailable.

## Data and scoring

The bundled nutrition values are illustrative per-100 g figures. The six flavor features, cuisine affinities, and category scores are manually assigned. The app uses curated replacement lists and keeps ingredient weights fixed. The score is `0.35 × flavor + 0.30 × nutrition + 0.25 × cuisine + 0.10 × role`.

The browser selects the first eligible candidate in descending score order. With a nonzero baseline, a swap must improve the ingredient-level target nutrient by more than 2% at the same weight. A tiny denominator floor lets gains from a zero baseline qualify. Whole-recipe mode repeats the choice independently per ingredient. Reported percentages use unrounded nutrient totals. Flavor and cuisine scores are proxies. Global combination search, cooking validation, and independently verified nutrition data are outside this prototype.

## LoRA training and results

Open [the training notebook](training/Recipe_LoRA_Colab.ipynb) in Colab with a T4 GPU and run the cells in order to reproduce the workflow. The notebook embeds the source also provided in [training/ml](training/ml), including the rule teacher, training script, policy tests, and ingredient snapshot. A new run downloads the public base model separately. The recorded base model is Qwen2.5-0.5B-Instruct at revision `7ae557604adf67be50417f59c2c2f167def9a775`.

The supervised targets came from unreviewed fixed rules. Prompts supplied the candidate scores and **precomputed eligibility flags**. The model returned a JSON candidate ID or null when no candidate was eligible. The training policy excluded the ambiguous half-portion pecorino entry and used its own nutrition normalization floor. The browser uses current app rules and displays the saved comparison as a recorded run.

- **540,672** trainable parameters out of **494,573,440** (0.1093%), rank 8 and alpha 16 on the query and value projections.
- **3 epochs** and **84 optimizer updates** on a recorded Tesla T4 run. Validation completion loss fell from **0.5600** initially to its best value of **0.1262** at epoch 1.
- The family split contained 224 training records (28 queries), 24 validation records (8 queries), and **24 test order variants representing 8 queries from one held-out recipe family, Pasta Carbonara**.

| Raw held-out metric | Base model | LoRA |
| --- | ---: | ---: |
| Eligibility compliance | 21/24 (87.5%) | 24/24 (100%) |
| Exact rule agreement | 20/24 (83.3%) | 19/24 (79.2%) |
| Valid JSON and candidate ID | 24/24 (100%) | 24/24 (100%) |

Eligibility improved while exact rule agreement fell. These measurements show compliance with supplied rules on a small, repeated-order test set. Some ingredients appear across recipe families. The experiment does not establish better flavor, suitability, or generalization to new ingredients. The verified GPU run predates submission packaging. Training was not rerun for packaging.

### Training evidence

- The [run manifest](training/evidence/adapter/training_manifest.json) records parameters, updates, revision, device, hashes, and split counts.
- The [training log](training/evidence/training_loss.csv), [loss plot](training/evidence/training_loss.png), and [validation loss](training/evidence/validation_loss.json) document the recorded run.
- The [raw predictions](training/evidence/raw_test_predictions.json), [aggregate results](training/evidence/evaluation.json), and [dataset splits](training/evidence/dataset) support the metrics.
- The [adapter and tokenizer](training/evidence/adapter) come from the training export. The package excludes downloaded base-model weights.

## Submission verification

| Check | Outcome |
| --- | --- |
| Clean `npm ci`, then `npm run build` | Passed with locked Vite 7.3.0 |
| Optimizer regression checks | 44 ingredient/goal cases matched between scopes and 20 whole-recipe nutrient direction checks passed |
| Offline Chrome | Passed at 1280, 768, and 390 px with external requests blocked |
| Python rule policy | All 7 tests passed. Run `python -B -m unittest discover -s training/ml -p "test_*.py" -v` from the submission root |
| LoRA evidence | Verified SHA-256 digests for the script, adapter, snapshot, and three dataset splits and recomputed test counts from raw outputs |
| ESLint | Targeted source files passed. Full `npm run lint` reported 8 pre-existing React lint errors in UI components with the locked dependencies |

The [five-page report](34_Mini_Project_Report.pdf) and [six-slide PowerPoint](34_Mini_Project_Presentation.pptx) are at the submission root. The ZIP contains the source, presentation, report, and training evidence. It excludes local dependencies, caches, credentials, and generated build folders.

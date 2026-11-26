"""Command line: python -m recipe_optimizer <command> (run from backend/)."""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter

from . import config, db, network, pipeline
from .matching import Catalog
from .service import NotFound, Service
from .sources import recipedb


def _recipe_filters(parser: argparse.ArgumentParser, pages: int) -> None:
    parser.add_argument("--region", action="append",
                        help="RecipeDB region (repeatable). Default: a built-in list of nine")
    parser.add_argument("--pages", type=int, default=pages,
                        help="result pages per region, 20 recipes each (max 25)")
    parser.add_argument("--title", action="append", default=[], help="also import a title search")
    parser.add_argument("--offline", action="store_true", help="use cached downloads only")
    parser.add_argument("--refresh", action="store_true", help="download again, ignoring the cache")


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="python -m recipe_optimizer", description=__doc__)
    root.add_argument("-v", "--verbose", action="store_true")
    commands = root.add_subparsers(dest="command", required=True)

    init = commands.add_parser("init-db", help="create an empty database with the schema")
    init.add_argument("--reset", action="store_true", help="delete all existing data first")

    build = commands.add_parser("build", help="download (or reuse) all sources and rebuild the database")
    _recipe_filters(build, pages=5)
    build.add_argument("--with-indb", action="store_true", help="also load the optional INDB")
    build.add_argument("--skip-flavordb", action="store_true")

    more = commands.add_parser("import-recipes", help="add more RecipeDB recipes to the database")
    _recipe_filters(more, pages=1)

    commands.add_parser("report", help="show data coverage and what is missing")

    serve = commands.add_parser("serve", help="start the API used by the web app")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8000)

    graph = commands.add_parser("network", help="write the substitution network as interactive HTML")
    graph.add_argument("--ingredient", help="limit to one ingredient id, e.g. butter")
    graph.add_argument("--output", default=str(config.DATA_DIR / "network.html"))

    demo = commands.add_parser("demo", help="run the whole workflow for one recipe")
    demo.add_argument("--title", default="Butter Chicken", help="words from the recipe title")
    demo.add_argument("--id", type=int, help="database recipe id (overrides --title)")
    demo.add_argument("--goal", default="satFat", choices=["satFat", "calories", "protein", "fiber"])
    return root


def _print_stats(summary: dict) -> None:
    for key, value in summary.items():
        print(f"  {key.replace('_', ' '):28} {value:,}")


def report() -> None:
    with db.connect(must_exist=True) as connection:
        print("Database:", config.DB_PATH)
        _print_stats(db.stats(connection))
        print("\nSources")
        for row in db.source_rows(connection):
            print(f"  {row['id']:16} {row['status']:12} {row['records']:6}  {row['license']}")
        for title, column in (("Recipe lines by data status", "missing_status"),
                              ("Quantity conversion method", "grams_method"),
                              ("Name match method", "match_method")):
            print(f"\n{title}")
            for row in connection.execute(
                f"SELECT {column}, COUNT(*) FROM recipe_ingredients GROUP BY 1 ORDER BY 2 DESC"
            ):
                print(f"  {row[0]:28} {row[1]:7,}")
        print("\nMost frequent unmatched names (candidates for the catalog)")
        names = Counter(dict(connection.execute(
            "SELECT standardized_name, COUNT(*) FROM recipe_ingredients "
            "WHERE missing_status='unmatched' GROUP BY 1").fetchall()))
        print("  " + "; ".join(f"{n} ({c})" for n, c in names.most_common(20)))
        gaps = connection.execute(
            "SELECT data_status, COUNT(*) FROM ingredients GROUP BY 1 ORDER BY 2 DESC").fetchall()
        print("\nCatalog ingredients by data status:", ", ".join(f"{a}: {b}" for a, b in gaps))
        mismatch = connection.execute(
            """SELECT COUNT(*) FROM recipe_ingredients l JOIN ingredients i ON i.id = l.ingredient_id
               WHERE i.nutrition_source='usda_sr_legacy' AND l.source_ndb_id IS NOT NULL
                 AND CAST(l.source_ndb_id AS INTEGER) != CAST(i.usda_ndb_number AS INTEGER)"""
        ).fetchone()[0]
        print(f"\nMatched lines where RecipeDB's own USDA code differs from ours: {mismatch:,}")


def demo(arguments) -> int:
    service = Service()
    if arguments.id is None:
        found = service.search(query=arguments.title, limit=100)["results"]
        if not found:
            print(f"No imported recipe title contains {arguments.title!r}.", file=sys.stderr)
            return 1
        # Prefer an exact title, then the best data coverage (search order).
        wanted = arguments.title.casefold()
        recipe_id = next((r["id"] for r in found if r["title"].casefold() == wanted), found[0]["id"])
    else:
        recipe_id = arguments.id

    recipe = service.recipe(recipe_id)
    print(f"\n1. RECIPE  {recipe['title']}  (database id {recipe_id}, RecipeDB {recipe['source_id']})")
    print(f"   Cuisine: {recipe['region']} / {recipe['sub_region']}   Servings: {recipe['servings']}")
    print(f"   Original page: {recipe['source_url']}")
    print("   Instructions:", recipe["instructions"] or "not published by RecipeDB")
    print("   Processes:", " > ".join(recipe["processes"][:14]))
    print("\n2. INGREDIENTS  (grams are estimates unless the method is mass_unit)")
    for row in recipe["ingredients"]:
        grams = f"{row['grams']:7.1f} g" if row["grams"] is not None else "      ? g"
        print(f"   {grams}  {row['original_phrase'][:44]:44}  -> {row['standardized_name'][:30]:30}"
              f" [{row['missing_status']}; {row['grams_method']}]")
    coverage = recipe["coverage"]
    print(f"   Nutrition covers {coverage['counted_lines']} of {coverage['total_lines']} lines.")

    result = service.evaluate(recipe_id, arguments.goal, scope="recipe")
    print(f"\n3. GOAL  {result['goal']['label']}")
    print("   Weights:", ", ".join(f"{k} {v:.2f}" for k, v in result["weights"].items()))
    print("\n4. RANKED SUBSTITUTES for each relevant ingredient")

    def show(value):
        return " n/a" if value is None else f"{value:.2f}"

    for entry in [r for r in result["recommendations"] if r["relevant"]][:4]:
        kept = "  (named in title: kept in whole-recipe mode)" if entry["in_title"] else ""
        print(f"\n   {entry['ingredient_name']} - {entry['share_percent'] or 0:.1f}% of the recipe's "
              f"{result['goal_result']['label'].lower()}{kept}")
        print(f"      {'candidate':30} {'health':>6} {'flavor':>6} {'cuisine':>7} {'role':>5} {'overall':>7} {'recipe':>7}")
        for item in entry["candidates"][:4]:
            s = item["scores"]
            print(f"      {item['name'][:30]:30} {show(s['health']):>6} {show(s['flavor']):>6} "
                  f"{show(s['cuisine']):>7} {show(s['role']):>5} {item['overall']:7.3f} "
                  f"{item['recipe_gain_percent']:6.1f}%")
        print(f"      {entry['rejected_count']} other role-compatible ingredients were rejected.")

    print("\n5. APPLIED SWAPS")
    for swap in result["applied"]:
        print(f"   {swap['from_name']} ({swap['grams']:.0f} g) -> {swap['to_name']} "
              f"({swap['new_grams']:.0f} g)  [{swap['ratio_basis']}]")
        for note in swap["notes"]:
            print(f"      note: {note}")
    if not result["applied"]:
        print("   None: no eligible swap for this goal.")

    basis = "per serving" if result["servings"] else "whole recipe (servings unknown)"
    print(f"\n6. ORIGINAL vs MODIFIED, {basis} (estimated from raw ingredient data)")
    for row in result["comparison"]:
        if row["original"] is None:
            print(f"   {row['label']:14} no data")
            continue
        values = row["per_serving"] or row
        percent = "n/a" if row["percent_change"] is None else f"{row['percent_change']:+.1f}%"
        partial = f"  ({len(row['lines_missing_value'])} line(s) lack this value)" if row["lines_missing_value"] else ""
        print(f"   {row['label']:14} {values['original']:9.1f} -> {values['modified']:9.1f} "
              f"{row['unit']:4} change {values['change']:+8.1f}  {percent:>8}{partial}")
    goal = result["goal_result"]
    print(f"\n   Target: {goal['label']} " +
          (f"improved by {goal['gain_percent']:.1f}%." if goal["improved"] else "was not improved."))
    for item in result["tradeoffs"]:
        print(f"   Trade-off: {item['label']} changes by {item['percent_change']:+.1f}%.")
    similarity = result["similarity"]
    print(f"   Swapped ingredients: flavor similarity {show(similarity['flavor'])} "
          f"({similarity['flavor_swaps_with_data']}/{similarity['swaps']} with data), "
          f"cuisine compatibility {show(similarity['cuisine'])}")
    if similarity["flavor_same_record_swaps"]:
        print(f"   Caution: {similarity['flavor_same_record_swaps']} swap(s) share one FlavorDB2 record, "
              "so 1.00 there means FlavorDB2 cannot tell the two foods apart.")
    return 0


def main(argv: list[str] | None = None) -> int:
    arguments = parser().parse_args(argv)
    config.configure_logging(arguments.verbose)
    # Recipe text contains accents and symbols that a legacy console cannot encode.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(arguments, "pages") and not 0 <= arguments.pages <= 25:
        print("--pages must be between 0 and 25: please keep requests to the source modest.",
              file=sys.stderr)
        return 2
    try:
        if arguments.command == "init-db":
            with db.connect() as connection:
                db.init_db(connection, reset=arguments.reset)
            print("Initialised", config.DB_PATH)
        elif arguments.command == "build":
            summary = pipeline.build(
                regions=arguments.region, pages=arguments.pages, titles=arguments.title,
                with_indb=arguments.with_indb, with_flavor=not arguments.skip_flavordb,
                offline=arguments.offline, refresh=arguments.refresh,
            )
            print("\nBuilt", config.DB_PATH)
            _print_stats(summary)
        elif arguments.command == "import-recipes":
            records = recipedb.collect(arguments.region or [], arguments.pages, titles=arguments.title,
                                       offline=arguments.offline, refresh=arguments.refresh)
            with db.connect(must_exist=True) as connection:
                if not connection.execute("SELECT 1 FROM ingredients LIMIT 1").fetchone():
                    print("The database has no ingredients yet. Run 'build' first.", file=sys.stderr)
                    return 1
                count = pipeline.import_recipes(connection, Catalog.load(), records)
                pipeline.rebuild_derived(connection)
                print(f"Imported or updated {count} recipes.")
                _print_stats(db.stats(connection))
        elif arguments.command == "report":
            report()
        elif arguments.command == "serve":
            import uvicorn

            uvicorn.run("recipe_optimizer.api:app", host=arguments.host, port=arguments.port)
        elif arguments.command == "network":
            with db.connect(must_exist=True) as connection:
                graph = network.build_graph(db.load_ingredients(connection))
            network.write_html(graph, arguments.output, arguments.ingredient)
            print(f"{graph.number_of_nodes()} nodes, {graph.number_of_edges()} links.")
            print("Wrote", arguments.output)
        elif arguments.command == "demo":
            return demo(arguments)
    except (db.DatabaseNotReady, NotFound, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    return 0

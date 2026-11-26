-- Unified ingredient and recipe database. Every external value keeps its source.

CREATE TABLE IF NOT EXISTS sources (
    id            TEXT PRIMARY KEY,
    name          TEXT NOT NULL,
    url           TEXT NOT NULL,
    license       TEXT NOT NULL,
    notes         TEXT NOT NULL DEFAULT '',
    status        TEXT NOT NULL,          -- loaded | skipped | unavailable
    records       INTEGER NOT NULL DEFAULT 0,
    retrieved_at  TEXT
);

-- Ingredient categories: cooking role and family (curated by this project).
CREATE TABLE IF NOT EXISTS categories (
    role          TEXT PRIMARY KEY,
    role_label    TEXT NOT NULL,
    family        TEXT NOT NULL,
    family_label  TEXT NOT NULL,
    substitutable INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS flavor_entities (
    entity_id  INTEGER PRIMARY KEY,       -- FlavorDB2 id
    name       TEXT NOT NULL,
    category   TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS flavor_molecules (
    pubchem_id     INTEGER PRIMARY KEY,
    common_name    TEXT NOT NULL DEFAULT '',
    flavor_profile TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS entity_molecules (
    entity_id  INTEGER NOT NULL REFERENCES flavor_entities(entity_id) ON DELETE CASCADE,
    pubchem_id INTEGER NOT NULL REFERENCES flavor_molecules(pubchem_id),
    PRIMARY KEY (entity_id, pubchem_id)
);

CREATE TABLE IF NOT EXISTS ingredients (
    id                TEXT PRIMARY KEY,
    name              TEXT NOT NULL,       -- standardized name
    role              TEXT NOT NULL REFERENCES categories(role),
    also_roles        TEXT NOT NULL DEFAULT '[]',
    nutrition_source  TEXT REFERENCES sources(id),
    nutrition_match   TEXT,                -- exact | proxy
    nutrition_note    TEXT NOT NULL DEFAULT '',
    source_food_id    TEXT,                -- USDA fdc_id or INDB food_code
    source_food_name  TEXT,                -- original name in the source
    usda_ndb_number   TEXT,
    flavor_entity_id  INTEGER REFERENCES flavor_entities(entity_id),
    flavor_match      TEXT,                -- exact | proxy
    data_status       TEXT NOT NULL        -- complete | missing_nutrition | missing_flavor | missing_both
);

CREATE TABLE IF NOT EXISTS ingredient_synonyms (
    synonym_key   TEXT PRIMARY KEY,
    ingredient_id TEXT NOT NULL REFERENCES ingredients(id) ON DELETE CASCADE,
    assumption    TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS nutrients (
    ingredient_id  TEXT NOT NULL REFERENCES ingredients(id) ON DELETE CASCADE,
    nutrient       TEXT NOT NULL,
    amount         REAL NOT NULL,          -- per 100 g; an unknown value has no row
    unit           TEXT NOT NULL,
    source         TEXT NOT NULL REFERENCES sources(id),
    source_food_id TEXT NOT NULL,
    PRIMARY KEY (ingredient_id, nutrient)
);

CREATE TABLE IF NOT EXISTS portions (
    ingredient_id TEXT NOT NULL REFERENCES ingredients(id) ON DELETE CASCADE,
    description   TEXT NOT NULL,
    amount        REAL NOT NULL,
    gram_weight   REAL NOT NULL,
    source        TEXT NOT NULL REFERENCES sources(id)
);

CREATE TABLE IF NOT EXISTS recipes (
    id                 INTEGER PRIMARY KEY,
    source             TEXT NOT NULL REFERENCES sources(id),
    source_id          TEXT NOT NULL,
    title              TEXT NOT NULL,
    region             TEXT,               -- cuisine
    sub_region         TEXT,
    continent          TEXT,
    servings           REAL,
    servings_raw       TEXT,
    servings_estimated INTEGER NOT NULL DEFAULT 0,
    prep_minutes       INTEGER,
    cook_minutes       INTEGER,
    total_minutes      INTEGER,
    instructions       TEXT,               -- NULL: not published by the source
    processes          TEXT NOT NULL DEFAULT '[]',
    utensils           TEXT NOT NULL DEFAULT '[]',
    diet_tags          TEXT NOT NULL DEFAULT '[]',
    source_site        TEXT,
    source_url         TEXT,
    detail_url         TEXT,
    imported_at        TEXT NOT NULL,
    UNIQUE (source, source_id)
);

CREATE TABLE IF NOT EXISTS recipe_ingredients (
    id                INTEGER PRIMARY KEY,
    recipe_id         INTEGER NOT NULL REFERENCES recipes(id) ON DELETE CASCADE,
    position          INTEGER NOT NULL,
    original_phrase   TEXT NOT NULL,       -- exactly as published
    source_name       TEXT NOT NULL,       -- RecipeDB's parsed name
    standardized_name TEXT NOT NULL,
    ingredient_id     TEXT REFERENCES ingredients(id),
    quantity_raw      TEXT NOT NULL DEFAULT '',
    unit_raw          TEXT NOT NULL DEFAULT '',
    state             TEXT NOT NULL DEFAULT '',
    size              TEXT NOT NULL DEFAULT '',
    grams             REAL,                -- NULL: could not be established
    grams_method      TEXT NOT NULL,
    grams_note        TEXT NOT NULL DEFAULT '',
    grams_is_estimate INTEGER NOT NULL DEFAULT 1,
    match_method      TEXT NOT NULL,
    match_confidence  REAL NOT NULL,
    match_note        TEXT NOT NULL DEFAULT '',
    source_ndb_id     TEXT,                -- RecipeDB's own USDA code (provenance only)
    missing_status    TEXT NOT NULL        -- ok | unmatched | no_nutrition_data | unknown_quantity
);

-- Cuisine associations, counted from the imported recipes.
CREATE TABLE IF NOT EXISTS cuisine_associations (
    ingredient_id  TEXT NOT NULL REFERENCES ingredients(id) ON DELETE CASCADE,
    region         TEXT NOT NULL,
    recipe_count   INTEGER NOT NULL,
    region_recipes INTEGER NOT NULL,
    PRIMARY KEY (ingredient_id, region)
);

-- Edges of the substitution network (undirected, stored once).
CREATE TABLE IF NOT EXISTS substitutions (
    ingredient_a       TEXT NOT NULL REFERENCES ingredients(id) ON DELETE CASCADE,
    ingredient_b       TEXT NOT NULL REFERENCES ingredients(id) ON DELETE CASCADE,
    role_score         REAL NOT NULL,
    flavor_jaccard     REAL,
    shared_molecules   INTEGER NOT NULL,
    same_flavor_entity INTEGER NOT NULL,
    weight             REAL NOT NULL,
    PRIMARY KEY (ingredient_a, ingredient_b)
);

CREATE INDEX IF NOT EXISTS idx_recipes_title ON recipes(title COLLATE NOCASE);
CREATE INDEX IF NOT EXISTS idx_recipes_region ON recipes(region);
CREATE INDEX IF NOT EXISTS idx_lines_recipe ON recipe_ingredients(recipe_id);
CREATE INDEX IF NOT EXISTS idx_lines_ingredient ON recipe_ingredients(ingredient_id);

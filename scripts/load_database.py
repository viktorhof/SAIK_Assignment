"""
Load species and shop data into SQLite.

LLM use disclaimer: an LLM was used during this exercise; the output was
reviewed, adapted, and verified by the author.
"""

import csv
import re
import sqlite3
import time
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
SPECIES_CSV = ROOT_DIR / "data" / "raw" / "species.csv"
SHOP_CSV = ROOT_DIR / "data" / "shop" / "inventory.csv"
DB_PATH = ROOT_DIR / "data" / "plantms.db"
BATCH_SIZE = 5000


def to_text(value):
    if value is None:
        return None
    text = value.strip()
    if not text or text == "None":
        return None
    return text


def to_int(value):
    text = to_text(value)
    if text is None:
        return None
    try:
        return int(float(text))
    except ValueError:
        return None


def to_real(value):
    text = to_text(value)
    if text is None:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def to_bool(value):
    text = to_text(value)
    if text is None:
        return None
    text = text.lower()
    if text == "true":
        return 1
    if text == "false":
        return 0
    return None


def split_csv_values(value):
    text = to_text(value)
    if text is None:
        return []
    return [part.strip() for part in text.split(",") if part.strip()]


_MONTH_ABBR = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}

def split_month_values(value):
    text = to_text(value)
    if text is None:
        return []

    months = []
    for part in text.replace(",", " ").split():
        part = part.strip().lower()
        # The source has both numeric months and abbreviations.
        month_number = to_int(part)
        if month_number is None:
            month_number = _MONTH_ABBR.get(part[:3])
        if month_number is None:
            continue
        if month_number < 1 or month_number > 12:
            continue
        months.append(month_number)
    return months


def unique_values(values):
    return list(dict.fromkeys(values))


def normalize_key(value):
    if value is None:
        return ""
    lowered = value.strip().lower()
    return re.sub(r"[^a-z0-9/]+", " ", lowered).strip()


def ontology_token(value):
    parts = re.findall(r"[A-Za-z0-9]+", value)
    return "".join(part[:1].upper() + part[1:].lower() for part in parts)


GROWTH_RATE_DIM = [
    ("slow", "Slow", "SlowGrowthRate"),
    ("moderate", "Moderate", "ModerateGrowthRate"),
    ("rapid", "Rapid", "RapidGrowthRate"),
]

GROWTH_FORM_DIM = [
    ("bunch", "Bunch", "Bunch"),
    ("colonizing", "Colonizing", "Colonizing"),
    ("erect", "Erect", "Erect"),
    ("multiple_stem", "Multiple Stem", "MultipleStem"),
    ("rhizomatous", "Rhizomatous", "Rhizomatous"),
    ("single_crown", "Single Crown", "SingleCrown"),
    ("single_stem", "Single Stem", "SingleStem"),
    ("stoloniferous", "Stoloniferous", "Stoloniferous"),
    ("thicket_forming", "Thicket Forming", "ThicketForming"),
]

GROWTH_HABIT_DIM = [
    ("tree", "Tree", "Tree"),
    ("shrub", "Shrub", "Shrub"),
    ("vine", "Vine", "Vine"),
    ("subshrub", "Subshrub", "Subshrub"),
    ("forb_herb", "Forb/Herb", "ForbHerb"),
    ("graminoid", "Graminoid", "Graminoid"),
    ("nonvascular", "Nonvascular", "Nonvascular"),
]

FOLIAGE_TEXTURE_DIM = [
    ("fine", "Fine", "FineTexture"),
    ("medium", "Medium", "MediumTexture"),
    ("coarse", "Coarse", "CoarseTexture"),
]

EDIBLE_PART_DIM = [
    ("flower", "Flower", "FlowerPart", "EdibleFlowersUse"),
    ("fruit", "Fruit", "FruitPart", "EdibleFruitsUse"),
    ("leaf", "Leaf", "LeafPart", "EdibleLeavesUse"),
    ("root", "Root", "RootPart", "EdibleRootsUse"),
    ("seed", "Seed", "SeedPart", "EdibleSeedsUse"),
    ("stem", "Stem", "StemPart", "EdibleStemsUse"),
    ("tuber", "Tuber", "TuberPart", "EdibleTubersUse"),
]

CARE_LEVEL_DIM = [
    ("easy", "Easy", "EasyCare"),
    ("medium", "Medium", "MediumCare"),
    ("hard", "Hard", "HardCare"),
]

TEMPERATURE_CATEGORY_DIM = [
    ("warm", "Warm", "WarmCategory"),
    ("cool", "Cool", "CoolCategory"),
    ("moderate", "Moderate", "ModerateCategory"),
]

MONTH_DIM = [
    (1, "January", "January"),
    (2, "February", "February"),
    (3, "March", "March"),
    (4, "April", "April"),
    (5, "May", "May"),
    (6, "June", "June"),
    (7, "July", "July"),
    (8, "August", "August"),
    (9, "September", "September"),
    (10, "October", "October"),
    (11, "November", "November"),
    (12, "December", "December"),
]


def build_dim_label_map(rows):
    return {normalize_key(label): code for code, label, _ in rows}


def build_lower_label_map(rows):
    return {label.lower(): code for code, label, _ in rows}


GROWTH_RATE_MAP = build_dim_label_map(GROWTH_RATE_DIM)
GROWTH_FORM_MAP = build_dim_label_map(GROWTH_FORM_DIM)
FOLIAGE_TEXTURE_MAP = build_dim_label_map(FOLIAGE_TEXTURE_DIM)
CARE_LEVEL_MAP = build_lower_label_map(CARE_LEVEL_DIM)
TEMPERATURE_CATEGORY_MAP = build_lower_label_map(TEMPERATURE_CATEGORY_DIM)

GROWTH_HABIT_MAP = {
    "tree": "tree",
    "shrub": "shrub",
    "vine": "vine",
    "subshrub": "subshrub",
    "forb/herb": "forb_herb",
    "forb herb": "forb_herb",
    "graminoid": "graminoid",
    "nonvascular": "nonvascular",
}

EDIBLE_PART_MAP = {
    "flower": "flower",
    "flowers": "flower",
    "fruit": "fruit",
    "fruits": "fruit",
    "leaf": "leaf",
    "leaves": "leaf",
    "root": "root",
    "roots": "root",
    "seed": "seed",
    "seeds": "seed",
    "stem": "stem",
    "stems": "stem",
    "tuber": "tuber",
    "tubers": "tuber",
}


DDL = [
    """
    CREATE TABLE family (
        family_id INTEGER PRIMARY KEY,
        family_name TEXT NOT NULL UNIQUE,
        family_common_name TEXT
    );
    """,
    """
    CREATE TABLE genus (
        genus_id INTEGER PRIMARY KEY,
        genus_name TEXT NOT NULL,
        family_id INTEGER NOT NULL REFERENCES family(family_id),
        UNIQUE(genus_name, family_id)
    );
    """,
    """
    CREATE TABLE growth_rate_dim (
        code TEXT PRIMARY KEY,
        label TEXT NOT NULL,
        ontology_suffix TEXT NOT NULL UNIQUE
    );
    """,
    """
    CREATE TABLE growth_form_dim (
        code TEXT PRIMARY KEY,
        label TEXT NOT NULL,
        ontology_suffix TEXT NOT NULL UNIQUE
    );
    """,
    """
    CREATE TABLE growth_habit_dim (
        code TEXT PRIMARY KEY,
        label TEXT NOT NULL,
        ontology_suffix TEXT NOT NULL UNIQUE
    );
    """,
    """
    CREATE TABLE foliage_texture_dim (
        code TEXT PRIMARY KEY,
        label TEXT NOT NULL,
        ontology_suffix TEXT NOT NULL UNIQUE
    );
    """,
    """
    CREATE TABLE edible_part_dim (
        code TEXT PRIMARY KEY,
        label TEXT NOT NULL,
        part_ontology_suffix TEXT NOT NULL UNIQUE,
        use_ontology_suffix TEXT NOT NULL UNIQUE
    );
    """,
    """
    CREATE TABLE care_level_dim (
        code TEXT PRIMARY KEY,
        label TEXT NOT NULL,
        ontology_suffix TEXT NOT NULL UNIQUE
    );
    """,
    """
    CREATE TABLE temperature_category_dim (
        code TEXT PRIMARY KEY,
        label TEXT NOT NULL,
        ontology_suffix TEXT NOT NULL UNIQUE
    );
    """,
    """
    CREATE TABLE month_dim (
        month_number INTEGER PRIMARY KEY,
        label TEXT NOT NULL UNIQUE,
        ontology_suffix TEXT NOT NULL UNIQUE
    );
    """,
    """
    CREATE TABLE flower_color_dim (
        code TEXT PRIMARY KEY,
        label TEXT NOT NULL UNIQUE,
        ontology_suffix TEXT NOT NULL UNIQUE
    );
    """,
    """
    CREATE TABLE fruit_color_dim (
        code TEXT PRIMARY KEY,
        label TEXT NOT NULL UNIQUE,
        ontology_suffix TEXT NOT NULL UNIQUE
    );
    """,
    """
    CREATE TABLE foliage_color_dim (
        code TEXT PRIMARY KEY,
        label TEXT NOT NULL UNIQUE,
        ontology_suffix TEXT NOT NULL UNIQUE
    );
    """,
    """
    CREATE TABLE region (
        region_id INTEGER PRIMARY KEY,
        region_name TEXT NOT NULL UNIQUE
    );
    """,
    """
    CREATE TABLE plant (
        plant_id INTEGER PRIMARY KEY,
        scientific_name TEXT,
        rank TEXT,
        genus_id INTEGER REFERENCES genus(genus_id),
        family_id INTEGER REFERENCES family(family_id),
        year INTEGER,
        author TEXT,
        bibliography TEXT,
        primary_common_name TEXT,
        image_url TEXT,
        ground_humidity INTEGER,
        growth_form_code TEXT REFERENCES growth_form_dim(code),
        growth_rate_code TEXT REFERENCES growth_rate_dim(code),
        vegetable INTEGER,
        edible INTEGER,
        light INTEGER,
        soil_nutriments INTEGER,
        soil_salinity INTEGER,
        anaerobic_tolerance INTEGER,
        atmospheric_humidity INTEGER,
        average_height_cm REAL,
        maximum_height_cm REAL,
        minimum_root_depth_cm REAL,
        ph_maximum REAL,
        ph_minimum REAL,
        planting_days_to_harvest INTEGER,
        planting_row_spacing_cm REAL,
        planting_spread_cm REAL,
        url_wikipedia_en TEXT
    );
    """,
    """
    CREATE TABLE plant_common_name (
        plant_id INTEGER NOT NULL REFERENCES plant(plant_id),
        common_name TEXT NOT NULL,
        is_primary INTEGER NOT NULL DEFAULT 0,
        PRIMARY KEY (plant_id, common_name)
    );
    """,
    """
    CREATE TABLE plant_synonym (
        plant_id INTEGER NOT NULL REFERENCES plant(plant_id),
        synonym_name TEXT NOT NULL,
        PRIMARY KEY (plant_id, synonym_name)
    );
    """,
    """
    CREATE TABLE plant_growth_habit (
        plant_id INTEGER NOT NULL REFERENCES plant(plant_id),
        growth_habit_code TEXT NOT NULL REFERENCES growth_habit_dim(code),
        PRIMARY KEY (plant_id, growth_habit_code)
    );
    """,
    """
    CREATE TABLE plant_bloom_month (
        plant_id INTEGER NOT NULL REFERENCES plant(plant_id),
        month_number INTEGER NOT NULL REFERENCES month_dim(month_number),
        PRIMARY KEY (plant_id, month_number)
    );
    """,
    """
    CREATE TABLE plant_fruit_month (
        plant_id INTEGER NOT NULL REFERENCES plant(plant_id),
        month_number INTEGER NOT NULL REFERENCES month_dim(month_number),
        PRIMARY KEY (plant_id, month_number)
    );
    """,
    """
    CREATE TABLE plant_growth_month (
        plant_id INTEGER NOT NULL REFERENCES plant(plant_id),
        month_number INTEGER NOT NULL REFERENCES month_dim(month_number),
        PRIMARY KEY (plant_id, month_number)
    );
    """,
    """
    CREATE TABLE plant_edible_part (
        plant_id INTEGER NOT NULL REFERENCES plant(plant_id),
        edible_part_code TEXT NOT NULL REFERENCES edible_part_dim(code),
        PRIMARY KEY (plant_id, edible_part_code)
    );
    """,
    """
    CREATE TABLE flower_component (
        plant_id INTEGER PRIMARY KEY REFERENCES plant(plant_id),
        conspicuous INTEGER
    );
    """,
    """
    CREATE TABLE plant_flower_color (
        plant_id INTEGER NOT NULL REFERENCES flower_component(plant_id),
        color_code TEXT NOT NULL REFERENCES flower_color_dim(code),
        PRIMARY KEY (plant_id, color_code)
    );
    """,
    """
    CREATE TABLE fruit_component (
        plant_id INTEGER PRIMARY KEY REFERENCES plant(plant_id),
        conspicuous INTEGER
    );
    """,
    """
    CREATE TABLE plant_fruit_color (
        plant_id INTEGER NOT NULL REFERENCES fruit_component(plant_id),
        color_code TEXT NOT NULL REFERENCES fruit_color_dim(code),
        PRIMARY KEY (plant_id, color_code)
    );
    """,
    """
    CREATE TABLE foliage_component (
        plant_id INTEGER PRIMARY KEY REFERENCES plant(plant_id),
        texture_code TEXT REFERENCES foliage_texture_dim(code)
    );
    """,
    """
    CREATE TABLE plant_foliage_color (
        plant_id INTEGER NOT NULL REFERENCES foliage_component(plant_id),
        color_code TEXT NOT NULL REFERENCES foliage_color_dim(code),
        PRIMARY KEY (plant_id, color_code)
    );
    """,
    """
    CREATE TABLE plant_distribution (
        plant_id INTEGER NOT NULL REFERENCES plant(plant_id),
        region_id INTEGER NOT NULL REFERENCES region(region_id),
        PRIMARY KEY (plant_id, region_id)
    );
    """,
    """
    CREATE TABLE shop_product (
        product_id INTEGER PRIMARY KEY,
        plant_id INTEGER NOT NULL REFERENCES plant(plant_id),
        product_name TEXT NOT NULL,
        stock_quantity INTEGER NOT NULL,
        price_eur REAL NOT NULL,
        shelf_date TEXT NOT NULL,
        care_level_code TEXT REFERENCES care_level_dim(code),
        temperature_category_code TEXT REFERENCES temperature_category_dim(code)
    );
    """,
]


INDEXES = [
    "CREATE INDEX idx_family_name ON family(family_name);",
    "CREATE INDEX idx_genus_name ON genus(genus_name);",
    "CREATE INDEX idx_plant_genus_id ON plant(genus_id);",
    "CREATE INDEX idx_plant_family_id ON plant(family_id);",
    "CREATE INDEX idx_plant_growth_rate_code ON plant(growth_rate_code);",
    "CREATE INDEX idx_plant_growth_form_code ON plant(growth_form_code);",
    "CREATE INDEX idx_plant_common_name_name ON plant_common_name(common_name);",
    "CREATE INDEX idx_plant_synonym_name ON plant_synonym(synonym_name);",
    "CREATE INDEX idx_plant_distribution_region ON plant_distribution(region_id);",
    "CREATE INDEX idx_shop_product_plant_id ON shop_product(plant_id);",
]


INSERT_SQL = {
    "plant": """
        INSERT INTO plant VALUES (
            ?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?
        );
    """,
    "plant_common_name": """
        INSERT OR IGNORE INTO plant_common_name VALUES (?,?,?);
    """,
    "plant_synonym": """
        INSERT OR IGNORE INTO plant_synonym VALUES (?,?);
    """,
    "plant_growth_habit": """
        INSERT OR IGNORE INTO plant_growth_habit VALUES (?,?);
    """,
    "plant_bloom_month": """
        INSERT OR IGNORE INTO plant_bloom_month VALUES (?,?);
    """,
    "plant_fruit_month": """
        INSERT OR IGNORE INTO plant_fruit_month VALUES (?,?);
    """,
    "plant_growth_month": """
        INSERT OR IGNORE INTO plant_growth_month VALUES (?,?);
    """,
    "plant_edible_part": """
        INSERT OR IGNORE INTO plant_edible_part VALUES (?,?);
    """,
    "flower_component": """
        INSERT OR REPLACE INTO flower_component VALUES (?,?);
    """,
    "plant_flower_color": """
        INSERT OR IGNORE INTO plant_flower_color VALUES (?,?);
    """,
    "fruit_component": """
        INSERT OR REPLACE INTO fruit_component VALUES (?,?);
    """,
    "plant_fruit_color": """
        INSERT OR IGNORE INTO plant_fruit_color VALUES (?,?);
    """,
    "foliage_component": """
        INSERT OR REPLACE INTO foliage_component VALUES (?,?);
    """,
    "plant_foliage_color": """
        INSERT OR IGNORE INTO plant_foliage_color VALUES (?,?);
    """,
    "plant_distribution": """
        INSERT OR IGNORE INTO plant_distribution VALUES (?,?);
    """,
    "shop_product": """
        INSERT OR REPLACE INTO shop_product VALUES (?,?,?,?,?,?,?,?);
    """,
}


def seed_dimensions(cursor):
    cursor.executemany("INSERT INTO growth_rate_dim VALUES (?,?,?)", GROWTH_RATE_DIM)
    cursor.executemany("INSERT INTO growth_form_dim VALUES (?,?,?)", GROWTH_FORM_DIM)
    cursor.executemany("INSERT INTO growth_habit_dim VALUES (?,?,?)", GROWTH_HABIT_DIM)
    cursor.executemany("INSERT INTO foliage_texture_dim VALUES (?,?,?)", FOLIAGE_TEXTURE_DIM)
    cursor.executemany("INSERT INTO edible_part_dim VALUES (?,?,?,?)", EDIBLE_PART_DIM)
    cursor.executemany("INSERT INTO care_level_dim VALUES (?,?,?)", CARE_LEVEL_DIM)
    cursor.executemany("INSERT INTO temperature_category_dim VALUES (?,?,?)", TEMPERATURE_CATEGORY_DIM)
    cursor.executemany("INSERT INTO month_dim VALUES (?,?,?)", MONTH_DIM)


def create_loader_state(cursor):
    return {
        "cursor": cursor,
        "family_cache": {},
        "genus_cache": {},
        "region_cache": {},
        "flower_color_cache": {},
        "fruit_color_cache": {},
        "foliage_color_cache": {},
    }


def get_or_create_family(state, family_name, family_common_name):
    cache = state["family_cache"]
    cursor = state["cursor"]

    if family_name in cache:
        family_id = cache[family_name]
        if family_common_name:
            cursor.execute(
                """
                UPDATE family
                SET family_common_name = COALESCE(family_common_name, ?)
                WHERE family_id = ?
                """,
                (family_common_name, family_id),
            )
        return family_id

    cursor.execute(
        """
        INSERT INTO family (family_name, family_common_name)
        VALUES (?, ?)
        ON CONFLICT(family_name) DO UPDATE
        SET family_common_name = COALESCE(family.family_common_name, excluded.family_common_name)
        """,
        (family_name, family_common_name),
    )

    row = cursor.execute(
        "SELECT family_id FROM family WHERE family_name = ?",
        (family_name,),
    ).fetchone()
    family_id = row[0]
    cache[family_name] = family_id
    return family_id


def get_or_create_genus(state, genus_name, family_id):
    cache = state["genus_cache"]
    cursor = state["cursor"]
    cache_key = (genus_name, family_id)

    if cache_key in cache:
        return cache[cache_key]

    cursor.execute(
        """
        INSERT OR IGNORE INTO genus (genus_name, family_id)
        VALUES (?, ?)
        """,
        (genus_name, family_id),
    )

    row = cursor.execute(
        """
        SELECT genus_id
        FROM genus
        WHERE genus_name = ? AND family_id = ?
        """,
        (genus_name, family_id),
    ).fetchone()
    genus_id = row[0]
    cache[cache_key] = genus_id
    return genus_id


def get_or_create_region(state, region_name):
    cache = state["region_cache"]
    cursor = state["cursor"]

    if region_name in cache:
        return cache[region_name]

    cursor.execute(
        "INSERT OR IGNORE INTO region (region_name) VALUES (?)",
        (region_name,),
    )

    row = cursor.execute(
        "SELECT region_id FROM region WHERE region_name = ?",
        (region_name,),
    ).fetchone()
    region_id = row[0]
    cache[region_name] = region_id
    return region_id


def get_or_create_color(state, table_name, cache_name, label, prefix):
    cursor = state["cursor"]
    cache = state[cache_name]
    clean_label = label.strip()

    if clean_label in cache:
        return cache[clean_label]

    code = re.sub(r"[^a-z0-9]+", "_", clean_label.lower()).strip("_")
    if not code:
        code = "unknown_" + str(len(cache) + 1)

    ontology_suffix = prefix + ontology_token(clean_label)

    cursor.execute(
        f"""
        INSERT OR IGNORE INTO {table_name} (code, label, ontology_suffix)
        VALUES (?, ?, ?)
        """,
        (code, clean_label, ontology_suffix),
    )

    cache[clean_label] = code
    return code


def flush_batches(cursor, batches):
    inserted_rows = 0

    for table_name in batches:
        rows = batches[table_name]
        if not rows:
            continue
        cursor.executemany(INSERT_SQL[table_name], rows)
        inserted_rows += len(rows)
        rows.clear()

    return inserted_rows


def collect_color_codes(state, raw_value, table_name, cache_name, prefix):
    colors = unique_values(split_csv_values(raw_value))
    return [
        get_or_create_color(state, table_name, cache_name, color, prefix)
        for color in colors
    ]


def load_species(cursor):
    if not SPECIES_CSV.exists():
        raise FileNotFoundError(
            "Missing species CSV: " + str(SPECIES_CSV)
        )

    state = create_loader_state(cursor)
    batches = {table_name: [] for table_name in INSERT_SQL if table_name != "shop_product"}
    loaded_rows = 0
    skipped_rows = 0
    start_time = time.time()

    print("Loading species from " + SPECIES_CSV.name + " ...")
    with open(SPECIES_CSV, newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")

        for row in reader:
            plant_id = to_int(row.get("id"))
            if plant_id is None:
                skipped_rows += 1
                continue

            family_id = None
            family_name = to_text(row.get("family"))
            family_common_name = to_text(row.get("family_common_name"))
            if family_name:
                family_id = get_or_create_family(state, family_name, family_common_name)

            genus_id = None
            genus_name = to_text(row.get("genus"))
            if genus_name and family_id is not None:
                genus_id = get_or_create_genus(state, genus_name, family_id)

            growth_rate_code = GROWTH_RATE_MAP.get(normalize_key(row.get("growth_rate")))
            growth_form_code = GROWTH_FORM_MAP.get(normalize_key(row.get("growth_form")))

            batches["plant"].append(
                (
                    plant_id,
                    to_text(row.get("scientific_name")),
                    to_text(row.get("rank")),
                    genus_id,
                    family_id,
                    to_int(row.get("year")),
                    to_text(row.get("author")),
                    to_text(row.get("bibliography")),
                    to_text(row.get("common_name")),
                    to_text(row.get("image_url")),
                    to_int(row.get("ground_humidity")),
                    growth_form_code,
                    growth_rate_code,
                    to_bool(row.get("vegetable")),
                    to_bool(row.get("edible")),
                    to_int(row.get("light")),
                    to_int(row.get("soil_nutriments")),
                    to_int(row.get("soil_salinity")),
                    to_int(row.get("anaerobic_tolerance")),
                    to_int(row.get("atmospheric_humidity")),
                    to_real(row.get("average_height_cm")),
                    to_real(row.get("maximum_height_cm")),
                    to_real(row.get("minimum_root_depth_cm")),
                    to_real(row.get("ph_maximum")),
                    to_real(row.get("ph_minimum")),
                    to_int(row.get("planting_days_to_harvest")),
                    to_real(row.get("planting_row_spacing_cm")),
                    to_real(row.get("planting_spread_cm")),
                    to_text(row.get("url_wikipedia_en")),
                )
            )

            seen_names = set()
            primary_common_name = to_text(row.get("common_name"))
            if primary_common_name:
                seen_names.add(primary_common_name)
                batches["plant_common_name"].append((plant_id, primary_common_name, 1))
            for common_name in split_csv_values(row.get("common_names")):
                if common_name in seen_names:
                    continue
                seen_names.add(common_name)
                batches["plant_common_name"].append((plant_id, common_name, 0))

            for synonym_name in unique_values(split_csv_values(row.get("synonyms"))):
                batches["plant_synonym"].append((plant_id, synonym_name))

            for habit in unique_values(split_csv_values(row.get("growth_habit"))):
                habit_code = GROWTH_HABIT_MAP.get(normalize_key(habit))
                if habit_code is not None:
                    batches["plant_growth_habit"].append((plant_id, habit_code))

            for month_number in unique_values(split_month_values(row.get("bloom_months"))):
                batches["plant_bloom_month"].append((plant_id, month_number))
            for month_number in unique_values(split_month_values(row.get("fruit_months"))):
                batches["plant_fruit_month"].append((plant_id, month_number))
            for month_number in unique_values(split_month_values(row.get("growth_months"))):
                batches["plant_growth_month"].append((plant_id, month_number))

            for edible_part in unique_values(split_csv_values(row.get("edible_part"))):
                edible_part_code = EDIBLE_PART_MAP.get(normalize_key(edible_part))
                if edible_part_code is not None:
                    batches["plant_edible_part"].append((plant_id, edible_part_code))

            flower_colors = collect_color_codes(
                state,
                row.get("flower_color"),
                "flower_color_dim",
                "flower_color_cache",
                "FlowerColor_",
            )
            flower_conspicuous = to_bool(row.get("flower_conspicuous"))
            if flower_colors or flower_conspicuous is not None:
                batches["flower_component"].append((plant_id, flower_conspicuous))
                for color_code in flower_colors:
                    batches["plant_flower_color"].append((plant_id, color_code))

            fruit_colors = collect_color_codes(
                state,
                row.get("fruit_color"),
                "fruit_color_dim",
                "fruit_color_cache",
                "FruitColor_",
            )
            fruit_conspicuous = to_bool(row.get("fruit_conspicuous"))
            if fruit_colors or fruit_conspicuous is not None:
                batches["fruit_component"].append((plant_id, fruit_conspicuous))
                for color_code in fruit_colors:
                    batches["plant_fruit_color"].append((plant_id, color_code))

            foliage_colors = collect_color_codes(
                state,
                row.get("foliage_color"),
                "foliage_color_dim",
                "foliage_color_cache",
                "FoliageColor_",
            )
            foliage_texture_code = FOLIAGE_TEXTURE_MAP.get(normalize_key(row.get("foliage_texture")))
            if foliage_colors or foliage_texture_code is not None:
                batches["foliage_component"].append((plant_id, foliage_texture_code))
                for color_code in foliage_colors:
                    batches["plant_foliage_color"].append((plant_id, color_code))

            for region_name in unique_values(split_csv_values(row.get("distributions"))):
                region_id = get_or_create_region(state, region_name)
                batches["plant_distribution"].append((plant_id, region_id))

            loaded_rows += 1
            if loaded_rows % BATCH_SIZE == 0:
                flush_batches(cursor, batches)
                print(f"  ... {loaded_rows:,} species processed", end="\r")

    flush_batches(cursor, batches)
    elapsed_seconds = time.time() - start_time
    print(f"  Species loaded: {loaded_rows:,} rows (skipped {skipped_rows}) [{elapsed_seconds:.1f}s]")


def load_shop_inventory(cursor):
    if not SHOP_CSV.exists():
        raise FileNotFoundError(
            "Missing shop inventory CSV: "
            + str(SHOP_CSV)
            + ". Run scripts/generate_shop_data.py first."
        )

    rows = []

    with open(SHOP_CSV, newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)

        for row in reader:
            care_level_text = to_text(row.get("care_level"))
            temperature_text = to_text(row.get("temperature_category"))

            product_id = to_int(row.get("product_id"))
            plant_id = to_int(row.get("trefle_id"))
            stock_quantity = to_int(row.get("stock_quantity"))
            price_eur = to_real(row.get("price_eur"))
            product_name = to_text(row.get("product_name"))
            shelf_date = to_text(row.get("shelf_date"))

            if product_id is None:
                raise ValueError("Invalid product_id in shop inventory row")
            if plant_id is None:
                raise ValueError("Invalid trefle_id in shop inventory row")
            if stock_quantity is None:
                raise ValueError("Invalid stock_quantity in shop inventory row")
            if price_eur is None:
                raise ValueError("Invalid price_eur in shop inventory row")
            if product_name is None:
                raise ValueError("Missing product_name in shop inventory row")
            if shelf_date is None:
                raise ValueError("Missing shelf_date in shop inventory row")

            rows.append(
                (
                    product_id,
                    plant_id,
                    product_name,
                    stock_quantity,
                    price_eur,
                    shelf_date,
                    CARE_LEVEL_MAP.get((care_level_text or "").lower()),
                    TEMPERATURE_CATEGORY_MAP.get((temperature_text or "").lower()),
                )
            )

    cursor.executemany(INSERT_SQL["shop_product"], rows)
    print(f"  Shop inventory loaded: {len(rows)} rows")


def print_summary(cursor):
    table_names = [
        "family",
        "genus",
        "plant",
        "plant_common_name",
        "plant_synonym",
        "plant_growth_habit",
        "plant_bloom_month",
        "plant_fruit_month",
        "plant_growth_month",
        "plant_edible_part",
        "flower_component",
        "plant_flower_color",
        "fruit_component",
        "plant_fruit_color",
        "foliage_component",
        "plant_foliage_color",
        "region",
        "plant_distribution",
        "shop_product",
    ]

    print("\nDatabase: " + str(DB_PATH))

    for table_name in table_names:
        row = cursor.execute("SELECT COUNT(*) FROM " + table_name).fetchone()
        count = row[0]
        print(f"  {table_name:<20} {count:,}")

    joined_row = cursor.execute(
        """
        SELECT COUNT(*)
        FROM shop_product sp
        JOIN plant p ON p.plant_id = sp.plant_id
        """
    ).fetchone()
    joined_count = joined_row[0]
    db_size_mb = DB_PATH.stat().st_size / 1048576

    print(f"  File size            {db_size_mb:.1f} MB")
    print(f"  shop <> plant joins  {joined_count:,}")
def main():
    if DB_PATH.exists():
        DB_PATH.unlink()
        print("Removed existing " + DB_PATH.name)

    connection = sqlite3.connect(DB_PATH)

    try:
        cursor = connection.cursor()
        cursor.execute("PRAGMA foreign_keys = ON;")

        for ddl_statement in DDL:
            cursor.execute(ddl_statement)
        seed_dimensions(cursor)
        connection.commit()

        load_species(cursor)
        connection.commit()

        print("Loading shop inventory from " + SHOP_CSV.name + " ...")
        load_shop_inventory(cursor)
        connection.commit()

        print("Creating indexes ...")
        for index_statement in INDEXES:
            cursor.execute(index_statement)
        connection.commit()

        print_summary(cursor)
    finally:
        connection.close()


if __name__ == "__main__":
    main()

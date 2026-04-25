"""
Load both data sources into SQLite for Step 2 OBDA.

Creates : data/plantms.db
Tables  : species        — all 416k rows from data/raw/species.csv
          shop_inventory — all rows from data/shop/inventory.csv

Run with: python3 scripts/load_database.py
Requires: only Python stdlib (csv, sqlite3, pathlib)

Columns omitted from species (not mapped in ontology):
  planting_description, planting_sowing_description,
  url_usda, url_tropicos, url_tela_botanica, url_powo,
  url_plantnet, url_gbif, url_openfarm, url_catminat
"""

import csv
import sqlite3
import time
from pathlib import Path

SPECIES_CSV   = Path(__file__).parent.parent / "data" / "raw" / "species.csv"
SHOP_CSV      = Path(__file__).parent.parent / "data" / "shop" / "inventory.csv"
DB_PATH       = Path(__file__).parent.parent / "data" / "plantms.db"
BATCH_SIZE    = 5_000   # rows per executemany call

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def to_int(v):
    """Convert CSV value to int, returning None for empty/None strings."""
    v = v.strip()
    if not v or v == "None":
        return None
    try:
        return int(float(v))
    except ValueError:
        return None

def to_real(v):
    """Convert CSV value to float, returning None for empty/None strings."""
    v = v.strip()
    if not v or v == "None":
        return None
    try:
        return float(v)
    except ValueError:
        return None

def to_bool(v):
    """Convert 'true'/'false' CSV string to 1/0 integer, None if missing."""
    v = v.strip().lower()
    if v == "true":
        return 1
    if v == "false":
        return 0
    return None

def to_text(v):
    """Return stripped string or None if empty."""
    v = v.strip()
    return v if v else None

# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

DDL_SPECIES = """
CREATE TABLE IF NOT EXISTS species (
    id                      INTEGER PRIMARY KEY,
    scientific_name         TEXT,
    rank                    TEXT,
    genus                   TEXT,
    family                  TEXT,
    year                    INTEGER,
    author                  TEXT,
    bibliography            TEXT,
    common_name             TEXT,
    family_common_name      TEXT,
    image_url               TEXT,
    flower_color            TEXT,
    flower_conspicuous      INTEGER,    -- 1/0/NULL
    foliage_color           TEXT,
    foliage_texture         TEXT,
    fruit_color             TEXT,
    fruit_conspicuous       INTEGER,    -- 1/0/NULL
    fruit_months            TEXT,       -- space-separated month numbers
    bloom_months            TEXT,       -- space-separated month numbers
    ground_humidity         INTEGER,
    growth_form             TEXT,
    growth_habit            TEXT,       -- comma-separated (e.g. "Tree,Shrub")
    growth_months           TEXT,       -- space-separated month numbers
    growth_rate             TEXT,
    edible_part             TEXT,       -- comma-separated
    vegetable               INTEGER,    -- 1/0/NULL
    edible                  INTEGER,    -- 1/0/NULL
    light                   INTEGER,
    soil_nutriments         INTEGER,
    soil_salinity           INTEGER,
    anaerobic_tolerance     INTEGER,
    atmospheric_humidity    INTEGER,
    average_height_cm       REAL,
    maximum_height_cm       REAL,
    minimum_root_depth_cm   REAL,
    ph_maximum              REAL,
    ph_minimum              REAL,
    planting_days_to_harvest INTEGER,
    planting_row_spacing_cm REAL,
    planting_spread_cm      REAL,
    synonyms                TEXT,
    distributions           TEXT,       -- comma-separated region names
    common_names            TEXT,
    url_wikipedia_en        TEXT
);
"""

DDL_SHOP = """
CREATE TABLE IF NOT EXISTS shop_inventory (
    product_id          INTEGER PRIMARY KEY,
    trefle_id           INTEGER REFERENCES species(id),
    scientific_name     TEXT,
    product_name        TEXT,
    stock_quantity      INTEGER,
    price_eur           REAL,
    shelf_date          TEXT,           -- ISO date string: YYYY-MM-DD
    care_level          TEXT,           -- Easy / Medium / Hard
    temperature_category TEXT           -- Warm / Cool / Moderate
);
"""

DDL_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_species_genus  ON species(genus);",
    "CREATE INDEX IF NOT EXISTS idx_species_family ON species(family);",
    "CREATE INDEX IF NOT EXISTS idx_shop_trefle_id ON shop_inventory(trefle_id);",
]

# ---------------------------------------------------------------------------
# Column mapping for species CSV
# Positions confirmed from header (0-based):
#   0:id 1:scientific_name 2:rank 3:genus 4:family 5:year 6:author
#   7:bibliography 8:common_name 9:family_common_name 10:image_url
#   11:flower_color 12:flower_conspicuous 13:foliage_color 14:foliage_texture
#   15:fruit_color 16:fruit_conspicuous 17:fruit_months 18:bloom_months
#   19:ground_humidity 20:growth_form 21:growth_habit 22:growth_months
#   23:growth_rate 24:edible_part 25:vegetable 26:edible 27:light
#   28:soil_nutriments 29:soil_salinity 30:anaerobic_tolerance
#   31:atmospheric_humidity 32:average_height_cm 33:maximum_height_cm
#   34:minimum_root_depth_cm 35:ph_maximum 36:ph_minimum
#   37:planting_days_to_harvest 38:planting_description (SKIP)
#   39:planting_sowing_description (SKIP) 40:planting_row_spacing_cm
#   41:planting_spread_cm 42:synonyms 43:distributions 44:common_names
#   45:url_usda (SKIP) 46:url_tropicos (SKIP) 47:url_tela_botanica (SKIP)
#   48:url_powo (SKIP) 49:url_plantnet (SKIP) 50:url_gbif (SKIP)
#   51:url_openfarm (SKIP) 52:url_catminat (SKIP) 53:url_wikipedia_en
# ---------------------------------------------------------------------------

def parse_species_row(r):
    """Convert a raw TSV row list into the tuple for INSERT."""
    if len(r) < 54:
        r = r + [""] * (54 - len(r))  # pad short rows
    return (
        to_int(r[0]),    # id
        to_text(r[1]),   # scientific_name
        to_text(r[2]),   # rank
        to_text(r[3]),   # genus
        to_text(r[4]),   # family
        to_int(r[5]),    # year
        to_text(r[6]),   # author
        to_text(r[7]),   # bibliography
        to_text(r[8]),   # common_name
        to_text(r[9]),   # family_common_name
        to_text(r[10]),  # image_url
        to_text(r[11]),  # flower_color
        to_bool(r[12]),  # flower_conspicuous
        to_text(r[13]),  # foliage_color
        to_text(r[14]),  # foliage_texture
        to_text(r[15]),  # fruit_color
        to_bool(r[16]),  # fruit_conspicuous
        to_text(r[17]),  # fruit_months
        to_text(r[18]),  # bloom_months
        to_int(r[19]),   # ground_humidity
        to_text(r[20]),  # growth_form
        to_text(r[21]),  # growth_habit
        to_text(r[22]),  # growth_months
        to_text(r[23]),  # growth_rate
        to_text(r[24]),  # edible_part
        to_bool(r[25]),  # vegetable
        to_bool(r[26]),  # edible
        to_int(r[27]),   # light
        to_int(r[28]),   # soil_nutriments
        to_int(r[29]),   # soil_salinity
        to_int(r[30]),   # anaerobic_tolerance
        to_int(r[31]),   # atmospheric_humidity
        to_real(r[32]),  # average_height_cm
        to_real(r[33]),  # maximum_height_cm
        to_real(r[34]),  # minimum_root_depth_cm
        to_real(r[35]),  # ph_maximum
        to_real(r[36]),  # ph_minimum
        to_int(r[37]),   # planting_days_to_harvest
        to_real(r[40]),  # planting_row_spacing_cm  (38,39 skipped)
        to_real(r[41]),  # planting_spread_cm
        to_text(r[42]),  # synonyms
        to_text(r[43]),  # distributions
        to_text(r[44]),  # common_names
        to_text(r[53]),  # url_wikipedia_en          (45-52 skipped)
    )

INSERT_SPECIES = """
INSERT OR IGNORE INTO species VALUES (
    ?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?
);
"""

INSERT_SHOP = """
INSERT OR REPLACE INTO shop_inventory VALUES (?,?,?,?,?,?,?,?,?);
"""

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    if DB_PATH.exists():
        DB_PATH.unlink()
        print(f"Removed existing {DB_PATH.name}")

    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    # Create tables
    cur.execute(DDL_SPECIES)
    cur.execute(DDL_SHOP)
    con.commit()

    # ---- Load species ----
    print(f"Loading species from {SPECIES_CSV.name} …")
    t0 = time.time()
    batch = []
    total = 0
    skipped = 0

    with open(SPECIES_CSV, newline="", encoding="utf-8") as f:
        reader = csv.reader(f, delimiter="\t")
        next(reader)  # skip header
        for raw in reader:
            parsed = parse_species_row(raw)
            if parsed[0] is None:   # skip rows with no id
                skipped += 1
                continue
            batch.append(parsed)
            if len(batch) >= BATCH_SIZE:
                cur.executemany(INSERT_SPECIES, batch)
                total += len(batch)
                batch = []
                print(f"  … {total:,} rows inserted", end="\r")

        if batch:
            cur.executemany(INSERT_SPECIES, batch)
            total += len(batch)

    con.commit()
    elapsed = time.time() - t0
    print(f"  Species loaded: {total:,} rows  (skipped {skipped})  [{elapsed:.1f}s]")

    # ---- Load shop inventory ----
    print(f"Loading shop inventory from {SHOP_CSV.name} …")
    shop_rows = []
    with open(SHOP_CSV, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            shop_rows.append((
                int(r["product_id"]),
                int(r["trefle_id"]),
                r["scientific_name"] or None,
                r["product_name"] or None,
                int(r["stock_quantity"]),
                float(r["price_eur"]),
                r["shelf_date"] or None,
                r["care_level"] or None,
                r["temperature_category"] or None,
            ))
    cur.executemany(INSERT_SHOP, shop_rows)
    con.commit()
    print(f"  Shop inventory loaded: {len(shop_rows)} rows")

    # ---- Create indexes ----
    print("Creating indexes …")
    for ddl in DDL_INDEXES:
        cur.execute(ddl)
    con.commit()

    # ---- Summary ----
    sp_count   = cur.execute("SELECT COUNT(*) FROM species").fetchone()[0]
    sh_count   = cur.execute("SELECT COUNT(*) FROM shop_inventory").fetchone()[0]
    db_size_mb = DB_PATH.stat().st_size / 1_048_576
    print(f"\nDatabase: {DB_PATH}")
    print(f"  species        : {sp_count:,} rows")
    print(f"  shop_inventory : {sh_count:,} rows")
    print(f"  File size      : {db_size_mb:.1f} MB")

    # Quick join check
    joined = cur.execute("""
        SELECT COUNT(*)
        FROM shop_inventory s
        JOIN species p ON p.id = s.trefle_id
    """).fetchone()[0]
    print(f"  shop ⋈ species : {joined} rows matched (of {sh_count} shop rows)")

    con.close()

if __name__ == "__main__":
    main()

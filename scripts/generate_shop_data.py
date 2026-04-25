"""
Generate mock shop inventory for "Grüner Daumen" — a small Vienna corner plant shop.

Output : data/shop/inventory.csv
Requires: only Python stdlib (csv, random, datetime)
Run with: python3 scripts/generate_shop_data.py

The trefle_id column is a FK to species.csv id and is the OBDA join key.
Care level is derived from Trefle ecological data where available.
Temperature category is assigned per family (not in Trefle CSV).
Shelf dates are seeded so some products are >90 days old (needed for CQ11).
"""

import csv
import random
from datetime import date, timedelta
from pathlib import Path

random.seed(42)

# ---------------------------------------------------------------------------
# Target genera
# Fields: genus, family, max_items, product_name, price_min, price_max,
#         care_override (None = derive from Trefle data), temp_override
# ---------------------------------------------------------------------------
TARGETS = [
    # Araceae — tropical houseplants (Warm)
    ("Monstera",      "Araceae",       3, "Monstera",           18.99, 79.99, None,   "Warm"),
    ("Spathiphyllum", "Araceae",       2, "Peace Lily",          9.99, 24.99, "Easy", "Warm"),
    ("Philodendron",  "Araceae",       3, "Philodendron",        12.99, 34.99, None,  "Warm"),
    ("Epipremnum",    "Araceae",       2, "Pothos",               8.99, 19.99, "Easy","Warm"),
    ("Zamioculcas",   "Araceae",       2, "ZZ Plant",            14.99, 29.99, "Easy","Warm"),
    ("Aglaonema",     "Araceae",       2, "Chinese Evergreen",    9.99, 24.99, "Easy","Warm"),
    ("Alocasia",      "Araceae",       2, "Alocasia",            14.99, 44.99, None,  "Warm"),
    ("Anthurium",     "Araceae",       2, "Anthurium",           12.99, 34.99, None,  "Warm"),
    # Orchidaceae — top sellers (Warm)
    ("Phalaenopsis",  "Orchidaceae",   5, "Moth Orchid",         12.99, 29.99, None,  "Warm"),
    ("Cymbidium",     "Orchidaceae",   3, "Cymbidium Orchid",    18.99, 44.99, None,  "Warm"),
    ("Dendrobium",    "Orchidaceae",   2, "Dendrobium Orchid",   14.99, 34.99, None,  "Warm"),
    # Lamiaceae — herb corner (Cool)
    ("Lavandula",     "Lamiaceae",     2, "Lavender",             3.99,  8.99, "Easy","Cool"),
    ("Salvia",        "Lamiaceae",     2, "Rosemary",             3.49,  7.99, "Easy","Cool"),
    ("Ocimum",        "Lamiaceae",     2, "Basil",                2.99,  4.99, "Easy","Cool"),
    ("Mentha",        "Lamiaceae",     2, "Mint",                 2.99,  4.99, "Easy","Cool"),
    ("Thymus",        "Lamiaceae",     2, "Thyme",                2.99,  4.99, "Easy","Cool"),
    ("Origanum",      "Lamiaceae",     1, "Oregano",              2.99,  4.99, "Easy","Cool"),
    # Asphodelaceae — succulents (Moderate)
    ("Aloe",          "Asphodelaceae", 3, "Aloe Vera",            5.99, 19.99, "Easy","Moderate"),
    ("Haworthia",     "Asphodelaceae", 2, "Haworthia",            4.99, 12.99, "Easy","Moderate"),
    # Cactaceae (Moderate)
    ("Mammillaria",   "Cactaceae",     3, "Mammillaria Cactus",   4.99, 12.99, "Easy","Moderate"),
    ("Echinopsis",    "Cactaceae",     2, "Echinopsis Cactus",    5.99, 14.99, "Easy","Moderate"),
    ("Opuntia",       "Cactaceae",     2, "Prickly Pear",         4.99,  9.99, "Easy","Moderate"),
    ("Cereus",        "Cactaceae",     1, "Cereus Cactus",        6.99, 19.99, "Easy","Moderate"),
    # Geraniaceae — Vienna window boxes (Moderate)
    ("Pelargonium",   "Geraniaceae",   6, "Geranium",             4.99, 12.99, "Easy","Moderate"),
    # Asparagaceae (Moderate)
    ("Sansevieria",   "Asparagaceae",  3, "Snake Plant",          8.99, 34.99, "Easy","Moderate"),
    ("Chlorophytum",  "Asparagaceae",  2, "Spider Plant",         6.99, 12.99, "Easy","Moderate"),
    ("Yucca",         "Asparagaceae",  2, "Yucca",               14.99, 49.99, "Easy","Moderate"),
    # Moraceae — statement plants (Warm)
    ("Ficus",         "Moraceae",      4, "Ficus",               14.99, 59.99, None,  "Warm"),
    # Rosaceae — roses (Cool)
    ("Rosa",          "Rosaceae",      4, "Rose",                 8.99, 24.99, None,  "Cool"),
    # Apiaceae — herb corner (Cool)
    ("Petroselinum",  "Apiaceae",      2, "Parsley",              2.99,  4.99, "Easy","Cool"),
    ("Coriandrum",    "Apiaceae",      1, "Coriander",            2.99,  4.99, "Easy","Cool"),
    ("Anethum",       "Apiaceae",      1, "Dill",                 2.99,  4.99, "Easy","Cool"),
    # Primulaceae (Cool)
    ("Primula",       "Primulaceae",   3, "Primrose",             4.99,  8.99, "Easy","Cool"),
    ("Cyclamen",      "Primulaceae",   2, "Cyclamen",             6.99, 14.99, "Easy","Cool"),
    # Others — variety
    ("Begonia",       "Begoniaceae",   3, "Begonia",              5.99, 14.99, None,  "Moderate"),
    ("Kalanchoe",     "Crassulaceae",  2, "Kalanchoe",            5.99,  9.99, "Easy","Moderate"),
    ("Tradescantia",  "Commelinaceae", 2, "Tradescantia",         5.99,  9.99, "Easy","Moderate"),
    ("Hedera",        "Araliaceae",    2, "Ivy",                  5.99, 12.99, "Easy","Cool"),
    ("Oxalis",        "Oxalidaceae",   1, "Oxalis",               4.99,  8.99, "Easy","Moderate"),
    ("Strelitzia",    "Strelitziaceae",2, "Bird of Paradise",    24.99, 79.99, None,  "Warm"),
    ("Pachira",       "Malvaceae",     2, "Money Tree",          14.99, 44.99, "Easy","Warm"),
]

# Column indices in species.csv (0-based, TSV)
COL = {
    "id": 0, "scientific_name": 1, "genus": 3, "family": 4,
    "light": 27, "soil_nutriments": 28, "anaerobic_tolerance": 30,
    "atmospheric_humidity": 31, "growth_habit": 21,
}

# ---------------------------------------------------------------------------
# Date helpers
# ---------------------------------------------------------------------------
START_DATE = date(2025, 10, 1)
CUT_DATE   = date(2026, 1, 24)   # products on shelf before this are >90 days old
END_DATE   = date(2026, 4, 15)

def random_old_date():
    """Return a date before the 90-day cutoff (for CQ11)."""
    span = (CUT_DATE - START_DATE).days
    return START_DATE + timedelta(days=random.randint(0, span))

def random_recent_date():
    """Return a date after the 90-day cutoff."""
    span = (END_DATE - CUT_DATE).days
    return CUT_DATE + timedelta(days=random.randint(1, span))

# ---------------------------------------------------------------------------
# Care level derivation from Trefle numeric columns
# ---------------------------------------------------------------------------
def derive_care(row, override):
    if override:
        return override
    def _int(col):
        v = row[COL[col]].strip()
        if v and v not in ("", "None"):
            try:
                return int(float(v))
            except ValueError:
                pass
        return None
    light = _int("light")
    soil  = _int("soil_nutriments")
    anaer = _int("anaerobic_tolerance")
    # Hard: low light tolerance OR very anaerobic
    if (light is not None and light < 4) or (anaer is not None and anaer > 6):
        return "Hard"
    # Easy: good light tolerance AND good soil nutriment tolerance
    if (light is not None and light >= 7) and (soil is not None and soil >= 5):
        return "Easy"
    # Medium: any data present but not extreme
    if light is not None or soil is not None:
        return "Medium"
    # No data: default Medium
    return "Medium"

# ---------------------------------------------------------------------------
# Read species.csv and collect matching rows per genus
# ---------------------------------------------------------------------------
CSV_PATH = Path(__file__).parent.parent / "data" / "raw" / "species.csv"
OUT_DIR  = Path(__file__).parent.parent / "data" / "shop"
OUT_PATH = OUT_DIR / "inventory.csv"

print("Reading species.csv …")
target_genera = {t[0] for t in TARGETS}
genus_rows: dict[str, list] = {g: [] for g in target_genera}

with open(CSV_PATH, newline="", encoding="utf-8") as f:
    reader = csv.reader(f, delimiter="\t")
    next(reader)  # skip header
    for row in reader:
        if len(row) <= COL["genus"]:
            continue
        genus = row[COL["genus"]].strip()
        if genus in genus_rows:
            genus_rows[genus].append(row)

found = {g: len(rows) for g, rows in genus_rows.items() if rows}
print(f"  Genera found: {len(found)}/{len(target_genera)}")
missing = target_genera - set(found)
if missing:
    print(f"  Not found (skipped): {sorted(missing)}")

# ---------------------------------------------------------------------------
# Build inventory
# ---------------------------------------------------------------------------
OUT_DIR.mkdir(parents=True, exist_ok=True)

FIELDNAMES = [
    "product_id", "trefle_id", "scientific_name", "product_name",
    "stock_quantity", "price_eur", "shelf_date", "care_level", "temperature_category",
]

inventory = []
product_id = 1001

# Families that should get old shelf dates to satisfy CQ11
OLD_DATE_FAMILIES = {"Araceae", "Orchidaceae", "Moraceae", "Strelitziaceae", "Malvaceae"}

for genus, family, max_items, product_name, p_min, p_max, care_override, temp in TARGETS:
    rows = genus_rows.get(genus, [])
    if not rows:
        continue

    # Shuffle to get variety; take up to max_items
    sample = random.sample(rows, min(max_items, len(rows)))

    for i, row in enumerate(sample):
        trefle_id     = row[COL["id"]].strip()
        scientific    = row[COL["scientific_name"]].strip()
        care          = derive_care(row, care_override)

        # Orchid stock: ensure each line has a decent amount for CQ13
        if family == "Orchidaceae":
            stock = random.randint(3, 8)
        else:
            stock = random.randint(2, 12)

        price = round(random.uniform(p_min, p_max), 2)

        # First item of each warm-family genus gets an old shelf date for CQ11
        if family in OLD_DATE_FAMILIES and i == 0:
            shelf = random_old_date()
        else:
            shelf = random_recent_date()

        # Map care/temp strings to ontology IRI labels used in inventory
        care_iri = {"Easy": "Easy", "Medium": "Medium", "Hard": "Hard"}[care]
        temp_iri = temp  # Warm / Cool / Moderate

        inventory.append({
            "product_id":           product_id,
            "trefle_id":            trefle_id,
            "scientific_name":      scientific,
            "product_name":         product_name,
            "stock_quantity":       stock,
            "price_eur":            f"{price:.2f}",
            "shelf_date":           shelf.isoformat(),
            "care_level":           care_iri,
            "temperature_category": temp_iri,
        })
        product_id += 1

# ---------------------------------------------------------------------------
# Write CSV
# ---------------------------------------------------------------------------
with open(OUT_PATH, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
    writer.writeheader()
    writer.writerows(inventory)

print(f"\nInventory written to: {OUT_PATH}")
print(f"  Total rows: {len(inventory)}")

# ---------------------------------------------------------------------------
# CQ coverage summary
# ---------------------------------------------------------------------------
import collections

family_stock: dict[str, int] = collections.defaultdict(int)
for t in TARGETS:
    genus, family = t[0], t[1]
    for item in inventory:
        # match by product_name prefix (quick approximation)
        if item["product_name"] == t[3]:
            family_stock[family] += int(item["stock_quantity"])

orchid_stock = sum(int(r["stock_quantity"]) for r in inventory
                   if any(r["trefle_id"] == row[COL["id"]]
                          for row in genus_rows.get("Phalaenopsis", []) +
                                     genus_rows.get("Cymbidium", []) +
                                     genus_rows.get("Dendrobium", [])))

araceae_items = [r for r in inventory
                 if any(r["trefle_id"] == row[COL["id"]]
                        for row in (genus_rows.get("Monstera", []) +
                                    genus_rows.get("Spathiphyllum", []) +
                                    genus_rows.get("Philodendron", []) +
                                    genus_rows.get("Epipremnum", []) +
                                    genus_rows.get("Zamioculcas", []) +
                                    genus_rows.get("Aglaonema", []) +
                                    genus_rows.get("Alocasia", []) +
                                    genus_rows.get("Anthurium", [])))]
araceae_stock = sum(int(r["stock_quantity"]) for r in araceae_items)

warm_old = [r for r in inventory
            if r["temperature_category"] == "Warm"
            and r["shelf_date"] < CUT_DATE.isoformat()]

vine_cheap = [r for r in inventory
              if float(r["price_eur"]) < 30.0
              and r["product_name"] in ("Pothos", "Ivy")]

print(f"\n  CQ11 — Warm + shelf >90 days:      {len(warm_old)} product(s)")
print(f"  CQ12 — Araceae total stock:         {araceae_stock} units")
print(f"  CQ13 — Orchid total stock:          {orchid_stock} units (need >5)")
print(f"  CQ14 — Vine plants <€30:            {len(vine_cheap)} product(s) "
      f"(growth_habit from Trefle)")
print()
print("  Note: CQ11 atmospheric_humidity filter applies at SPARQL query time")
print("        via JOIN with Trefle species table.")

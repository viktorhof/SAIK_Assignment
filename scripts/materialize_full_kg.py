#!/usr/bin/env python3
"""
Materialize the full Plant Management ABox from the SQLite database.

Ontop is the preferred OBDA materializer for the assignment. In this project
Ontop 5.4.0 currently fails against SQLite when materializing predicates that
are produced by several triples maps. This script follows the same normalized
database schema and R2RML predicate choices directly, so the full KG can still
be generated reproducibly for GraphDB import and SHACL validation.
"""

import sqlite3
import time
from pathlib import Path
from urllib.parse import quote

from rdflib import Literal, URIRef
from rdflib.namespace import RDF, RDFS, XSD


ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "plantms.db"
OUTPUT_PATH = ROOT / "data" / "plantms_full_kg.ttl"

PLANT = "http://www.semanticweb.org/plantms/ontology#"
RESOURCE = "http://www.semanticweb.org/plantms/resource/"


def iri(value):
    return "<" + str(value) + ">"


def segment(value):
    return quote(str(value), safe="")


def plant_iri(plant_id):
    return iri(RESOURCE + "plant/" + segment(plant_id))


def family_iri(family_name):
    return iri(RESOURCE + "family/" + segment(family_name))


def genus_iri(genus_name):
    return iri(RESOURCE + "genus/" + segment(genus_name))


def region_iri(region_id):
    return iri(RESOURCE + "region/" + segment(region_id))


def distribution_iri(plant_id, region_id):
    return iri(RESOURCE + "distribution/" + segment(plant_id) + "/" + segment(region_id))


def product_iri(product_id):
    return iri(RESOURCE + "product/" + segment(product_id))


def flower_iri(plant_id):
    return iri(RESOURCE + "flower/" + segment(plant_id))


def foliage_iri(plant_id):
    return iri(RESOURCE + "foliage/" + segment(plant_id))


def fruit_iri(plant_id):
    return iri(RESOURCE + "fruit/" + segment(plant_id))


def ontology_iri(suffix):
    return iri(PLANT + segment(suffix))


def literal(value, datatype=None):
    if datatype is None:
        return Literal(value).n3()
    return Literal(value, datatype=datatype).n3()


def bool_literal(value):
    return literal("true" if int(value) else "false", XSD.boolean)


def write_triple(output, subject, predicate, object_value):
    output.write(subject + " " + predicate + " " + object_value + " .\n")


def write_literal(output, subject, predicate, value, datatype=None):
    if value is None or value == "":
        return 0
    write_triple(output, subject, predicate, literal(value, datatype))
    return 1


def write_iri(output, subject, predicate, object_value):
    if object_value is None or object_value == "":
        return 0
    write_triple(output, subject, predicate, object_value)
    return 1


def materialize_query(connection, output, label, query, writer):
    started = time.time()
    count = 0
    cursor = connection.execute(query)
    for row in cursor:
        count += writer(output, row)
    elapsed = time.time() - started
    print(f"{label}: {count:,} triples ({elapsed:.1f}s)")
    return count


def plant_writer(output, row):
    subject = plant_iri(row["plant_id"])
    count = 0
    write_triple(output, subject, iri(RDF.type), iri(PLANT + "Plant"))
    count += 1
    count += write_literal(output, subject, iri(RDFS.label), row["scientific_name"])
    count += write_literal(output, subject, iri(PLANT + "hasTrefleId"), row["plant_id"], XSD.integer)
    count += write_literal(output, subject, iri(PLANT + "hasScientificName"), row["scientific_name"])
    count += write_literal(output, subject, iri(PLANT + "hasYear"), row["year"], XSD.integer)
    count += write_literal(output, subject, iri(PLANT + "hasAuthor"), row["author"])
    count += write_literal(output, subject, iri(PLANT + "hasBibliography"), row["bibliography"])
    count += write_literal(output, subject, iri(PLANT + "hasImageUrl"), row["image_url"], XSD.anyURI)
    count += write_literal(output, subject, iri(PLANT + "hasWikipediaUrl"), row["url_wikipedia_en"], XSD.anyURI)
    count += write_literal(output, subject, iri(PLANT + "hasAverageHeightCm"), row["average_height_cm"], XSD.decimal)
    count += write_literal(output, subject, iri(PLANT + "hasMaximumHeightCm"), row["maximum_height_cm"], XSD.decimal)
    count += write_literal(output, subject, iri(PLANT + "hasMinimumRootDepthCm"), row["minimum_root_depth_cm"], XSD.decimal)
    count += write_literal(output, subject, iri(PLANT + "hasLightRequirement"), row["light"], XSD.integer)
    count += write_literal(output, subject, iri(PLANT + "hasSoilNutriments"), row["soil_nutriments"], XSD.integer)
    count += write_literal(output, subject, iri(PLANT + "hasSoilSalinity"), row["soil_salinity"], XSD.integer)
    count += write_literal(output, subject, iri(PLANT + "hasGroundHumidity"), row["ground_humidity"], XSD.integer)
    count += write_literal(output, subject, iri(PLANT + "hasAtmosphericHumidity"), row["atmospheric_humidity"], XSD.integer)
    count += write_literal(output, subject, iri(PLANT + "hasAnaerobicTolerance"), row["anaerobic_tolerance"], XSD.integer)
    count += write_literal(output, subject, iri(PLANT + "hasPhMinimum"), row["ph_minimum"], XSD.decimal)
    count += write_literal(output, subject, iri(PLANT + "hasPhMaximum"), row["ph_maximum"], XSD.decimal)
    count += write_literal(output, subject, iri(PLANT + "hasPlantingDaysToHarvest"), row["planting_days_to_harvest"], XSD.integer)
    count += write_literal(output, subject, iri(PLANT + "hasPlantingRowSpacingCm"), row["planting_row_spacing_cm"], XSD.decimal)
    count += write_literal(output, subject, iri(PLANT + "hasPlantingSpreadCm"), row["planting_spread_cm"], XSD.decimal)
    count += write_literal(output, subject, iri(PLANT + "isEdible"), row["edible"], XSD.boolean)
    count += write_literal(output, subject, iri(PLANT + "isVegetable"), row["vegetable"], XSD.boolean)
    if row["family_name"]:
        count += write_iri(output, subject, iri(PLANT + "belongsToFamily"), family_iri(row["family_name"]))
    if row["genus_name"]:
        count += write_iri(output, subject, iri(PLANT + "belongsToGenus"), genus_iri(row["genus_name"]))
    return count


def family_writer(output, row):
    subject = family_iri(row["family_name"])
    count = 0
    write_triple(output, subject, iri(RDF.type), iri(PLANT + "Family"))
    count += 1
    count += write_literal(output, subject, iri(RDFS.label), row["family_name"])
    count += write_literal(output, subject, iri(PLANT + "hasFamilyCommonName"), row["family_common_name"])
    return count


def genus_writer(output, row):
    subject = genus_iri(row["genus_name"])
    count = 0
    write_triple(output, subject, iri(RDF.type), iri(PLANT + "Genus"))
    count += 1
    count += write_literal(output, subject, iri(RDFS.label), row["genus_name"])
    count += write_iri(output, subject, iri(PLANT + "isSubsumedByFamily"), family_iri(row["family_name"]))
    return count


def component_writer(kind, class_name, label_predicate):
    def writer(output, row):
        if kind == "flower":
            subject = flower_iri(row["plant_id"])
        elif kind == "foliage":
            subject = foliage_iri(row["plant_id"])
        else:
            subject = fruit_iri(row["plant_id"])
        count = 0
        write_triple(output, subject, iri(RDF.type), iri(PLANT + class_name))
        count += 1
        count += write_literal(output, subject, iri(RDFS.label), row["scientific_name"])
        count += write_iri(output, subject, iri(PLANT + "isComponentOf"), plant_iri(row["plant_id"]))
        if label_predicate:
            count += write_literal(output, subject, iri(PLANT + label_predicate), row["conspicuous"], XSD.boolean)
        return count
    return writer


def shop_product_writer(output, row):
    subject = product_iri(row["product_id"])
    count = 0
    write_triple(output, subject, iri(RDF.type), iri(PLANT + "ShopProduct"))
    count += 1
    count += write_literal(output, subject, iri(RDFS.label), row["product_name"])
    count += write_literal(output, subject, iri(PLANT + "hasProductId"), row["product_id"], XSD.integer)
    count += write_literal(output, subject, iri(PLANT + "hasProductName"), row["product_name"])
    count += write_literal(output, subject, iri(PLANT + "hasStockQuantity"), row["stock_quantity"], XSD.integer)
    count += write_literal(output, subject, iri(PLANT + "hasPriceEur"), row["price_eur"], XSD.decimal)
    count += write_literal(output, subject, iri(PLANT + "hasShelfDate"), row["shelf_date"], XSD.date)
    count += write_iri(output, subject, iri(PLANT + "isShopProductFor"), plant_iri(row["plant_id"]))
    if row["care_suffix"]:
        count += write_iri(output, subject, iri(PLANT + "hasCareLevel"), ontology_iri(row["care_suffix"]))
    if row["temperature_suffix"]:
        count += write_iri(output, subject, iri(PLANT + "hasTemperatureCategory"), ontology_iri(row["temperature_suffix"]))
    count += write_iri(output, plant_iri(row["plant_id"]), iri(PLANT + "hasShopProduct"), subject)
    return count


def main():
    if not DB_PATH.exists():
        raise SystemExit(f"Database not found: {DB_PATH}")

    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row

    total = 0
    started = time.time()
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    with open(OUTPUT_PATH, "w", encoding="utf-8", newline="\n") as output:
        total += materialize_query(connection, output, "plants", """
            SELECT p.*, f.family_name, g.genus_name
            FROM plant p
            LEFT JOIN family f ON f.family_id = p.family_id
            LEFT JOIN genus g ON g.genus_id = p.genus_id
        """, plant_writer)

        total += materialize_query(connection, output, "families", "SELECT * FROM family", family_writer)
        total += materialize_query(connection, output, "genera", """
            SELECT g.genus_name, f.family_name
            FROM genus g
            JOIN family f ON f.family_id = g.family_id
        """, genus_writer)

        total += materialize_query(connection, output, "common names", "SELECT * FROM plant_common_name", lambda out, row: write_literal(out, plant_iri(row["plant_id"]), iri(PLANT + "hasCommonName"), row["common_name"]))
        total += materialize_query(connection, output, "synonyms", "SELECT * FROM plant_synonym", lambda out, row: write_literal(out, plant_iri(row["plant_id"]), iri(PLANT + "hasSynonymName"), row["synonym_name"]))
        total += materialize_query(connection, output, "growth rates", """
            SELECT plant_id, ontology_suffix FROM plant JOIN growth_rate_dim ON growth_rate_dim.code = plant.growth_rate_code
        """, lambda out, row: write_iri(out, plant_iri(row["plant_id"]), iri(PLANT + "hasGrowthRate"), ontology_iri(row["ontology_suffix"])))
        total += materialize_query(connection, output, "growth forms", """
            SELECT plant_id, ontology_suffix FROM plant JOIN growth_form_dim ON growth_form_dim.code = plant.growth_form_code
        """, lambda out, row: write_iri(out, plant_iri(row["plant_id"]), iri(PLANT + "hasGrowthForm"), ontology_iri(row["ontology_suffix"])))
        total += materialize_query(connection, output, "growth habits", """
            SELECT plant_id, ontology_suffix FROM plant_growth_habit JOIN growth_habit_dim ON growth_habit_dim.code = plant_growth_habit.growth_habit_code
        """, lambda out, row: write_iri(out, plant_iri(row["plant_id"]), iri(PLANT + "hasGrowthHabit"), ontology_iri(row["ontology_suffix"])))

        total += materialize_query(connection, output, "months", "SELECT * FROM month_dim", lambda out, row: (
            write_triple(out, ontology_iri(row["ontology_suffix"]), iri(RDF.type), iri(PLANT + "Month")) or
            write_literal(out, ontology_iri(row["ontology_suffix"]), iri(RDFS.label), row["label"]) + 1
        ))
        total += materialize_query(connection, output, "bloom months", """
            SELECT plant_id, ontology_suffix FROM plant_bloom_month JOIN month_dim USING (month_number)
        """, lambda out, row: write_iri(out, plant_iri(row["plant_id"]), iri(PLANT + "bloomsInMonth"), ontology_iri(row["ontology_suffix"])))
        total += materialize_query(connection, output, "fruit months", """
            SELECT plant_id, ontology_suffix FROM plant_fruit_month JOIN month_dim USING (month_number)
        """, lambda out, row: write_iri(out, plant_iri(row["plant_id"]), iri(PLANT + "fruitingInMonth"), ontology_iri(row["ontology_suffix"])))
        total += materialize_query(connection, output, "growth months", """
            SELECT plant_id, ontology_suffix FROM plant_growth_month JOIN month_dim USING (month_number)
        """, lambda out, row: write_iri(out, plant_iri(row["plant_id"]), iri(PLANT + "growsInMonth"), ontology_iri(row["ontology_suffix"])))

        total += materialize_query(connection, output, "edible parts", """
            SELECT plant_id, part_ontology_suffix, use_ontology_suffix
            FROM plant_edible_part JOIN edible_part_dim ON edible_part_dim.code = plant_edible_part.edible_part_code
        """, lambda out, row: (
            write_iri(out, plant_iri(row["plant_id"]), iri(PLANT + "hasEdiblePart"), ontology_iri(row["part_ontology_suffix"])) +
            write_iri(out, plant_iri(row["plant_id"]), iri(PLANT + "hasPlantUse"), ontology_iri(row["use_ontology_suffix"]))
        ))
        total += materialize_query(connection, output, "vegetable uses", "SELECT plant_id FROM plant WHERE vegetable = 1", lambda out, row: write_iri(out, plant_iri(row["plant_id"]), iri(PLANT + "hasPlantUse"), iri(PLANT + "VegetableUseIndividual")))

        total += materialize_query(connection, output, "flowers", """
            SELECT flower_component.plant_id, flower_component.conspicuous, plant.scientific_name
            FROM flower_component JOIN plant ON plant.plant_id = flower_component.plant_id
        """, component_writer("flower", "Flower", "hasFlowerConspicuous"))
        total += materialize_query(connection, output, "plant-flower links", "SELECT plant_id FROM flower_component", lambda out, row: write_iri(out, plant_iri(row["plant_id"]), iri(PLANT + "hasComponent"), flower_iri(row["plant_id"])))
        total += materialize_query(connection, output, "flower colors", """
            SELECT plant_id, ontology_suffix FROM plant_flower_color JOIN flower_color_dim ON flower_color_dim.code = plant_flower_color.color_code
        """, lambda out, row: write_iri(out, flower_iri(row["plant_id"]), iri(PLANT + "hasColor"), ontology_iri(row["ontology_suffix"])))

        total += materialize_query(connection, output, "foliage", """
            SELECT foliage_component.plant_id, plant.scientific_name
            FROM foliage_component JOIN plant ON plant.plant_id = foliage_component.plant_id
        """, component_writer("foliage", "Foliage", None))
        total += materialize_query(connection, output, "plant-foliage links", "SELECT plant_id FROM foliage_component", lambda out, row: write_iri(out, plant_iri(row["plant_id"]), iri(PLANT + "hasComponent"), foliage_iri(row["plant_id"])))
        total += materialize_query(connection, output, "foliage colors", """
            SELECT plant_id, ontology_suffix FROM plant_foliage_color JOIN foliage_color_dim ON foliage_color_dim.code = plant_foliage_color.color_code
        """, lambda out, row: write_iri(out, foliage_iri(row["plant_id"]), iri(PLANT + "hasColor"), ontology_iri(row["ontology_suffix"])))
        total += materialize_query(connection, output, "foliage textures", """
            SELECT plant_id, ontology_suffix FROM foliage_component JOIN foliage_texture_dim ON foliage_texture_dim.code = foliage_component.texture_code
        """, lambda out, row: write_iri(out, foliage_iri(row["plant_id"]), iri(PLANT + "hasFoliageTexture"), ontology_iri(row["ontology_suffix"])))

        total += materialize_query(connection, output, "fruits", """
            SELECT fruit_component.plant_id, fruit_component.conspicuous, plant.scientific_name
            FROM fruit_component JOIN plant ON plant.plant_id = fruit_component.plant_id
        """, component_writer("fruit", "Fruit", "hasFruitConspicuous"))
        total += materialize_query(connection, output, "plant-fruit links", "SELECT plant_id FROM fruit_component", lambda out, row: write_iri(out, plant_iri(row["plant_id"]), iri(PLANT + "hasComponent"), fruit_iri(row["plant_id"])))
        total += materialize_query(connection, output, "fruit colors", """
            SELECT plant_id, ontology_suffix FROM plant_fruit_color JOIN fruit_color_dim ON fruit_color_dim.code = plant_fruit_color.color_code
        """, lambda out, row: write_iri(out, fruit_iri(row["plant_id"]), iri(PLANT + "hasColor"), ontology_iri(row["ontology_suffix"])))

        total += materialize_query(connection, output, "regions", "SELECT * FROM region", lambda out, row: (
            write_triple(out, region_iri(row["region_id"]), iri(RDF.type), iri(PLANT + "Region")) or
            write_literal(out, region_iri(row["region_id"]), iri(RDFS.label), row["region_name"]) + 1
        ))
        total += materialize_query(connection, output, "distributions", "SELECT * FROM plant_distribution", lambda out, row: (
            (write_triple(out, distribution_iri(row["plant_id"], row["region_id"]), iri(RDF.type), iri(PLANT + "PlantDistribution")) or 1) +
            write_iri(out, distribution_iri(row["plant_id"], row["region_id"]), iri(PLANT + "distributionForPlant"), plant_iri(row["plant_id"])) +
            write_iri(out, distribution_iri(row["plant_id"], row["region_id"]), iri(PLANT + "inRegion"), region_iri(row["region_id"])) +
            write_iri(out, plant_iri(row["plant_id"]), iri(PLANT + "hasDistribution"), distribution_iri(row["plant_id"], row["region_id"]))
        ))

        total += materialize_query(connection, output, "shop products", """
            SELECT sp.*, cl.ontology_suffix AS care_suffix, tc.ontology_suffix AS temperature_suffix
            FROM shop_product sp
            LEFT JOIN care_level_dim cl ON cl.code = sp.care_level_code
            LEFT JOIN temperature_category_dim tc ON tc.code = sp.temperature_category_code
        """, shop_product_writer)

    elapsed = time.time() - started
    print(f"Full KG written to: {OUTPUT_PATH}")
    print(f"Total triples: {total:,}")
    print(f"Elapsed: {elapsed:.1f}s")


if __name__ == "__main__":
    main()

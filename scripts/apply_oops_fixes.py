"""
Apply the final ontology cleanup rules.

LLM use disclaimer: an LLM was used during this exercise; the output was
reviewed, adapted, and verified by the author.
"""

from pathlib import Path
from rdflib import Graph, Namespace, RDF, RDFS, OWL, XSD, Literal, URIRef


ROOT_DIR = Path(__file__).resolve().parent.parent
INPUT_TTL = ROOT_DIR / "ontology" / "plant_management.ttl"
OUTPUT_TTL = ROOT_DIR / "ontology" / "plant_management_oops_fixed.ttl"
OUTPUT_RDF = ROOT_DIR / "ontology" / "plant_management_oops_fixed.rdf"

PLANT = Namespace("http://www.semanticweb.org/plantms/ontology#")
DCTERMS = Namespace("http://purl.org/dc/terms/")


def add_label_comment(graph, subject, label, comment=None):
    graph.add((subject, RDFS.label, Literal(label, lang="en")))
    if comment:
        graph.add((subject, RDFS.comment, Literal(comment, lang="en")))


def replace_comment(graph, subject, comment):
    graph.remove((subject, RDFS.comment, None))
    graph.add((subject, RDFS.comment, Literal(comment, lang="en")))


def add_object_property(graph, name, domain, range_, label, comment, transitive=False):
    uri = PLANT[name]
    graph.add((uri, RDF.type, OWL.ObjectProperty))
    graph.add((uri, RDFS.domain, domain))
    graph.add((uri, RDFS.range, range_))
    add_label_comment(graph, uri, label, comment)
    if transitive:
        graph.add((uri, RDF.type, OWL.TransitiveProperty))
    return uri


def add_inverse_property(graph, name, inverse_of, domain, range_, label, comment=None, transitive=False):
    uri = add_object_property(graph, name, domain, range_, label, comment, transitive=transitive)
    graph.add((inverse_of, OWL.inverseOf, uri))
    return uri


def remove_unused_time_interval(graph):
    time_interval = PLANT.TimeInterval
    graph.remove((time_interval, None, None))
    graph.remove((None, None, time_interval))


def fix_part_relations(graph):
    has_part = PLANT.hasPart
    is_part_of = PLANT.isPartOf

    graph.remove((has_part, RDF.type, OWL.TransitiveProperty))
    graph.remove((is_part_of, RDF.type, OWL.TransitiveProperty))
    graph.remove((has_part, OWL.propertyChainAxiom, None))

    replace_comment(
        graph,
        has_part,
        "Direct relation between a plant and a structural plant part.",
    )
    graph.remove((is_part_of, RDFS.comment, None))


def fix_numeric_ranges(graph):
    restricted_properties = [
        "hasPlantingDaysToHarvest",
        "hasSoilNutriments",
        "hasPlantingSpreadCm",
        "hasPhMinimum",
        "hasAtmosphericHumidity",
        "hasMinimumRootDepthCm",
        "hasMaximumHeightCm",
        "hasPlantingRowSpacingCm",
        "hasStockQuantity",
        "hasAnaerobicTolerance",
        "hasSoilSalinity",
        "hasLightRequirement",
        "hasPriceEur",
        "hasPhMaximum",
        "hasAverageHeightCm",
        "hasGroundHumidity",
    ]

    for property_name in restricted_properties:
        property_uri = PLANT[property_name]
        graph.remove((property_uri, RDFS.range, XSD.integer))
        graph.remove((property_uri, RDFS.range, XSD.decimal))


def add_season_links(graph):
    in_season = add_object_property(
        graph,
        "inSeason",
        PLANT.Month,
        PLANT.Season,
        "in season",
        "Connects a month to the season it belongs to.",
    )
    add_inverse_property(
        graph,
        "hasMonth",
        in_season,
        PLANT.Season,
        PLANT.Month,
        "has month",
    )

    month_seasons = {
        "January": "Winter",
        "February": "Winter",
        "March": "Spring",
        "April": "Spring",
        "May": "Spring",
        "June": "Summer",
        "July": "Summer",
        "August": "Summer",
        "September": "Autumn",
        "October": "Autumn",
        "November": "Autumn",
        "December": "Winter",
    }

    for month_name, season_name in month_seasons.items():
        graph.add((PLANT[month_name], in_season, PLANT[season_name]))


def add_useful_inverses(graph):
    add_inverse_property(
        graph, "hasFamilyMember", PLANT.belongsToFamily, PLANT.Family, PLANT.Plant,
        "has family member"
    )
    add_inverse_property(
        graph, "hasGenusMember", PLANT.belongsToGenus, PLANT.Genus, PLANT.Plant,
        "has genus member"
    )
    add_inverse_property(
        graph, "hasGenus", PLANT.isSubsumedByFamily, PLANT.Family, PLANT.Genus,
        "has genus"
    )
    add_inverse_property(
        graph, "colorOfPart", PLANT.hasColor, PLANT.Color, PLANT.PlantPart,
        "color of part"
    )
    add_inverse_property(
        graph, "foliageTextureOf", PLANT.hasFoliageTexture, PLANT.FoliageTexture, PLANT.Foliage,
        "foliage texture of"
    )
    add_inverse_property(
        graph, "growthHabitOf", PLANT.hasGrowthHabit, PLANT.GrowthHabit, PLANT.Plant,
        "growth habit of"
    )
    add_inverse_property(
        graph, "growthFormOf", PLANT.hasGrowthForm, PLANT.GrowthForm, PLANT.Plant,
        "growth form of"
    )
    add_inverse_property(
        graph, "growthRateOf", PLANT.hasGrowthRate, PLANT.GrowthRate, PLANT.Plant,
        "growth rate of"
    )
    add_inverse_property(
        graph, "isBloomMonthOf", PLANT.bloomsInMonth, PLANT.Month, PLANT.Plant,
        "is bloom month of"
    )
    add_inverse_property(
        graph, "isFruitingMonthOf", PLANT.fruitingInMonth, PLANT.Month, PLANT.Plant,
        "is fruiting month of"
    )
    add_inverse_property(
        graph, "isGrowthMonthOf", PLANT.growsInMonth, PLANT.Month, PLANT.Plant,
        "is growth month of"
    )
    add_inverse_property(
        graph, "conditionRequiredBy", PLANT.requiresCondition, PLANT.HabitatCondition, PLANT.Plant,
        "condition required by"
    )
    add_inverse_property(
        graph, "regionOfDistribution", PLANT.inRegion, PLANT.Region, PLANT.PlantDistribution,
        "region of distribution"
    )
    add_inverse_property(
        graph, "statusOfDistribution", PLANT.hasDistributionStatus,
        PLANT.DistributionStatus, PLANT.PlantDistribution,
        "status of distribution"
    )
    add_inverse_property(
        graph, "hasSubRegion", PLANT.isSubRegionOf, PLANT.Region, PLANT.Region,
        "has sub-region", transitive=True
    )
    add_inverse_property(
        graph, "plantUseOf", PLANT.hasPlantUse, PLANT.PlantUse, PLANT.Plant,
        "plant use of"
    )
    add_inverse_property(
        graph, "ediblePartOf", PLANT.hasEdiblePart, PLANT.EdiblePart, PLANT.Plant,
        "edible part of"
    )
    add_inverse_property(
        graph, "careLevelOfProduct", PLANT.hasCareLevel, PLANT.CareLevel, PLANT.ShopProduct,
        "care level of product"
    )
    add_inverse_property(
        graph, "temperatureCategoryOfProduct", PLANT.hasTemperatureCategory,
        PLANT.TemperatureCategory, PLANT.ShopProduct,
        "temperature category of product"
    )


def write_graph(graph, path, rdf_format):
    serialized = graph.serialize(format=rdf_format)
    path.write_text(serialized.rstrip() + "\n", encoding="utf-8")


def main():
    if not INPUT_TTL.exists():
        raise FileNotFoundError("Missing input ontology: " + str(INPUT_TTL))

    graph = Graph()
    graph.parse(INPUT_TTL, format="turtle")
    graph.bind("plant", PLANT)
    graph.bind("dcterms", DCTERMS)

    graph.add((PLANT[""], DCTERMS.license,
               URIRef("https://creativecommons.org/licenses/by/4.0/")))

    remove_unused_time_interval(graph)
    fix_part_relations(graph)
    fix_numeric_ranges(graph)
    add_season_links(graph)
    add_useful_inverses(graph)

    write_graph(graph, OUTPUT_TTL, "turtle")
    write_graph(graph, OUTPUT_RDF, "xml")

    classes = sum(1 for _ in graph.triples((None, RDF.type, OWL.Class)))
    object_properties = sum(1 for _ in graph.triples((None, RDF.type, OWL.ObjectProperty)))
    datatype_properties = sum(1 for _ in graph.triples((None, RDF.type, OWL.DatatypeProperty)))
    individuals = sum(1 for _ in graph.triples((None, RDF.type, OWL.NamedIndividual)))

    print("Cleaned ontology written to: " + str(OUTPUT_TTL))
    print("Cleaned RDF/XML written to: " + str(OUTPUT_RDF))
    print(f"  Triples            : {len(graph):,}")
    print(f"  Classes            : {classes}")
    print(f"  Object properties  : {object_properties}")
    print(f"  Datatype properties: {datatype_properties}")
    print(f"  Named individuals  : {individuals}")


if __name__ == "__main__":
    main()

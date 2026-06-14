"""
Generate the Plant Management OWL2 TBox.

LLM use disclaimer: an LLM was used during this exercise; the output was
reviewed, adapted, and verified by the author.
"""

from pathlib import Path
from rdflib import Graph, Namespace, RDF, RDFS, OWL, XSD, Literal, BNode
from rdflib.collection import Collection

PLANT = Namespace("http://www.semanticweb.org/plantms/ontology#")

g = Graph()
g.bind("plant", PLANT)
g.bind("owl", OWL)
g.bind("rdf", RDF)
g.bind("rdfs", RDFS)
g.bind("xsd", XSD)

def add_class(name, superclass=OWL.Thing, label=None, comment=None):
    uri = PLANT[name]
    g.add((uri, RDF.type, OWL.Class))
    g.add((uri, RDFS.subClassOf, superclass))
    g.add((uri, RDFS.label, Literal(label or name, lang="en")))
    if comment:
        g.add((uri, RDFS.comment, Literal(comment, lang="en")))
    return uri


def add_object_property(name, domain=None, range_=None, characteristics=None,
                        label=None, comment=None):
    uri = PLANT[name]
    g.add((uri, RDF.type, OWL.ObjectProperty))
    if domain:
        g.add((uri, RDFS.domain, domain))
    if range_:
        g.add((uri, RDFS.range, range_))
    for char in (characteristics or []):
        g.add((uri, RDF.type, char))
    g.add((uri, RDFS.label, Literal(label or name, lang="en")))
    if comment:
        g.add((uri, RDFS.comment, Literal(comment, lang="en")))
    return uri


def add_datatype_property(name, domain=None, range_=XSD.string,
                          characteristics=None, label=None, comment=None):
    uri = PLANT[name]
    g.add((uri, RDF.type, OWL.DatatypeProperty))
    if domain:
        g.add((uri, RDFS.domain, domain))
    if range_:
        g.add((uri, RDFS.range, range_))
    for char in (characteristics or []):
        g.add((uri, RDF.type, char))
    g.add((uri, RDFS.label, Literal(label or name, lang="en")))
    if comment:
        g.add((uri, RDFS.comment, Literal(comment, lang="en")))
    return uri


def add_some_values_from(class_uri, prop_uri, filler_uri):
    restriction = BNode()
    g.add((restriction, RDF.type, OWL.Restriction))
    g.add((restriction, OWL.onProperty, prop_uri))
    g.add((restriction, OWL.someValuesFrom, filler_uri))
    g.add((class_uri, RDFS.subClassOf, restriction))


def add_all_values_from(class_uri, prop_uri, filler_uri):
    restriction = BNode()
    g.add((restriction, RDF.type, OWL.Restriction))
    g.add((restriction, OWL.onProperty, prop_uri))
    g.add((restriction, OWL.allValuesFrom, filler_uri))
    g.add((class_uri, RDFS.subClassOf, restriction))


def add_min_qualified_cardinality(class_uri, prop_uri, n, filler_uri):
    restriction = BNode()
    g.add((restriction, RDF.type, OWL.Restriction))
    g.add((restriction, OWL.onProperty, prop_uri))
    g.add((restriction, OWL.minQualifiedCardinality,
           Literal(n, datatype=XSD.nonNegativeInteger)))
    g.add((restriction, OWL.onClass, filler_uri))
    g.add((class_uri, RDFS.subClassOf, restriction))


def add_property_chain(super_prop_uri, chain_prop_uris):
    chain_list = BNode()
    Collection(g, chain_list, chain_prop_uris)
    g.add((super_prop_uri, OWL.propertyChainAxiom, chain_list))


def add_disjoint_union(parent_uri, member_uris):
    members_list = BNode()
    Collection(g, members_list, member_uris)
    g.add((parent_uri, OWL.disjointUnionOf, members_list))


def add_all_disjoint_classes(member_uris):
    node = BNode()
    g.add((node, RDF.type, OWL.AllDisjointClasses))
    members_list = BNode()
    Collection(g, members_list, member_uris)
    g.add((node, OWL.members, members_list))


def add_named_individual(name, class_uri, label=None):
    uri = PLANT[name]
    g.add((uri, RDF.type, OWL.NamedIndividual))
    g.add((uri, RDF.type, class_uri))
    g.add((uri, RDFS.label, Literal(label or name, lang="en")))
    return uri


def add_datatype_range_restriction(prop_uri, facets):
    restriction_node = BNode()
    g.add((restriction_node, RDF.type, RDFS.Datatype))
    g.add((restriction_node, OWL.onDatatype, XSD.decimal))
    facet_list = BNode()
    facet_items = []
    for facet_uri, value in facets:
        facet_bn = BNode()
        g.add((facet_bn, facet_uri, value))
        facet_items.append(facet_bn)
    Collection(g, facet_list, facet_items)
    g.add((restriction_node, OWL.withRestrictions, facet_list))
    g.add((prop_uri, RDFS.range, restriction_node))


def add_integer_range_restriction(prop_uri, min_incl=None, max_incl=None):
    restriction_node = BNode()
    g.add((restriction_node, RDF.type, RDFS.Datatype))
    g.add((restriction_node, OWL.onDatatype, XSD.integer))
    facet_items = []
    if min_incl is not None:
        bn = BNode()
        g.add((bn, XSD.minInclusive, Literal(min_incl, datatype=XSD.integer)))
        facet_items.append(bn)
    if max_incl is not None:
        bn = BNode()
        g.add((bn, XSD.maxInclusive, Literal(max_incl, datatype=XSD.integer)))
        facet_items.append(bn)
    facet_list = BNode()
    Collection(g, facet_list, facet_items)
    g.add((restriction_node, OWL.withRestrictions, facet_list))
    g.add((prop_uri, RDFS.range, restriction_node))


def add_decimal_min_restriction(prop_uri, min_incl=0):
    restriction_node = BNode()
    g.add((restriction_node, RDF.type, RDFS.Datatype))
    g.add((restriction_node, OWL.onDatatype, XSD.decimal))
    bn = BNode()
    g.add((bn, XSD.minInclusive, Literal(min_incl, datatype=XSD.decimal)))
    facet_list = BNode()
    Collection(g, facet_list, [bn])
    g.add((restriction_node, OWL.withRestrictions, facet_list))
    g.add((prop_uri, RDFS.range, restriction_node))


ONTOLOGY_IRI = PLANT[""]

g.add((ONTOLOGY_IRI, RDF.type, OWL.Ontology))
g.add((ONTOLOGY_IRI, RDFS.label,
       Literal("Plant Management System Ontology", lang="en")))
g.add((ONTOLOGY_IRI, RDFS.comment, Literal(
    "OWL2 schema for the Plant Management System.",
    lang="en")))
g.add((ONTOLOGY_IRI, OWL.versionInfo, Literal("1.0.0")))

# Taxonomy
TaxonomicRank = add_class(
    "TaxonomicRank",
    label="Taxonomic Rank",
    comment="Abstract superclass for taxonomic classification units."
)
Family = add_class(
    "Family",
    superclass=TaxonomicRank,
    label="Family",
    comment="Taxonomic family."
)
Genus = add_class(
    "Genus",
    superclass=TaxonomicRank,
    label="Genus",
    comment="Taxonomic genus."
)
Plant = add_class(
    "Plant",
    label="Plant",
    comment="Main plant species entity."
)

# Plant parts
PlantPart = add_class(
    "PlantPart",
    label="Plant Part",
    comment="Abstract superclass for structural plant components."
)
Flower = add_class(
    "Flower", superclass=PlantPart,
    label="Flower",
    comment="Flower of a plant."
)
Foliage = add_class(
    "Foliage", superclass=PlantPart,
    label="Foliage",
    comment="Leaves or visible foliage of a plant."
)
Fruit = add_class(
    "Fruit", superclass=PlantPart,
    label="Fruit",
    comment="Fruit of a plant. Has color, conspicuousness, and fruiting months."
)
Root = add_class(
    "Root", superclass=PlantPart,
    label="Root",
    comment="Root system of a plant."
)

# Descriptors
Color = add_class(
    "Color",
    label="Color",
    comment="Abstract superclass for all plant-part color descriptors."
)
FlowerColor = add_class(
    "FlowerColor", superclass=Color,
    label="Flower Color",
    comment="Color of a flower."
)
FoliageColor = add_class(
    "FoliageColor", superclass=Color,
    label="Foliage Color",
    comment="Color of foliage (e.g. Green, Grey)."
)
FruitColor = add_class(
    "FruitColor", superclass=Color,
    label="Fruit Color",
    comment="Color of fruit (e.g. Black, Red)."
)
FoliageTexture = add_class(
    "FoliageTexture",
    label="Foliage Texture",
    comment="Texture of foliage: fine, medium, or coarse."
)
GrowthHabit = add_class(
    "GrowthHabit",
    label="Growth Habit",
    comment="Overall growth habit of a plant."
)
GrowthForm = add_class(
    "GrowthForm",
    label="Growth Form",
    comment="Specific growth form."
)
GrowthRate = add_class(
    "GrowthRate",
    label="Growth Rate",
    comment="Rate of growth: Slow, Moderate, or Rapid."
)

# Ecological conditions
HabitatCondition = add_class(
    "HabitatCondition",
    label="Habitat Condition",
    comment="Abstract superclass for environmental/ecological condition types."
)
SoilCondition = add_class(
    "SoilCondition", superclass=HabitatCondition,
    label="Soil Condition",
    comment="Soil-related conditions: nutriments, salinity, pH range."
)
LightCondition = add_class(
    "LightCondition", superclass=HabitatCondition,
    label="Light Condition",
    comment="Light requirement (0–10 scale)."
)
HumidityCondition = add_class(
    "HumidityCondition", superclass=HabitatCondition,
    label="Humidity Condition",
    comment="Humidity conditions."
)
AnaerobicCondition = add_class(
    "AnaerobicCondition", superclass=HabitatCondition,
    label="Anaerobic Condition",
    comment="Anaerobic tolerance level."
)

# Temporal classes
Month = add_class(
    "Month",
    label="Month",
    comment="Calendar month."
)
Season = add_class(
    "Season",
    label="Season",
    comment="Season of the year: Spring, Summer, Autumn, Winter."
)
TimeInterval = add_class(
    "TimeInterval",
    label="Time Interval",
    comment="An interval defined by a start and end month."
)

# Geography
Region = add_class(
    "Region",
    label="Region",
    comment="Abstract geographic region. Subclassed into Continent and Country."
)
Continent = add_class(
    "Continent", superclass=Region,
    label="Continent",
    comment="Top-level geographic region (e.g. Europe, North America)."
)
Country = add_class(
    "Country", superclass=Region,
    label="Country",
    comment="Country or state-level region."
)

# Distribution
PlantDistribution = add_class(
    "PlantDistribution",
    label="Plant Distribution",
    comment="Distribution record for a plant in a region."
)
DistributionStatus = add_class(
    "DistributionStatus",
    label="Distribution Status",
    comment="Status of a plant's presence in a region."
)

# Plant use
PlantUse = add_class(
    "PlantUse",
    label="Plant Use",
    comment="Abstract superclass for plant use roles."
)
EdibleUse = add_class(
    "EdibleUse", superclass=PlantUse,
    label="Edible Use",
    comment="Plant used as a food source."
)
VegetableUse = add_class(
    "VegetableUse", superclass=PlantUse,
    label="Vegetable Use",
    comment="Plant classified as a vegetable."
)
OrnamentalUse = add_class(
    "OrnamentalUse", superclass=PlantUse,
    label="Ornamental Use",
    comment="Plant used for decorative / ornamental purposes."
)

# Edible parts
EdiblePart = add_class(
    "EdiblePart",
    label="Edible Part",
    comment="The part of a plant that is edible."
)

# Taxonomy
belongsToFamily = add_object_property(
    "belongsToFamily", domain=Plant, range_=Family,
    characteristics=[OWL.FunctionalProperty],
    label="belongs to family",
    comment="Links a plant to its taxonomic family."
)
belongsToGenus = add_object_property(
    "belongsToGenus", domain=Plant, range_=Genus,
    characteristics=[OWL.FunctionalProperty],
    label="belongs to genus",
    comment="Links a plant to its taxonomic genus."
)
isSubsumedByFamily = add_object_property(
    "isSubsumedByFamily", domain=Genus, range_=Family,
    characteristics=[OWL.FunctionalProperty],
    label="is subsumed by family",
    comment="Links a genus to its parent family."
)

# Plant part relations
hasPart = add_object_property(
    "hasPart", domain=Plant, range_=PlantPart,
    characteristics=[OWL.TransitiveProperty],
    label="has part",
    comment="Part relation between a plant and a plant part."
)
isPartOf = add_object_property(
    "isPartOf", domain=PlantPart, range_=Plant,
    characteristics=[OWL.TransitiveProperty],
    label="is part of",
)
g.add((hasPart, OWL.inverseOf, isPartOf))

hasComponent = add_object_property(
    "hasComponent", domain=Plant, range_=PlantPart,
    label="has component",
    comment="Direct structural component of a plant."
)
isComponentOf = add_object_property(
    "isComponentOf", domain=PlantPart, range_=Plant,
    label="is component of",
)
g.add((hasComponent, OWL.inverseOf, isComponentOf))
g.add((hasComponent, RDFS.subPropertyOf, hasPart))

# Descriptors
hasColor = add_object_property(
    "hasColor", domain=PlantPart, range_=Color,
    label="has color",
    comment="Links a plant part to a color."
)
hasFoliageTexture = add_object_property(
    "hasFoliageTexture", domain=Foliage, range_=FoliageTexture,
    characteristics=[OWL.FunctionalProperty],
    label="has foliage texture",
    comment="Texture of foliage."
)
hasGrowthHabit = add_object_property(
    "hasGrowthHabit", domain=Plant, range_=GrowthHabit,
    label="has growth habit",
    comment="Growth habit of a plant."
)
hasGrowthForm = add_object_property(
    "hasGrowthForm", domain=Plant, range_=GrowthForm,
    label="has growth form",
    comment="Specific growth form."
)
hasGrowthRate = add_object_property(
    "hasGrowthRate", domain=Plant, range_=GrowthRate,
    characteristics=[OWL.FunctionalProperty],
    label="has growth rate",
    comment="Rate of growth."
)

# Temporal
bloomsInMonth = add_object_property(
    "bloomsInMonth", domain=Plant, range_=Month,
    label="blooms in month",
    comment="Month when the plant blooms."
)
fruitingInMonth = add_object_property(
    "fruitingInMonth", domain=Plant, range_=Month,
    label="fruiting in month",
    comment="Month when the plant fruits."
)
growsInMonth = add_object_property(
    "growsInMonth", domain=Plant, range_=Month,
    label="grows in month",
    comment="Month of active growth."
)

# Ecological
requiresCondition = add_object_property(
    "requiresCondition", domain=Plant, range_=HabitatCondition,
    label="requires condition",
    comment="Links a plant to an ecological condition type."
)

# Distribution
hasDistribution = add_object_property(
    "hasDistribution", domain=Plant, range_=PlantDistribution,
    label="has distribution",
    comment="Links a plant to a distribution record."
)
distributionForPlant = add_object_property(
    "distributionForPlant", domain=PlantDistribution, range_=Plant,
    label="distribution for plant",
)
g.add((hasDistribution, OWL.inverseOf, distributionForPlant))

inRegion = add_object_property(
    "inRegion", domain=PlantDistribution, range_=Region,
    label="in region",
    comment="Links a PlantDistribution node to its geographic Region."
)
hasDistributionStatus = add_object_property(
    "hasDistributionStatus", domain=PlantDistribution, range_=DistributionStatus,
    label="has distribution status",
    comment="Status of the distribution (Native, Introduced, Endemic, Absent)."
)
isSubRegionOf = add_object_property(
    "isSubRegionOf", domain=Region, range_=Region,
    characteristics=[OWL.TransitiveProperty],
    label="is sub-region of",
    comment="Transitive region hierarchy: Country isSubRegionOf Continent."
)

# Plant use
hasPlantUse = add_object_property(
    "hasPlantUse", domain=Plant, range_=PlantUse,
    label="has plant use",
    comment="Links a plant to a plant use."
)
hasEdiblePart = add_object_property(
    "hasEdiblePart", domain=Plant, range_=EdiblePart,
    label="has edible part",
    comment="Which parts of the plant are edible."
)

hasTrefleId = add_datatype_property(
    "hasTrefleId", domain=Plant, range_=XSD.integer,
    characteristics=[OWL.FunctionalProperty],
    label="has Trefle ID",
    comment="Unique numeric identifier from the Trefle database."
)
hasScientificName = add_datatype_property(
    "hasScientificName", domain=Plant, range_=XSD.string,
    characteristics=[OWL.FunctionalProperty],
    label="has scientific name",
    comment="Scientific name of the species."
)
hasCommonName = add_datatype_property(
    "hasCommonName", domain=Plant, range_=XSD.string,
    label="has common name",
    comment="Common name(s) of the plant. Multi-valued."
)
hasFamilyCommonName = add_datatype_property(
    "hasFamilyCommonName", domain=Family, range_=XSD.string,
    label="has family common name",
    comment="Common-language name of the taxonomic family."
)
hasSynonymName = add_datatype_property(
    "hasSynonymName", domain=Plant, range_=XSD.string,
    label="has synonym name",
    comment="Taxonomic synonym."
)
hasYear = add_datatype_property(
    "hasYear", domain=Plant, range_=XSD.integer,
    label="has year",
    comment="Year of taxonomic publication."
)
hasAuthor = add_datatype_property(
    "hasAuthor", domain=Plant, range_=XSD.string,
    label="has author",
    comment="Author of the taxonomic description."
)
hasMaximumHeightCm = add_datatype_property(
    "hasMaximumHeightCm", domain=Plant, range_=XSD.decimal,
    label="has maximum height (cm)",
    comment="Maximum height in centimetres."
)
hasAverageHeightCm = add_datatype_property(
    "hasAverageHeightCm", domain=Plant, range_=XSD.decimal,
    label="has average height (cm)",
    comment="Average height in centimetres."
)
hasMinimumRootDepthCm = add_datatype_property(
    "hasMinimumRootDepthCm", domain=Plant, range_=XSD.decimal,
    label="has minimum root depth (cm)",
    comment="Minimum root depth in centimetres."
)
hasLightRequirement = add_datatype_property(
    "hasLightRequirement", domain=Plant, range_=XSD.integer,
    label="has light requirement",
    comment="Light requirement on a 0–10 scale."
)
hasPhMinimum = add_datatype_property(
    "hasPhMinimum", domain=Plant, range_=XSD.decimal,
    label="has pH minimum",
    comment="Minimum soil pH."
)
hasPhMaximum = add_datatype_property(
    "hasPhMaximum", domain=Plant, range_=XSD.decimal,
    label="has pH maximum",
    comment="Maximum soil pH."
)
hasSoilNutriments = add_datatype_property(
    "hasSoilNutriments", domain=Plant, range_=XSD.integer,
    label="has soil nutriments",
    comment="Soil nutriment requirement (0–10)."
)
hasSoilSalinity = add_datatype_property(
    "hasSoilSalinity", domain=Plant, range_=XSD.integer,
    label="has soil salinity",
    comment="Soil salinity tolerance (0–10)."
)
hasGroundHumidity = add_datatype_property(
    "hasGroundHumidity", domain=Plant, range_=XSD.integer,
    label="has ground humidity",
    comment="Ground humidity requirement (0–10)."
)
hasAtmosphericHumidity = add_datatype_property(
    "hasAtmosphericHumidity", domain=Plant, range_=XSD.integer,
    label="has atmospheric humidity",
    comment="Atmospheric humidity requirement (0–10)."
)
hasAnaerobicTolerance = add_datatype_property(
    "hasAnaerobicTolerance", domain=Plant, range_=XSD.integer,
    label="has anaerobic tolerance",
    comment="Tolerance for anaerobic conditions (0–10)."
)
isEdible = add_datatype_property(
    "isEdible", domain=Plant, range_=XSD.boolean,
    label="is edible",
    comment="True if the plant is edible."
)
isVegetable = add_datatype_property(
    "isVegetable", domain=Plant, range_=XSD.boolean,
    label="is vegetable",
    comment="True if the plant is classified as a vegetable."
)
hasFlowerConspicuous = add_datatype_property(
    "hasFlowerConspicuous", domain=Flower, range_=XSD.boolean,
    label="has conspicuous flower",
    comment="Whether the flower is conspicuous."
)
hasFruitConspicuous = add_datatype_property(
    "hasFruitConspicuous", domain=Fruit, range_=XSD.boolean,
    label="has conspicuous fruit",
    comment="Whether the fruit is conspicuous."
)
hasPlantingDaysToHarvest = add_datatype_property(
    "hasPlantingDaysToHarvest", domain=Plant, range_=XSD.integer,
    label="has planting days to harvest",
    comment="Days from planting to harvest."
)
hasPlantingSpreadCm = add_datatype_property(
    "hasPlantingSpreadCm", domain=Plant, range_=XSD.decimal,
    label="has planting spread (cm)",
    comment="Spread of the plant at maturity."
)
hasImageUrl = add_datatype_property(
    "hasImageUrl", domain=Plant, range_=XSD.anyURI,
    label="has image URL",
    comment="URL of a representative plant image."
)
hasWikipediaUrl = add_datatype_property(
    "hasWikipediaUrl", domain=Plant, range_=XSD.anyURI,
    label="has Wikipedia URL",
    comment="URL of the Wikipedia article."
)
hasBibliography = add_datatype_property(
    "hasBibliography", domain=Plant, range_=XSD.string,
    label="has bibliography",
    comment="Bibliographic reference for the taxon."
)
hasPlantingRowSpacingCm = add_datatype_property(
    "hasPlantingRowSpacingCm", domain=Plant, range_=XSD.decimal,
    label="has planting row spacing (cm)",
    comment="Recommended row spacing in centimetres."
)

# OWL2 axioms
add_all_disjoint_classes([Family, Genus, Plant])
add_all_disjoint_classes([Flower, Foliage, Fruit, Root])
add_all_disjoint_classes([EdibleUse, VegetableUse, OrnamentalUse])

Tree = PLANT["Tree"]
Shrub = PLANT["Shrub"]
Vine = PLANT["Vine"]
Subshrub = PLANT["Subshrub"]
ForbHerb = PLANT["ForbHerb"]
Graminoid = PLANT["Graminoid"]
Nonvascular = PLANT["Nonvascular"]
add_disjoint_union(GrowthHabit, [Tree, Shrub, Vine, Subshrub, ForbHerb, Graminoid, Nonvascular])

months_uris = [PLANT[m] for m in [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
]]
add_disjoint_union(Month, months_uris)

season_uris = [PLANT[s] for s in ["Spring", "Summer", "Autumn", "Winter"]]
add_disjoint_union(Season, season_uris)

add_disjoint_union(GrowthRate,
    [PLANT["SlowGrowthRate"], PLANT["ModerateGrowthRate"], PLANT["RapidGrowthRate"]])

add_property_chain(belongsToFamily, [belongsToGenus, isSubsumedByFamily])

add_property_chain(hasPart, [hasComponent, hasPart])

add_some_values_from(Plant, belongsToGenus, Genus)
add_some_values_from(Plant, belongsToFamily, Family)
add_some_values_from(Plant, hasDistribution, PlantDistribution)

add_all_values_from(PlantPart, hasColor, Color)
add_all_values_from(PlantDistribution, inRegion, Region)

add_min_qualified_cardinality(Plant, hasComponent, 1, PlantPart)

key_list = BNode()
Collection(g, key_list, [hasTrefleId])
g.add((Plant, OWL.hasKey, key_list))

add_integer_range_restriction(hasLightRequirement, min_incl=0, max_incl=10)

for prop in [hasSoilNutriments, hasSoilSalinity, hasGroundHumidity,
             hasAtmosphericHumidity, hasAnaerobicTolerance]:
    add_integer_range_restriction(prop, min_incl=0, max_incl=10)

for prop in [hasMaximumHeightCm, hasAverageHeightCm, hasMinimumRootDepthCm,
             hasPlantingSpreadCm, hasPlantingRowSpacingCm]:
    add_decimal_min_restriction(prop, min_incl=0)

for prop in [hasPhMinimum, hasPhMaximum]:
    restriction_node = BNode()
    g.add((restriction_node, RDF.type, RDFS.Datatype))
    g.add((restriction_node, OWL.onDatatype, XSD.decimal))
    bn_min = BNode()
    g.add((bn_min, XSD.minInclusive, Literal("0.0", datatype=XSD.decimal)))
    bn_max = BNode()
    g.add((bn_max, XSD.maxInclusive, Literal("14.0", datatype=XSD.decimal)))
    facet_list = BNode()
    Collection(g, facet_list, [bn_min, bn_max])
    g.add((restriction_node, OWL.withRestrictions, facet_list))
    g.add((prop, RDFS.range, restriction_node))

add_integer_range_restriction(hasPlantingDaysToHarvest, min_incl=0)

# Controlled vocabularies
month_names = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
]
for m in month_names:
    add_named_individual(m, Month, label=m)

for s in ["Spring", "Summer", "Autumn", "Winter"]:
    add_named_individual(s, Season, label=s)

growth_habit_map = {
    "Tree": "Tree",
    "Shrub": "Shrub",
    "Vine": "Vine",
    "Subshrub": "Subshrub",
    "ForbHerb": "Forb/herb",
    "Graminoid": "Graminoid",
    "Nonvascular": "Nonvascular",
}
for iri_name, label in growth_habit_map.items():
    add_named_individual(iri_name, GrowthHabit, label=label)

growth_rate_map = {
    "SlowGrowthRate": "Slow",
    "ModerateGrowthRate": "Moderate",
    "RapidGrowthRate": "Rapid",
}
for iri_name, label in growth_rate_map.items():
    add_named_individual(iri_name, GrowthRate, label=label)

growth_form_map = {
    "Bunch": "Bunch",
    "Colonizing": "Colonizing",
    "Erect": "Erect",
    "MultipleStem": "Multiple Stem",
    "Rhizomatous": "Rhizomatous",
    "SingleCrown": "Single Crown",
    "SingleStem": "Single Stem",
    "Stoloniferous": "Stoloniferous",
    "ThicketForming": "Thicket Forming",
}
for iri_name, label in growth_form_map.items():
    add_named_individual(iri_name, GrowthForm, label=label)

for iri_name, label in [("FineTexture", "Fine"), ("MediumTexture", "Medium"),
                         ("CoarseTexture", "Coarse")]:
    add_named_individual(iri_name, FoliageTexture, label=label)

flower_colors = ["Blue", "Purple", "Yellow", "White", "Red", "Orange",
                 "Green", "Brown", "Black"]
for c in flower_colors:
    add_named_individual(f"FlowerColor_{c}", FlowerColor, label=c)

foliage_colors = ["Green", "Grey", "Red", "Yellow"]
for c in foliage_colors:
    add_named_individual(f"FoliageColor_{c}", FoliageColor, label=c)

fruit_colors = ["Black", "Blue", "Brown", "Green", "Orange", "Purple",
                "Red", "White", "Yellow"]
for c in fruit_colors:
    add_named_individual(f"FruitColor_{c}", FruitColor, label=c)

for iri_name, label in [
    ("NativeStatus", "Native"),
    ("IntroducedStatus", "Introduced"),
    ("EndemicStatus", "Endemic"),
    ("AbsentStatus", "Absent"),
]:
    add_named_individual(iri_name, DistributionStatus, label=label)

edible_part_map = {
    "FlowerPart": "Flowers",
    "FruitPart": "Fruits",
    "LeafPart": "Leaves",
    "RootPart": "Roots",
    "SeedPart": "Seeds",
    "StemPart": "Stem",
    "TuberPart": "Tubers",
}
for iri_name, label in edible_part_map.items():
    add_named_individual(iri_name, EdiblePart, label=label)

plant_use_map = {
    "EdibleLeavesUse": ("Edible Leaves", EdibleUse),
    "EdibleRootsUse": ("Edible Roots", EdibleUse),
    "EdibleFruitsUse": ("Edible Fruits", EdibleUse),
    "EdibleStemsUse": ("Edible Stems", EdibleUse),
    "EdibleSeedsUse": ("Edible Seeds", EdibleUse),
    "EdibleTubersUse": ("Edible Tubers", EdibleUse),
    "EdibleFlowersUse": ("Edible Flowers", EdibleUse),
    "VegetableUseIndividual": ("Vegetable", VegetableUse),
    "OrnamentalUseIndividual": ("Ornamental", OrnamentalUse),
}
for iri_name, (label, cls) in plant_use_map.items():
    add_named_individual(iri_name, cls, label=label)

# Shop layer
ShopProduct = add_class(
    "ShopProduct",
    label="Shop Product",
    comment="An item in the shop inventory."
)
CareLevel = add_class(
    "CareLevel",
    label="Care Level",
    comment="Difficulty of plant care as assessed by the shop."
)
TemperatureCategory = add_class(
    "TemperatureCategory",
    label="Temperature Category",
    comment="Preferred temperature range for a shop product."
)

hasShopProduct = add_object_property(
    "hasShopProduct", domain=Plant, range_=ShopProduct,
    label="has shop product",
    comment="Links a plant species to a shop product."
)
isShopProductFor = add_object_property(
    "isShopProductFor", domain=ShopProduct, range_=Plant,
    characteristics=[OWL.FunctionalProperty],
    label="is shop product for",
    comment="Links a shop product to its plant species."
)
g.add((hasShopProduct, OWL.inverseOf, isShopProductFor))

hasCareLevel = add_object_property(
    "hasCareLevel", domain=ShopProduct, range_=CareLevel,
    characteristics=[OWL.FunctionalProperty],
    label="has care level",
    comment="Care difficulty of this shop product (Easy/Medium/Hard)."
)
hasTemperatureCategory = add_object_property(
    "hasTemperatureCategory", domain=ShopProduct, range_=TemperatureCategory,
    characteristics=[OWL.FunctionalProperty],
    label="has temperature category",
    comment="Preferred temperature range for this product (Warm/Cool/Moderate)."
)

hasProductId = add_datatype_property(
    "hasProductId", domain=ShopProduct, range_=XSD.integer,
    characteristics=[OWL.FunctionalProperty],
    label="has product ID",
    comment="Unique shop SKU."
)
hasProductName = add_datatype_property(
    "hasProductName", domain=ShopProduct, range_=XSD.string,
    characteristics=[OWL.FunctionalProperty],
    label="has product name",
    comment="Commercial name used in the shop (e.g. 'Monstera', 'Peace Lily')."
)
hasStockQuantity = add_datatype_property(
    "hasStockQuantity", domain=ShopProduct, range_=XSD.integer,
    label="has stock quantity",
    comment="Number of units currently on the shelf."
)
hasPriceEur = add_datatype_property(
    "hasPriceEur", domain=ShopProduct, range_=XSD.decimal,
    label="has price (EUR)",
    comment="Retail price in Euros."
)
hasShelfDate = add_datatype_property(
    "hasShelfDate", domain=ShopProduct, range_=XSD.date,
    label="has shelf date",
    comment="Date the product arrived on the shop shelf."
)

add_disjoint_union(CareLevel,
    [PLANT["EasyCare"], PLANT["MediumCare"], PLANT["HardCare"]])

add_disjoint_union(TemperatureCategory,
    [PLANT["WarmCategory"], PLANT["CoolCategory"], PLANT["ModerateCategory"]])

shop_key_list = BNode()
Collection(g, shop_key_list, [hasProductId])
g.add((ShopProduct, OWL.hasKey, shop_key_list))

add_some_values_from(ShopProduct, isShopProductFor, Plant)

add_integer_range_restriction(hasStockQuantity, min_incl=0)
add_decimal_min_restriction(hasPriceEur, min_incl=0)

for iri_name, label in [("EasyCare", "Easy"), ("MediumCare", "Medium"), ("HardCare", "Hard")]:
    add_named_individual(iri_name, CareLevel, label=label)

for iri_name, label in [
    ("WarmCategory", "Warm"),
    ("CoolCategory", "Cool"),
    ("ModerateCategory", "Moderate"),
]:
    add_named_individual(iri_name, TemperatureCategory, label=label)

output_path = Path(__file__).parent.parent / "ontology" / "plant_management.ttl"
rdf_output_path = Path(__file__).parent.parent / "ontology" / "plant_management.rdf"
output_path.parent.mkdir(parents=True, exist_ok=True)


def write_graph(path, rdf_format):
    serialized = g.serialize(format=rdf_format)
    path.write_text(serialized.rstrip() + "\n", encoding="utf-8")


write_graph(output_path, "turtle")
write_graph(rdf_output_path, "xml")

print(f"Ontology written to: {output_path}")
print(f"RDF/XML written to: {rdf_output_path}")
print(f"  Triples : {len(g):,}")

classes = sum(1 for _, p, o in g if p == RDF.type and o == OWL.Class)
obj_props = sum(1 for _, p, o in g if p == RDF.type and o == OWL.ObjectProperty)
dt_props = sum(1 for _, p, o in g if p == RDF.type and o == OWL.DatatypeProperty)
individuals = sum(1 for _, p, o in g if p == RDF.type and o == OWL.NamedIndividual)
print(f"  Classes            : {classes}")
print(f"  Object properties  : {obj_props}")
print(f"  Datatype properties: {dt_props}")
print(f"  Named individuals  : {individuals}")

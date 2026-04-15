"""
Generate OWL2 TBox for the Plant Management System ontology.

Output: ontology/plant_management.ttl

Design decisions and rationale are documented in ontology/README.md.
Run with:  python scripts/generate_ontology.py
Requires:  rdflib >= 6.0  (pip install rdflib)
"""

from pathlib import Path
from rdflib import Graph, Namespace, RDF, RDFS, OWL, XSD, Literal, BNode
from rdflib.collection import Collection

# ---------------------------------------------------------------------------
# Section 1: Namespaces
# ---------------------------------------------------------------------------

PLANT = Namespace("http://www.semanticweb.org/plantms/ontology#")

g = Graph()
g.bind("plant", PLANT)
g.bind("owl", OWL)
g.bind("rdf", RDF)
g.bind("rdfs", RDFS)
g.bind("xsd", XSD)

# ---------------------------------------------------------------------------
# Section 2: Helper functions
# ---------------------------------------------------------------------------

def add_class(name, superclass=OWL.Thing, label=None, comment=None):
    """Declare an owl:Class with optional superclass, label, comment."""
    uri = PLANT[name]
    g.add((uri, RDF.type, OWL.Class))
    g.add((uri, RDFS.subClassOf, superclass))
    g.add((uri, RDFS.label, Literal(label or name, lang="en")))
    if comment:
        g.add((uri, RDFS.comment, Literal(comment, lang="en")))
    return uri


def add_object_property(name, domain=None, range_=None, characteristics=None,
                        label=None, comment=None):
    """Declare an owl:ObjectProperty."""
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
    """Declare an owl:DatatypeProperty."""
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
    """Add: class_uri rdfs:subClassOf [owl:someValuesFrom filler_uri]."""
    restriction = BNode()
    g.add((restriction, RDF.type, OWL.Restriction))
    g.add((restriction, OWL.onProperty, prop_uri))
    g.add((restriction, OWL.someValuesFrom, filler_uri))
    g.add((class_uri, RDFS.subClassOf, restriction))


def add_all_values_from(class_uri, prop_uri, filler_uri):
    """Add: class_uri rdfs:subClassOf [owl:allValuesFrom filler_uri]."""
    restriction = BNode()
    g.add((restriction, RDF.type, OWL.Restriction))
    g.add((restriction, OWL.onProperty, prop_uri))
    g.add((restriction, OWL.allValuesFrom, filler_uri))
    g.add((class_uri, RDFS.subClassOf, restriction))


def add_min_qualified_cardinality(class_uri, prop_uri, n, filler_uri):
    """Add: class_uri rdfs:subClassOf [minQualifiedCardinality n on filler]."""
    restriction = BNode()
    g.add((restriction, RDF.type, OWL.Restriction))
    g.add((restriction, OWL.onProperty, prop_uri))
    g.add((restriction, OWL.minQualifiedCardinality,
           Literal(n, datatype=XSD.nonNegativeInteger)))
    g.add((restriction, OWL.onClass, filler_uri))
    g.add((class_uri, RDFS.subClassOf, restriction))


def add_property_chain(super_prop_uri, chain_prop_uris):
    """Add: super_prop owl:propertyChainAxiom (p1 p2 ...)."""
    chain_list = BNode()
    Collection(g, chain_list, chain_prop_uris)
    g.add((super_prop_uri, OWL.propertyChainAxiom, chain_list))


def add_disjoint_union(parent_uri, member_uris):
    """Add: parent owl:disjointUnionOf (m1 m2 ...)."""
    members_list = BNode()
    Collection(g, members_list, member_uris)
    g.add((parent_uri, OWL.disjointUnionOf, members_list))


def add_all_disjoint_classes(member_uris):
    """Add: [] a owl:AllDisjointClasses; owl:members (m1 m2 ...)."""
    node = BNode()
    g.add((node, RDF.type, OWL.AllDisjointClasses))
    members_list = BNode()
    Collection(g, members_list, member_uris)
    g.add((node, OWL.members, members_list))


def add_named_individual(name, class_uri, label=None):
    """Declare an owl:NamedIndividual of the given class."""
    uri = PLANT[name]
    g.add((uri, RDF.type, OWL.NamedIndividual))
    g.add((uri, RDF.type, class_uri))
    g.add((uri, RDFS.label, Literal(label or name, lang="en")))
    return uri


def add_datatype_range_restriction(prop_uri, facets):
    """
    Add a datatype range restriction using owl:withRestrictions.
    facets: list of (xsd:facet_uri, Literal)
    """
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
    """Add xsd:integer range restriction [min_incl..max_incl]."""
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
    """Add xsd:decimal range restriction [min_incl..∞]."""
    restriction_node = BNode()
    g.add((restriction_node, RDF.type, RDFS.Datatype))
    g.add((restriction_node, OWL.onDatatype, XSD.decimal))
    bn = BNode()
    g.add((bn, XSD.minInclusive, Literal(min_incl, datatype=XSD.decimal)))
    facet_list = BNode()
    Collection(g, facet_list, [bn])
    g.add((restriction_node, OWL.withRestrictions, facet_list))
    g.add((prop_uri, RDFS.range, restriction_node))


# ---------------------------------------------------------------------------
# Section 3: Ontology declaration
# ---------------------------------------------------------------------------

ONTOLOGY_IRI = PLANT[""]

g.add((ONTOLOGY_IRI, RDF.type, OWL.Ontology))
g.add((ONTOLOGY_IRI, RDFS.label,
       Literal("Plant Management System Ontology", lang="en")))
g.add((ONTOLOGY_IRI, RDFS.comment, Literal(
    "OWL2 TBox for the Plant Management System. "
    "Schema only — no instance data. "
    "ABox (individuals from CSV) produced via OBDA in Step 2.",
    lang="en")))
g.add((ONTOLOGY_IRI, OWL.versionInfo, Literal("1.0.0")))

# ---------------------------------------------------------------------------
# Section 4: Class definitions
# ---------------------------------------------------------------------------

# --- Group 1: Taxonomy ---
TaxonomicRank = add_class(
    "TaxonomicRank",
    label="Taxonomic Rank",
    comment="Abstract superclass for taxonomic classification units (Family, Genus). "
            "Enables the property chain belongsToGenus∘isSubsumedByFamily ⊑ belongsToFamily."
)
Family = add_class(
    "Family",
    superclass=TaxonomicRank,
    label="Family",
    comment="Taxonomic family (e.g. Pinaceae, Rosaceae). Maps to CSV column 'family'."
)
Genus = add_class(
    "Genus",
    superclass=TaxonomicRank,
    label="Genus",
    comment="Taxonomic genus (e.g. Abies, Rosa). Maps to CSV column 'genus'."
)
Plant = add_class(
    "Plant",
    label="Plant",
    comment="Main entity. One individual per species row in the CSV. "
            "All plant-level properties are attached here."
)

# --- Group 2: Plant Parts / Componency ODP ---
PlantPart = add_class(
    "PlantPart",
    label="Plant Part",
    comment="Abstract superclass for structural plant components. "
            "Supports the Componency ODP."
)
Flower = add_class(
    "Flower", superclass=PlantPart,
    label="Flower",
    comment="Flower of a plant. Has color (flower_color) and conspicuousness "
            "(flower_conspicuous)."
)
Foliage = add_class(
    "Foliage", superclass=PlantPart,
    label="Foliage",
    comment="Leaves/foliage of a plant. Has color (foliage_color) and texture "
            "(foliage_texture)."
)
Fruit = add_class(
    "Fruit", superclass=PlantPart,
    label="Fruit",
    comment="Fruit of a plant. Has color, conspicuousness, and fruiting months."
)
Root = add_class(
    "Root", superclass=PlantPart,
    label="Root",
    comment="Root system of a plant. Has minimum_root_depth_cm."
)

# --- Group 3: Descriptors ---
Color = add_class(
    "Color",
    label="Color",
    comment="Abstract superclass for all plant-part color descriptors."
)
FlowerColor = add_class(
    "FlowerColor", superclass=Color,
    label="Flower Color",
    comment="Color of a flower (e.g. Blue, Yellow). "
            "Named individuals created from CSV values."
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
    comment="Texture of foliage: fine, medium, or coarse. "
            "Maps to CSV column 'foliage_texture'."
)
GrowthHabit = add_class(
    "GrowthHabit",
    label="Growth Habit",
    comment="Overall growth habit of a plant (Tree, Shrub, Vine, etc.). "
            "CSV 'growth_habit' is comma-separated; a plant can have multiple."
)
GrowthForm = add_class(
    "GrowthForm",
    label="Growth Form",
    comment="Specific growth form (Single Stem, Erect, Rhizomatous, etc.). "
            "Maps to CSV column 'growth_form'."
)
GrowthRate = add_class(
    "GrowthRate",
    label="Growth Rate",
    comment="Rate of growth: Slow, Moderate, or Rapid. "
            "Maps to CSV column 'growth_rate'."
)

# --- Group 4: Ecological Conditions ---
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
    comment="Light requirement (0–10 scale). Maps to CSV column 'light'."
)
HumidityCondition = add_class(
    "HumidityCondition", superclass=HabitatCondition,
    label="Humidity Condition",
    comment="Humidity conditions: ground_humidity and atmospheric_humidity."
)
AnaerobicCondition = add_class(
    "AnaerobicCondition", superclass=HabitatCondition,
    label="Anaerobic Condition",
    comment="Anaerobic tolerance level. Maps to CSV column 'anaerobic_tolerance'."
)

# --- Group 5: Temporal ---
Month = add_class(
    "Month",
    label="Month",
    comment="Calendar month. 12 named individuals (January–December). "
            "Used by bloomsInMonth, fruitingInMonth, growsInMonth."
)
Season = add_class(
    "Season",
    label="Season",
    comment="Season of the year: Spring, Summer, Autumn, Winter."
)
TimeInterval = add_class(
    "TimeInterval",
    label="Time Interval",
    comment="An interval defined by a start and end month. "
            "Optional future use for capturing continuous bloom ranges."
)

# --- Group 6: Geographic ---
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
    comment="Country or state-level region. isSubRegionOf Continent (transitive)."
)

# --- Group 7: N-ary Distribution ODP ---
PlantDistribution = add_class(
    "PlantDistribution",
    label="Plant Distribution",
    comment="Reification class for the N-ary relation Plant × Region × DistributionStatus. "
            "Connects a plant to a region with an optional status (Native, Introduced, etc.)."
)
DistributionStatus = add_class(
    "DistributionStatus",
    label="Distribution Status",
    comment="Status of a plant's presence in a region. "
            "Named individuals: NativeStatus, IntroducedStatus, EndemicStatus, AbsentStatus."
)

# --- Group 8: AgentRole / Plant Use ---
PlantUse = add_class(
    "PlantUse",
    label="Plant Use",
    comment="Abstract superclass for plant use roles (AgentRole ODP). "
            "A plant points to PlantUse individuals rather than inheriting use subclasses."
)
EdibleUse = add_class(
    "EdibleUse", superclass=PlantUse,
    label="Edible Use",
    comment="Plant used as a food source. Maps to CSV 'edible' = true."
)
VegetableUse = add_class(
    "VegetableUse", superclass=PlantUse,
    label="Vegetable Use",
    comment="Plant classified as a vegetable. Maps to CSV 'vegetable' = true."
)
OrnamentalUse = add_class(
    "OrnamentalUse", superclass=PlantUse,
    label="Ornamental Use",
    comment="Plant used for decorative / ornamental purposes."
)

# --- Group 9: Edible Parts ---
EdiblePart = add_class(
    "EdiblePart",
    label="Edible Part",
    comment="The part of a plant that is edible. "
            "Named individuals: FlowerPart, FruitPart, LeafPart, RootPart, SeedPart, StemPart, TuberPart. "
            "Maps to CSV column 'edible_part' (comma-separated)."
)

# ---------------------------------------------------------------------------
# Section 5: Property definitions
# ---------------------------------------------------------------------------

# --- Object Properties ---

# Taxonomy
belongsToFamily = add_object_property(
    "belongsToFamily", domain=Plant, range_=Family,
    characteristics=[OWL.FunctionalProperty],
    label="belongs to family",
    comment="Links a plant to its taxonomic family. Functional (one family per plant). "
            "Can be inferred via: belongsToGenus ∘ isSubsumedByFamily ⊑ belongsToFamily."
)
belongsToGenus = add_object_property(
    "belongsToGenus", domain=Plant, range_=Genus,
    characteristics=[OWL.FunctionalProperty],
    label="belongs to genus",
    comment="Links a plant to its taxonomic genus. Maps to CSV column 'genus'."
)
isSubsumedByFamily = add_object_property(
    "isSubsumedByFamily", domain=Genus, range_=Family,
    characteristics=[OWL.FunctionalProperty],
    label="is subsumed by family",
    comment="Links a genus to its parent family. Enables the property chain axiom."
)

# Componency ODP
hasPart = add_object_property(
    "hasPart", domain=Plant, range_=PlantPart,
    characteristics=[OWL.TransitiveProperty],
    label="has part",
    comment="Transitive part-of relation. Plant hasPart PlantPart (and all sub-parts). "
            "Supports the Componency ODP."
)
isPartOf = add_object_property(
    "isPartOf", domain=PlantPart, range_=Plant,
    characteristics=[OWL.TransitiveProperty],
    label="is part of",
    comment="Inverse of hasPart. Transitive."
)
g.add((hasPart, OWL.inverseOf, isPartOf))

hasComponent = add_object_property(
    "hasComponent", domain=Plant, range_=PlantPart,
    label="has component",
    comment="Direct (non-transitive) structural component. "
            "hasComponent subPropertyOf hasPart. "
            "Plant hasComponent Flower — i.e. this plant HAS a flower."
)
isComponentOf = add_object_property(
    "isComponentOf", domain=PlantPart, range_=Plant,
    label="is component of",
    comment="Inverse of hasComponent."
)
g.add((hasComponent, OWL.inverseOf, isComponentOf))
# hasComponent subPropertyOf hasPart
g.add((hasComponent, RDFS.subPropertyOf, hasPart))

# Descriptors
hasColor = add_object_property(
    "hasColor", domain=PlantPart, range_=Color,
    label="has color",
    comment="Links a plant part (Flower, Foliage, Fruit) to a Color individual. "
            "Type-safe via subclasses FlowerColor, FoliageColor, FruitColor."
)
hasFoliageTexture = add_object_property(
    "hasFoliageTexture", domain=Foliage, range_=FoliageTexture,
    characteristics=[OWL.FunctionalProperty],
    label="has foliage texture",
    comment="Texture of foliage (fine/medium/coarse). Maps to CSV 'foliage_texture'."
)
hasGrowthHabit = add_object_property(
    "hasGrowthHabit", domain=Plant, range_=GrowthHabit,
    label="has growth habit",
    comment="Growth habit of a plant (Tree, Shrub, etc.). "
            "Multi-valued: CSV 'growth_habit' is comma-separated."
)
hasGrowthForm = add_object_property(
    "hasGrowthForm", domain=Plant, range_=GrowthForm,
    label="has growth form",
    comment="Specific growth form. Maps to CSV 'growth_form'."
)
hasGrowthRate = add_object_property(
    "hasGrowthRate", domain=Plant, range_=GrowthRate,
    characteristics=[OWL.FunctionalProperty],
    label="has growth rate",
    comment="Rate of growth (Slow/Moderate/Rapid). Functional. Maps to CSV 'growth_rate'."
)

# Temporal
bloomsInMonth = add_object_property(
    "bloomsInMonth", domain=Plant, range_=Month,
    label="blooms in month",
    comment="Month(s) when the plant blooms. "
            "Maps to CSV 'bloom_months' (space-separated integers)."
)
fruitingInMonth = add_object_property(
    "fruitingInMonth", domain=Plant, range_=Month,
    label="fruiting in month",
    comment="Month(s) when the plant fruits. Maps to CSV 'fruit_months'."
)
growsInMonth = add_object_property(
    "growsInMonth", domain=Plant, range_=Month,
    label="grows in month",
    comment="Month(s) of active growth. Maps to CSV 'growth_months'."
)

# Ecological
requiresCondition = add_object_property(
    "requiresCondition", domain=Plant, range_=HabitatCondition,
    label="requires condition",
    comment="Abstract link from a plant to an ecological condition type. "
            "Numeric condition values are also expressed as datatype properties."
)

# N-ary Distribution ODP
hasDistribution = add_object_property(
    "hasDistribution", domain=Plant, range_=PlantDistribution,
    label="has distribution",
    comment="Links a plant to a PlantDistribution node (N-ary ODP). "
            "Each node connects the plant to a region with an optional status."
)
distributionForPlant = add_object_property(
    "distributionForPlant", domain=PlantDistribution, range_=Plant,
    label="distribution for plant",
    comment="Inverse of hasDistribution."
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

# AgentRole ODP
hasPlantUse = add_object_property(
    "hasPlantUse", domain=Plant, range_=PlantUse,
    label="has plant use",
    comment="Links a plant to its use role(s) (AgentRole ODP). "
            "Avoids class explosion by using role individuals."
)
hasEdiblePart = add_object_property(
    "hasEdiblePart", domain=Plant, range_=EdiblePart,
    label="has edible part",
    comment="Which parts of the plant are edible. "
            "Multi-valued, maps to CSV 'edible_part' (comma-separated)."
)

# --- Datatype Properties ---

hasTrefleId = add_datatype_property(
    "hasTrefleId", domain=Plant, range_=XSD.integer,
    characteristics=[OWL.FunctionalProperty],
    label="has Trefle ID",
    comment="Unique numeric identifier from the Trefle database. Maps to CSV 'id'."
)
hasScientificName = add_datatype_property(
    "hasScientificName", domain=Plant, range_=XSD.string,
    characteristics=[OWL.FunctionalProperty],
    label="has scientific name",
    comment="Scientific name of the species. Maps to CSV 'scientific_name'."
)
hasCommonName = add_datatype_property(
    "hasCommonName", domain=Plant, range_=XSD.string,
    label="has common name",
    comment="Common name(s) of the plant. Multi-valued."
)
hasSynonymName = add_datatype_property(
    "hasSynonymName", domain=Plant, range_=XSD.string,
    label="has synonym name",
    comment="Taxonomic synonyms. Multi-valued, comma-separated in CSV 'synonyms'."
)
hasYear = add_datatype_property(
    "hasYear", domain=Plant, range_=XSD.integer,
    label="has year",
    comment="Year of taxonomic publication. Maps to CSV 'year'."
)
hasAuthor = add_datatype_property(
    "hasAuthor", domain=Plant, range_=XSD.string,
    label="has author",
    comment="Author of the taxonomic description. Maps to CSV 'author'."
)
hasMaximumHeightCm = add_datatype_property(
    "hasMaximumHeightCm", domain=Plant, range_=XSD.decimal,
    label="has maximum height (cm)",
    comment="Maximum height in centimetres. Maps to CSV 'maximum_height_cm'. Must be ≥ 0."
)
hasAverageHeightCm = add_datatype_property(
    "hasAverageHeightCm", domain=Plant, range_=XSD.decimal,
    label="has average height (cm)",
    comment="Average height in centimetres. Maps to CSV 'average_height_cm'. Must be ≥ 0."
)
hasMinimumRootDepthCm = add_datatype_property(
    "hasMinimumRootDepthCm", domain=Plant, range_=XSD.decimal,
    label="has minimum root depth (cm)",
    comment="Minimum root depth in centimetres. Maps to CSV 'minimum_root_depth_cm'."
)
hasLightRequirement = add_datatype_property(
    "hasLightRequirement", domain=Plant, range_=XSD.integer,
    label="has light requirement",
    comment="Light requirement on a 0–10 scale. Maps to CSV 'light'."
)
hasPhMinimum = add_datatype_property(
    "hasPhMinimum", domain=Plant, range_=XSD.decimal,
    label="has pH minimum",
    comment="Minimum soil pH. Range [0.0, 14.0]. Maps to CSV 'ph_minimum'."
)
hasPhMaximum = add_datatype_property(
    "hasPhMaximum", domain=Plant, range_=XSD.decimal,
    label="has pH maximum",
    comment="Maximum soil pH. Range [0.0, 14.0]. Maps to CSV 'ph_maximum'."
)
hasSoilNutriments = add_datatype_property(
    "hasSoilNutriments", domain=Plant, range_=XSD.integer,
    label="has soil nutriments",
    comment="Soil nutriment requirement (0–10). Maps to CSV 'soil_nutriments'."
)
hasSoilSalinity = add_datatype_property(
    "hasSoilSalinity", domain=Plant, range_=XSD.integer,
    label="has soil salinity",
    comment="Soil salinity tolerance (0–10). Maps to CSV 'soil_salinity'."
)
hasGroundHumidity = add_datatype_property(
    "hasGroundHumidity", domain=Plant, range_=XSD.integer,
    label="has ground humidity",
    comment="Ground humidity requirement (0–10). Maps to CSV 'ground_humidity'."
)
hasAtmosphericHumidity = add_datatype_property(
    "hasAtmosphericHumidity", domain=Plant, range_=XSD.integer,
    label="has atmospheric humidity",
    comment="Atmospheric humidity requirement (0–10). Maps to CSV 'atmospheric_humidity'."
)
hasAnaerobicTolerance = add_datatype_property(
    "hasAnaerobicTolerance", domain=Plant, range_=XSD.integer,
    label="has anaerobic tolerance",
    comment="Tolerance for anaerobic conditions (0–10). Maps to CSV 'anaerobic_tolerance'."
)
isEdible = add_datatype_property(
    "isEdible", domain=Plant, range_=XSD.boolean,
    label="is edible",
    comment="True if the plant is edible. Maps to CSV 'edible'."
)
isVegetable = add_datatype_property(
    "isVegetable", domain=Plant, range_=XSD.boolean,
    label="is vegetable",
    comment="True if the plant is classified as a vegetable. Maps to CSV 'vegetable'."
)
hasFlowerConspicuous = add_datatype_property(
    "hasFlowerConspicuous", domain=Flower, range_=XSD.boolean,
    label="has conspicuous flower",
    comment="Whether the flower is conspicuous. Maps to CSV 'flower_conspicuous'."
)
hasFruitConspicuous = add_datatype_property(
    "hasFruitConspicuous", domain=Fruit, range_=XSD.boolean,
    label="has conspicuous fruit",
    comment="Whether the fruit is conspicuous. Maps to CSV 'fruit_conspicuous'."
)
hasPlantingDaysToHarvest = add_datatype_property(
    "hasPlantingDaysToHarvest", domain=Plant, range_=XSD.integer,
    label="has planting days to harvest",
    comment="Days from planting to harvest. Maps to CSV 'planting_days_to_harvest'."
)
hasPlantingSpreadCm = add_datatype_property(
    "hasPlantingSpreadCm", domain=Plant, range_=XSD.decimal,
    label="has planting spread (cm)",
    comment="Spread of the plant at maturity (cm). Maps to CSV 'planting_spread_cm'."
)
hasImageUrl = add_datatype_property(
    "hasImageUrl", domain=Plant, range_=XSD.anyURI,
    label="has image URL",
    comment="URL of a representative plant image. Maps to CSV 'image_url'."
)
hasWikipediaUrl = add_datatype_property(
    "hasWikipediaUrl", domain=Plant, range_=XSD.anyURI,
    label="has Wikipedia URL",
    comment="URL of the Wikipedia article. Maps to CSV 'url_wikipedia_en'."
)
hasBibliography = add_datatype_property(
    "hasBibliography", domain=Plant, range_=XSD.string,
    label="has bibliography",
    comment="Bibliographic reference for the taxon. Maps to CSV 'bibliography'."
)
hasPlantingRowSpacingCm = add_datatype_property(
    "hasPlantingRowSpacingCm", domain=Plant, range_=XSD.decimal,
    label="has planting row spacing (cm)",
    comment="Recommended row spacing in centimetres. Maps to CSV 'planting_row_spacing_cm'."
)

# ---------------------------------------------------------------------------
# Section 6: OWL2 Axioms
# ---------------------------------------------------------------------------

# 6a. AllDisjointClasses
add_all_disjoint_classes([Family, Genus, Plant])
add_all_disjoint_classes([Flower, Foliage, Fruit, Root])
add_all_disjoint_classes([EdibleUse, VegetableUse, OrnamentalUse])

# 6b. DisjointUnionOf
# GrowthHabit — 7 members (from actual CSV values)
Tree = PLANT["Tree"]
Shrub = PLANT["Shrub"]
Vine = PLANT["Vine"]
Subshrub = PLANT["Subshrub"]
ForbHerb = PLANT["ForbHerb"]
Graminoid = PLANT["Graminoid"]
Nonvascular = PLANT["Nonvascular"]
add_disjoint_union(GrowthHabit, [Tree, Shrub, Vine, Subshrub, ForbHerb, Graminoid, Nonvascular])

# Month — 12 members
months_uris = [PLANT[m] for m in [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
]]
add_disjoint_union(Month, months_uris)

# Season — 4 members
season_uris = [PLANT[s] for s in ["Spring", "Summer", "Autumn", "Winter"]]
add_disjoint_union(Season, season_uris)

# GrowthRate — 3 members
add_disjoint_union(GrowthRate,
    [PLANT["SlowGrowthRate"], PLANT["ModerateGrowthRate"], PLANT["RapidGrowthRate"]])

# 6c. Property Chain Axioms
# Chain 1: belongsToGenus ∘ isSubsumedByFamily ⊑ belongsToFamily
add_property_chain(belongsToFamily, [belongsToGenus, isSubsumedByFamily])

# Chain 2: hasComponent ∘ hasPart ⊑ hasPart  (already covered by subPropertyOf + transitivity,
# but we add it explicitly to satisfy the OWL2 feature requirement)
add_property_chain(hasPart, [hasComponent, hasPart])

# 6d. Existential restrictions (owl:someValuesFrom)
# Plant must belong to at least one genus
add_some_values_from(Plant, belongsToGenus, Genus)
# Plant must belong to at least one family (also inferred via chain)
add_some_values_from(Plant, belongsToFamily, Family)
# Plant must have at least one distribution
add_some_values_from(Plant, hasDistribution, PlantDistribution)

# 6e. Universal restrictions (owl:allValuesFrom)
# hasColor always points to a Color
add_all_values_from(PlantPart, hasColor, Color)
# inRegion always points to a Region
add_all_values_from(PlantDistribution, inRegion, Region)

# 6f. Qualified minimum cardinality (owl:minQualifiedCardinality)
# Plant must have at least 1 component that is a PlantPart
add_min_qualified_cardinality(Plant, hasComponent, 1, PlantPart)

# 6g. owl:hasKey — hasTrefleId uniquely identifies a Plant
key_list = BNode()
Collection(g, key_list, [hasTrefleId])
g.add((Plant, OWL.hasKey, key_list))

# 6h. Datatype range restrictions

# Light: integer in [0, 10]
add_integer_range_restriction(hasLightRequirement, min_incl=0, max_incl=10)

# 0–10 integer columns
for prop in [hasSoilNutriments, hasSoilSalinity, hasGroundHumidity,
             hasAtmosphericHumidity, hasAnaerobicTolerance]:
    add_integer_range_restriction(prop, min_incl=0, max_incl=10)

# Heights and depths: decimal ≥ 0
for prop in [hasMaximumHeightCm, hasAverageHeightCm, hasMinimumRootDepthCm,
             hasPlantingSpreadCm, hasPlantingRowSpacingCm]:
    add_decimal_min_restriction(prop, min_incl=0)

# pH: decimal in [0.0, 14.0]
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

# Days to harvest: integer ≥ 0
add_integer_range_restriction(hasPlantingDaysToHarvest, min_incl=0)

# ---------------------------------------------------------------------------
# Section 7: Named Individuals (controlled vocabularies)
# ---------------------------------------------------------------------------

# Months
month_names = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
]
for m in month_names:
    add_named_individual(m, Month, label=m)

# Seasons
for s in ["Spring", "Summer", "Autumn", "Winter"]:
    add_named_individual(s, Season, label=s)

# GrowthHabit — from CSV actual values
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

# GrowthRate
growth_rate_map = {
    "SlowGrowthRate": "Slow",
    "ModerateGrowthRate": "Moderate",
    "RapidGrowthRate": "Rapid",
}
for iri_name, label in growth_rate_map.items():
    add_named_individual(iri_name, GrowthRate, label=label)

# GrowthForm — from CSV actual values
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

# FoliageTexture
for iri_name, label in [("FineTexture", "Fine"), ("MediumTexture", "Medium"),
                         ("CoarseTexture", "Coarse")]:
    add_named_individual(iri_name, FoliageTexture, label=label)

# FlowerColor (from CSV unique values)
flower_colors = ["Blue", "Purple", "Yellow", "White", "Red", "Orange",
                 "Green", "Brown", "Black"]
for c in flower_colors:
    add_named_individual(f"FlowerColor_{c}", FlowerColor, label=c)

# FoliageColor
foliage_colors = ["Green", "Grey", "Red", "Yellow"]
for c in foliage_colors:
    add_named_individual(f"FoliageColor_{c}", FoliageColor, label=c)

# FruitColor
fruit_colors = ["Black", "Blue", "Brown", "Green", "Orange", "Purple",
                "Red", "White", "Yellow"]
for c in fruit_colors:
    add_named_individual(f"FruitColor_{c}", FruitColor, label=c)

# DistributionStatus
for iri_name, label in [
    ("NativeStatus", "Native"),
    ("IntroducedStatus", "Introduced"),
    ("EndemicStatus", "Endemic"),
    ("AbsentStatus", "Absent"),
]:
    add_named_individual(iri_name, DistributionStatus, label=label)

# EdiblePart — from CSV actual values
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

# PlantUse individuals
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

# ---------------------------------------------------------------------------
# Section 8: Serialize
# ---------------------------------------------------------------------------

output_path = Path(__file__).parent.parent / "ontology" / "plant_management.ttl"
output_path.parent.mkdir(parents=True, exist_ok=True)
g.serialize(str(output_path), format="turtle")

print(f"Ontology written to: {output_path}")
print(f"  Triples : {len(g):,}")

# Quick summary
from collections import Counter
type_counts = Counter(str(o) for _, p, o in g if p == RDF.type)
classes = sum(1 for _, p, o in g if p == RDF.type and o == OWL.Class)
obj_props = sum(1 for _, p, o in g if p == RDF.type and o == OWL.ObjectProperty)
dt_props = sum(1 for _, p, o in g if p == RDF.type and o == OWL.DatatypeProperty)
individuals = sum(1 for _, p, o in g if p == RDF.type and o == OWL.NamedIndividual)
print(f"  Classes            : {classes}")
print(f"  Object properties  : {obj_props}")
print(f"  Datatype properties: {dt_props}")
print(f"  Named individuals  : {individuals}")

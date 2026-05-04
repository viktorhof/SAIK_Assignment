# OOPS Findings

This file records the ontology issues reported by the OOPS! validator for
`ontology/plant_management.ttl`.

## Summary

- `P04` Creating unconnected ontology elements: 3 cases (`Minor`)
- `P13` Inverse relationships not explicitly declared: 19 cases (`Minor`)
- `P19` Defining multiple domains or ranges in properties: 16 cases (`Critical`)
- `P29` Defining wrong transitive relationships: 2 cases (`Critical`)
- `P41` No license declared: ontology-level issue (`Important`)

## P04 - Creating unconnected ontology elements

The following ontology elements were reported as isolated:

- `http://www.semanticweb.org/plantms/ontology#Season`
- `http://www.semanticweb.org/plantms/ontology#TaxonomicRank`
- `http://www.semanticweb.org/plantms/ontology#TimeInterval`

What this means:

These classes exist in the ontology, but OOPS did not detect enough connections
from them to the rest of the model through properties, restrictions, or broader
usage patterns.

How serious it is:

This is usually a modeling cleanliness issue rather than a logic error. The
ontology can still work correctly, but these classes may look unfinished or
underused.

How it could be fixed:

- `Season`: connect it to the rest of the ontology with properties such as a
  relation from `Month` to `Season`, or use it in a restriction or query-driven
  pattern.
- `TaxonomicRank`: keep it if it is needed as an abstract superclass for
  `Family` and `Genus`, but consider adding a short justification in the
  documentation if it remains only a hierarchy helper.
- `TimeInterval`: either connect it to month-based modeling with explicit
  properties such as start and end month, or remove it if it is only planned
  for future use and not required in the final submission.

## P13 - Inverse relationships not explicitly declared

The following relationships were reported as missing an explicit `owl:inverseOf`:

- `http://www.semanticweb.org/plantms/ontology#hasGrowthRate`
- `http://www.semanticweb.org/plantms/ontology#hasDistributionStatus`
- `http://www.semanticweb.org/plantms/ontology#isSubRegionOf`
- `http://www.semanticweb.org/plantms/ontology#requiresCondition`
- `http://www.semanticweb.org/plantms/ontology#hasTemperatureCategory`
- `http://www.semanticweb.org/plantms/ontology#fruitingInMonth`
- `http://www.semanticweb.org/plantms/ontology#hasColor`
- `http://www.semanticweb.org/plantms/ontology#inRegion`
- `http://www.semanticweb.org/plantms/ontology#hasFoliageTexture`
- `http://www.semanticweb.org/plantms/ontology#hasGrowthHabit`
- `http://www.semanticweb.org/plantms/ontology#growsInMonth`
- `http://www.semanticweb.org/plantms/ontology#hasGrowthForm`
- `http://www.semanticweb.org/plantms/ontology#isSubsumedByFamily`
- `http://www.semanticweb.org/plantms/ontology#bloomsInMonth`
- `http://www.semanticweb.org/plantms/ontology#hasCareLevel`
- `http://www.semanticweb.org/plantms/ontology#hasPlantUse`
- `http://www.semanticweb.org/plantms/ontology#belongsToFamily`
- `http://www.semanticweb.org/plantms/ontology#hasEdiblePart`
- `http://www.semanticweb.org/plantms/ontology#belongsToGenus`

What this means:

OOPS prefers object properties to have explicitly declared inverse properties.
For example, if a plant `belongsToFamily` a family, OOPS expects a matching
inverse such as a family property pointing back to the plant.

How serious it is:

This is a minor warning. Missing inverses do not automatically make the
ontology wrong. Many ontologies intentionally define only the direction that is
actually needed for queries or reasoning.

How it could be fixed:

- Add inverse properties where they are meaningful and useful, for example:
  `belongsToFamily` / `hasMemberPlant`,
  `belongsToGenus` / `hasGenusMember`,
  `hasPlantUse` / `isUseOfPlant`,
  `bloomsInMonth` / `isBloomMonthOf`.
- Do not add inverse properties only to satisfy the tool if they make the model
  harder to read or are never used.
- In the write-up, it is acceptable to explain that some inverses were omitted
  on purpose to keep the schema compact.

## P19 - Defining multiple domains or ranges in properties

The following properties were reported:

- `http://www.semanticweb.org/plantms/ontology#hasPlantingDaysToHarvest`
- `http://www.semanticweb.org/plantms/ontology#hasSoilNutriments`
- `http://www.semanticweb.org/plantms/ontology#hasPlantingSpreadCm`
- `http://www.semanticweb.org/plantms/ontology#hasPhMinimum`
- `http://www.semanticweb.org/plantms/ontology#hasAtmosphericHumidity`
- `http://www.semanticweb.org/plantms/ontology#hasMinimumRootDepthCm`
- `http://www.semanticweb.org/plantms/ontology#hasMaximumHeightCm`
- `http://www.semanticweb.org/plantms/ontology#hasPlantingRowSpacingCm`
- `http://www.semanticweb.org/plantms/ontology#hasStockQuantity`
- `http://www.semanticweb.org/plantms/ontology#hasAnaerobicTolerance`
- `http://www.semanticweb.org/plantms/ontology#hasSoilSalinity`
- `http://www.semanticweb.org/plantms/ontology#hasLightRequirement`
- `http://www.semanticweb.org/plantms/ontology#hasPriceEur`
- `http://www.semanticweb.org/plantms/ontology#hasPhMaximum`
- `http://www.semanticweb.org/plantms/ontology#hasAverageHeightCm`
- `http://www.semanticweb.org/plantms/ontology#hasGroundHumidity`

What this means:

OOPS believes these properties may have been defined with multiple domain or
range statements. In OWL, multiple `rdfs:domain` or `rdfs:range` axioms are not
alternatives. They are interpreted together as an intersection, which can lead
to unintended semantics.

How serious it is:

This one is marked as critical by OOPS because it can reflect a real modeling
mistake. However, in this ontology it should be checked carefully before being
treated as an actual error. Some OWL tools flag complex datatype range
restrictions even when the ontology is still valid.

How it could be fixed:

- Review each listed property and confirm whether it truly has more than one
  domain or range axiom.
- If a property was meant to apply to one class only, keep a single clear
  `rdfs:domain`.
- If the issue comes from datatype restrictions, consider simplifying the
  declaration or rewriting it in a form that OOPS interprets more clearly.
- If the ontology is valid OWL and the warning is only caused by the way the
  datatype restriction is written, document this as a tool limitation rather
  than changing the model unnecessarily.

## P29 - Defining wrong transitive relationships

The following relationships were reported as incorrectly transitive:

- `http://www.semanticweb.org/plantms/ontology#hasPart`
- `http://www.semanticweb.org/plantms/ontology#isPartOf`

What this means:

OOPS is warning that these relationships may not always be safely transitive.
For example, if a plant has a flower and a flower has a petal, transitivity can
be useful. But if domain and range are too narrow, transitivity may force
unintended inferences.

How serious it is:

This is the most important modeling warning in the report. If transitivity is
used carelessly, it can introduce incorrect class inferences and make the
ontology harder to reason over correctly.

How it could be fixed:

- Recheck whether `hasPart` and `isPartOf` really need to be transitive for the
  assignment requirements.
- If transitivity is needed, broaden the domain and range so they do not imply
  that every intermediate part must also be a `Plant` or every whole must also
  be a `PlantPart`.
- If transitivity is not essential, remove `owl:TransitiveProperty` and keep
  only the direct component relation.
- Test the revised ontology again in a reasoner after the change.

## P41 - No license declared

OOPS reported that the ontology metadata does not declare a license.

What this means:

The ontology header includes label, comments, and version information, but no
statement about the usage license.

How serious it is:

This does not affect reasoning or ontology validity, but it is an important
metadata omission in a final deliverable.

How it could be fixed:

- Add a license triple in the ontology header, for example using
  `dcterms:license` or another common vocabulary.
- If the course does not prescribe a license, use a standard open license and
  mention it in the documentation as well.

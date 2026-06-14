# OOPS Second Scan

This file records the OOPS! scan result after applying the ontology fixes to
`ontology/plant_management_oops_fixed.ttl`.

## Summary

| Pitfall | Severity | Meaning | Count |
|---|---|---|---:|
| P04 | Minor | Creating unconnected ontology elements | 1 |
| P20 | Minor | Misusing ontology annotations | 5 |

No critical or important issue remains in the second scan result.

## Remaining Findings

### P04 - Creating unconnected ontology elements

OOPS reports one remaining unconnected ontology element:

- `http://www.semanticweb.org/plantms/ontology#TaxonomicRank`

This class is kept intentionally as an abstract superclass for `Family` and
`Genus`. It supports the taxonomy model and does not affect the generated KG.
For example, the generated KG contains family resources such as `Araceae` and
genus resources such as `Monstera`; both are part of the taxonomy model that
`TaxonomicRank` documents at schema level.

### P20 - Misusing ontology annotations

OOPS reports five minor annotation warnings for inverse helper properties:

- `http://www.semanticweb.org/plantms/ontology#isFruitingMonthOf`
- `http://www.semanticweb.org/plantms/ontology#temperatureCategoryOfProduct`
- `http://www.semanticweb.org/plantms/ontology#isGrowthMonthOf`
- `http://www.semanticweb.org/plantms/ontology#careLevelOfProduct`
- `http://www.semanticweb.org/plantms/ontology#isBloomMonthOf`

These warnings concern annotation quality. They do not indicate an ontology
consistency problem and do not affect KG materialisation or reasoning.
For example, `isBloomMonthOf` is the inverse helper for bloom-month navigation,
and `careLevelOfProduct` is the inverse helper for shop care-level navigation.
These properties help reverse query patterns, but the P20 warnings are about
their annotations rather than the underlying object-property semantics.

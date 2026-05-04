# OOPS Fixes

This file records the follow-up artifact for the OOPS! findings in
`OOPS_FINDINGS.md`.

## Summary

- `P04`: partly fixed.
- `P13`: fixed where inverse properties are useful.
- `P19`: fixed.
- `P29`: fixed.
- `P41`: fixed.

## Reproduce

```bash
python scripts/generate_ontology.py
python scripts/apply_oops_fixes.py
```

The first command recreates the original ontology artifact. The second command
creates the OOPS-fixed follow-up artifacts:

- `ontology/plant_management_oops_fixed.ttl`
- `ontology/plant_management_oops_fixed.rdf`

## Fixed Items

- `P04`: connected `Season` to `Month` with `inSeason` / `hasMonth`, kept
  `TaxonomicRank` as the superclass of `Family` and `Genus`, and removed the
  unused `TimeInterval` class.
- `P13`: added useful inverse properties for taxonomy, months, regions, plant
  uses, edible parts, care levels, temperature categories, growth descriptors,
  colors, and conditions.
- `P19`: changed restricted numeric datatype properties so each property has
  only one `rdfs:range`, using the OWL datatype restriction as that range.
- `P29`: removed transitivity from `hasPart` and `isPartOf`, and removed the
  part propagation property chain.
- `P41`: added `dcterms:license` with CC BY 4.0.

## Not Done Here

- SHACL validation is still separate Task 3 work.
- The online OOPS scan should be run again manually after these ontology changes.

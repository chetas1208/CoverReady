# CoverReady Taxonomy

This package stores versioned underwriting evidence rulesets and scoring inputs.

- `base_small_business.v1.json` defines the baseline document, safety, operational, coverage, and renewal requirements.
- `restaurant_overlay.v1.json` adds restaurant-specific cooking and fire-safety requirements.

The API scoring engine treats these files as the single source of truth for:

- deterministic requirement points
- evidence fields and accepted document types
- critical missing-document caps
- human-readable missing-document labels


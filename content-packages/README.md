# Reviewed content packages

Packages are immutable, versioned JSON documents. The catalog exposes only packages whose `review_status` is `reviewed`; drafts are validated but unavailable to learners.

The Day 1 package is `python-functions` version `1.0.0`. It covers Python parameters, return values, and the print-versus-return misconception in Arabic and English. Each item carries package-owned tests, evidence references, misconception metadata, and transfer metadata.

When adding a package, preserve old versions, use stable item IDs, include both language variants, and update the evaluation fixtures before changing the API contract.

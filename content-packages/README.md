# Versioned learning content

This directory reserves a trackable location for Asser's content packages. No content package or reviewed topic is included in Moustafa's Day 1 implementation.

The first prototype will use one reviewed programming topic. A session pins a `content_package_id` and `content_version`; submissions reference an `item_id` within that version. Asser owns the initial package and the content catalog adapter that validates these references. Ahmed owns labeled evaluation fixtures under `backend/tests/fixtures/evaluations/`.

When content is added, retain each referenced version and record the topic, instructional language, review status, and item identifiers. A draft must not be exposed as selectable reviewed content. Coordinate the package format with Ahmed and Mohamed before integration.

UI locale and instructional language are separate session preferences. Content/evaluation design must preserve separate outcome and reasoning verdicts and explicit `uncertain` results when evidence is insufficient. A wrong answer alone must not label a misconception.

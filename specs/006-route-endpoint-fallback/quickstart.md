# Quickstart: Route Endpoint Fallback

**Feature**: [spec.md](spec.md) | **Date**: 2026-10-29

Proves tag-less routes serve endpoint stop names as
origin/destination, identically in all three shapes, per
[contracts/endpoint-fallback.md](contracts/endpoint-fallback.md).
Follows the 003 quickstart's backend setup (database up,
migrations applied, `createcachetable` done, dataset
imported per `specs/002-osm-snapshot-import`); no new
setup of any kind.

## 1. Detail fallback (Story 1)

1. Pick a servable route with blank stored origin/
   destination and recorded stops — expect detail
   `origin` = first ordered stop's name, `destination` =
   last ordered stop's name.
2. Pick a route with stored text — expect the stored
   values byte-identically (compare against the pre-change
   response if available).
3. Pick a servable route with no stops — expect explicit
   `null` origin/destination, not invented names.
4. Pick a single-stop route — expect the same stop name
   as both origin and destination.

## 2. Cross-shape agreement (Story 2)

1. For the tag-less route from step 1, read the routes
   list (via search or browse) — expect identical
   origin/destination to its detail.
2. Run a connectivity query the route serves — expect
   identical origin/destination in that result too.
3. Read an unknown id — expect the existing
   plain-language 404, unchanged.

## 3. Regression sweep

1. Run the full backend suite — expect green with zero
   modifications to pre-existing behavior tests
   (SC-003); only new fallback tests and updated
   query-count bounds.
2. Confirm `git status` shows zero frontend changes and
   zero migration files.

## Done when

All three steps succeed, the automated suite is green, and
review confirms the contract delta holds: values change,
shape frozen, stored text always wins.

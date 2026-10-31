# Quickstart: Ranked Journey Options

**Feature**: [spec.md](spec.md) | **Contracts**: [contracts/answer.md](contracts/answer.md) | **Data model**: [data-model.md](data-model.md)

Validates ranked answers end to end: all verified options grouped by operator, hints only where supported, capped destination members, no invented content.

## Prerequisites

- Backend deps installed; Postgres running; `DJANGO_SECRET_KEY` set.
- No model key needed for ranking tests (deterministic ranking over stubbed matrix results; model drafts verified as before).

## Run the gates

```bash
# backend — ranked-answer tests alongside the existing suites
python backend/manage.py test apps.journey apps.transport tests
```

Expected: full suite green, including KSRTC-only (KSRTC wording), mixed-operator (2 groups), and no-times tests.

## Manual validation (dev servers running)

1. Ask a journey with several direct services → expect `option_groups` per operator, every option evidence-linked, deterministic order across repeats.
2. Ask a journey with hint-supporting data → expect `boarding_hint` naming the boarding point; ask one without → expect no hint and no invented stand.
3. Ask into a multi-stop place → expect `destinations` with up to 5 reachable members, each evidence-linked.
4. Ask with one verified service → expect a one-item list; ask with none → expect the honest refusal shape, unchanged.

## What good looks like

- Mixed operators yield one group per operator (unknown last); KSRTC-only yields KSRTC wording.
- Answer text contains no times and no transfers; every route links to `/routes/:id` evidence.

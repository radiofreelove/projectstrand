# ADR-0005: Sources and facts are data, and the build enforces them

- Status: accepted
- Date: 2026-11-03

## Context

Legal guides go stale quietly. A fee changes in one place and stays wrong in three others. Readers cannot tell what was checked, or when.

## Decision

- Every source is an entry in `data/sources.yml` with an id, title, publisher, URL, version date, the date we checked it, and a status (`verified`, `secondary`, `unverified`, `linked`).
- Every number or detail that changes (fees, addresses, phone numbers, dates) is an entry in `data/facts.yml` that names its sources.
- Templates cite with `src("id")` and use values with `fact("id")`. The build fails on an unknown id.
- Each page automatically lists the sources it used, with dates and labels.
- The build publishes `sources.json`, `facts.json`, and `build-report.json` so anyone can audit the data.
- Sources older than `max_source_age_days` (120) appear as warnings in the build report and the weekly scheduled check.

## Consequences

Updating a fee is a one-line change. Every claim is traceable. The audit trail is machine-readable as well as human-readable.

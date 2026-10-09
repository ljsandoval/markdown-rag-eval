---
tags: [runbook]
area: platform
created: 2027-03-15
---

# Recover a Data Gap

What to do after an interruption in ingest has left a window with no observations.

## Establish the boundaries

Find the last observation before the gap and the first after it, per station. Do not assume the gap is the same width for every station, because the collector skips stations independently and an outage rarely starts cleanly.

## Procedure

Work one station at a time for small gaps and in batches by region for large ones.

### If the gap is under an hour

Run [[sensor-backfill]] for the affected station and the gap window rounded outward to the nearest hour. Overlap is harmless because backfill is idempotent.

#### Verifying afterwards

Re-query the window and confirm the observation count matches the expected count, which is ten per hour per station. A count that is short by a handful usually means the station itself was down rather than the collector, which is not something backfill can fix.

### If the gap is over an hour

Check whether the upstream station API still holds the window at all. Most stations retain seventy two hours and a few retain only twenty four, so a long gap discovered late may be unrecoverable for part of the network. Record what was unrecoverable rather than leaving it implicit.

## Afterwards

Observations written by backfill carry the same quality flags as live ones, so a recovered window is not marked as recovered anywhere. If that distinction matters it has to be derived from the write timestamp. Flag meanings are in [[quality-flags]] and the live pipeline is [[tide-gauge-ingest]].


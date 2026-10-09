---
tags: [project, ingest]
area: platform
created: 2027-02-03
---

# Sensor Backfill

A separate job that fetches historical observations for a station and time range, used to fill gaps left by outages or by stations that were offline. Owned by [[jun-okafor]].

## Why it is separate from the collector

The collector is tuned for a fixed six minute cycle and a predictable write volume. Backfill is bursty by nature, occasionally writing tens of thousands of rows at once, and mixing the two would make the collector's timing unpredictable. Keeping them apart means a large backfill can be throttled or paused without touching live ingest. The live pipeline is [[tide-gauge-ingest]].

## Invocation

Backfill takes a station identifier and an inclusive date range. It refuses ranges longer than thirty days in a single call, because the upstream station API pages at a thousand observations and a longer range makes the job's runtime hard to predict.

## Duplicate handling

Backfill writes are idempotent on the pair of station identifier and observation timestamp. Re-running a range that was already filled is safe and is the expected recovery action after a partial failure. The procedure that uses this is [[recover-a-data-gap]].


---
tags: [project, ingest]
area: platform
created: 2027-01-12
---

# Tide Gauge Ingest

The pipeline that pulls water level observations from the station network and lands them in Postgres. Owned by [[avery-lin]].

## Current shape

The collector polls every station on a six minute cycle and writes observations directly to the `observations` table in Postgres. There is no queue and no streaming tier between the collector and the database. That is deliberate and the reasoning is in [[retire-the-kafka-tier]].

Each write carries a station identifier, an observation timestamp in UTC, a water level in metres, and a quality flag. The flag vocabulary is defined in [[quality-flags]] and the station fields are described in [[station-metadata-schema]].

## Cycle timing

A full cycle takes between forty and ninety seconds depending on how many stations are slow to answer. The collector does not wait for stragglers past a thirty second timeout; a station that times out is skipped and picked up on the next cycle, which means a single slow station costs at most one cycle of data rather than blocking the whole run.

## Backfill

Gaps are filled separately rather than by the collector. See [[sensor-backfill]] for the backfill job and [[recover-a-data-gap]] for the procedure after an outage.

## Known limitations

The collector holds no state between cycles, so it cannot tell the difference between a station that has never reported and one that stopped reporting an hour ago. Detecting that is the monitoring layer's job and it is not built yet.

Observations arriving more than two hours late are written with their true observation timestamp, which means a late batch can appear behind data that was already queried. Nothing downstream currently reacts to that.


---
tags: [reference, schema]
area: platform
created: 2027-01-18
---

# Quality Flags

Every observation carries a flag recording what the ingest checks concluded about the reading.

## Flag values

| Flag | Meaning |
|---|---|
| 0 | Passed every check. |
| 1 | Not yet checked. Written before validation ran. |
| 2 | Interpolated from neighbouring observations rather than measured. |
| 3 | Suspect. Failed at least one check and should be excluded from aggregates. |
| 9 | No reading. The station answered but reported no value. |

A reading carrying flag 3 has failed one of the checks below, and anything built on top of the data should exclude it rather than average it in.

## The checks

The range check rejects a reading outside the station's configured minimum and maximum, which catches a sensor reporting a hardware fault value such as -999.

The spike test compares a reading against the two either side of it and rejects a jump larger than half a metre in six minutes, which is physically implausible at every station in the network.

The continuity test looks for a sequence of identical values, which in practice means a frozen sensor rather than genuinely still water.

## What the flags do not record

Nothing distinguishes an observation written by live ingest from one written by [[sensor-backfill]]. Both carry flags from the same vocabulary. See [[recover-a-data-gap]] and [[station-metadata-schema]].


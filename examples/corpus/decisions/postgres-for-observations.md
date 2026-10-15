---
tags: [decision]
area: platform
created: 2027-01-05
status: accepted
---

# Postgres for Observations

Observations are stored in Postgres rather than in a purpose built time series database.

## Context

The network is around four hundred stations reporting every six minutes, which is roughly ninety six thousand rows per day. The team is three engineers. Query patterns are overwhelmingly recent data for one station, or daily aggregates across a region.

## Decision

Store observations in a single Postgres table partitioned by month, with a composite index on station identifier and observation timestamp. Field definitions are in [[station-metadata-schema]].

## What was rejected

A dedicated time series database was evaluated and rejected. At ninety six thousand rows per day the compression and downsampling advantages are not reachable for years, and the operational cost of a second database for one table was judged higher than the query performance gained. Terms used here are defined in [[glossary]].

## Consequences

Aggregate queries across the whole network for a multi year window are slow and will stay slow. If that pattern becomes common the decision should be revisited rather than worked around with more indexes.


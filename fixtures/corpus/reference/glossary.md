---
tags: [reference]
area: platform
created: 2027-01-08
---

# Glossary

Terms used across the platform notes. Entries are deliberately short.

## Station

One physical tide gauge installation with a fixed location and a stable identifier.

## Observation

A single water level reading from one station at one timestamp.

## Cycle

One complete pass of the collector across every station in the network.

## Collector

The service that polls stations and writes observations. See [[tide-gauge-ingest]].

## Backfill

Fetching historical observations to fill a gap. See [[sensor-backfill]].

## Quality flag

A small integer recording how much confidence a reading carries. See [[quality-flags]].

## Gap

A window during which no observations were recorded for one or more stations.

## Station network file

The configuration listing every station the collector should poll, with its identifier and endpoint. Fields are described in [[station-metadata-schema]].

## Datum

The reference surface a water level is measured against. Two stations reporting the same number are not necessarily at the same height unless they share a datum.


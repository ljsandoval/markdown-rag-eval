---
tags: [reference, schema]
area: platform
created: 2027-01-15
---

# Station Metadata Schema

The fields carried for each station in the station network file and in the `stations` table. See [[glossary]] for the terms.

## Fields

| Field | Type | Nullable | Notes |
|---|---|---|---|
| `station_id` | text | no | Stable identifier, format `MT-NNN`. Never reused, even after a station is decommissioned. |
| `name` | text | no | Human readable, not stable. Do not key anything on it. |
| `latitude` | numeric(8,5) | no | Decimal degrees, WGS84. |
| `longitude` | numeric(8,5) | no | Decimal degrees, WGS84. |
| `datum` | text | no | Reference surface the water level is measured against. |
| `datum_offset_m` | numeric(6,3) | no | Metres between the station datum and the network datum. |
| `endpoint` | text | no | Upstream API path the collector polls. |
| `retention_hours` | integer | no | How long upstream holds observations. Usually 72, sometimes 24. |
| `commissioned_on` | date | no | First day the station reported. |
| `decommissioned_on` | date | yes | Null for active stations. |

## Why datum_offset_m is not optional

Two stations reporting 1.82 metres are not at the same water level unless they share a datum. Every comparison across stations has to go through the offset, so a null would make the comparison silently wrong rather than loudly impossible. The storage decision is [[postgres-for-observations]].


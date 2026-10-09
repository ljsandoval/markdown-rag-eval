---
tags: [decision]
area: platform
created: 2027-02-20
status: accepted
---

# Retire the Kafka Tier

The streaming tier between the collector and Postgres has been removed. The collector now writes directly to the database.

## Context

The original design put a Kafka topic between collection and storage, on the expectation that several consumers would eventually read the observation stream. Fourteen months later there was still exactly one consumer, the database writer.

## Decision

Remove the topic. The collector writes directly to Postgres, as described in [[tide-gauge-ingest]]. The storage decision itself is [[postgres-for-observations]].

## Why

Three reasons, in order of weight.

The tier was carrying no load it needed to carry. One producer and one consumer is a function call wearing a distributed system as a costume.

It was the least reliable component in the pipeline. Two of the three multi hour data gaps in the preceding year originated in the streaming tier rather than in the collector or the database, and in both cases diagnosis was slower because the failure was a consumer lag rather than an error.

It made the write path harder to reason about. With the topic in place, an observation's arrival in Postgres was eventually consistent with its collection, and nothing in the system expressed how eventual.

## What would reverse this

A second genuine consumer of the raw observation stream. Anything that only needs aggregates should read the database instead.


---
tags: [incident]
area: platform
created: 2027-03-14
---

# Collector Outage 2027-03-14

An eleven hour interruption in ingest affecting 104 of 397 stations. Written up by [[avery-lin]].

## Timeline

At 03:12 the collector logged its last successful cycle. The next cycle began at 03:18 as scheduled and did not complete. No error was logged and the process remained alive, holding an open connection to the database and to fourteen stations, which is why every liveness check the team had at the time continued to pass. The service was running, the port was open, and the database connection was established; nothing was being written. The gap went unnoticed until 14:09, when a regional aggregate for the previous twelve hours came back short and an analyst asked whether the number was right. That question, rather than any alert, is what started the investigation. The first ten minutes went into confirming the aggregate was correct and the data was genuinely missing, and another twenty into establishing that the collector process was up, which was initially read as evidence against a collector problem rather than for one. The actual cause was a station that accepted a connection and then never sent a byte. The collector's thirty second timeout covered the case where a station failed to respond to a request, but the read loop had no timeout of its own, so a station that held the connection open without answering parked one worker indefinitely. With fourteen such stations the worker pool was exhausted and the cycle could never complete, while the stations that were answering normally sat in a queue that was never drained. This had happened once before, in September of the previous year, for ninety minutes, and had been recorded as a transient upstream problem because the collector recovered on its own when the station eventually closed the connection. Restarting the collector at 14:41 restored ingest within two minutes. Recovery of the missing window began at 15:00 using the procedure now written up in [[recover-a-data-gap]], and completed for 71 of the 104 stations. The remaining 33 are stations whose upstream retention is twenty four hours rather than seventy two, and by the time the backfill reached them part of the window had already aged out upstream. Roughly four hours of data for those 33 stations is permanently missing and is recorded as such rather than interpolated.

## Contributing factors

Every liveness check tested something other than the thing that mattered. Process alive, port open, and database reachable were all true throughout. Nothing checked whether a row had been written recently, which is the only signal that would have caught this.

The September precedent was closed as transient without anyone asking why a station holding a connection open could stall a cycle at all. A ninety minute version of this outage was available for diagnosis six months earlier and was not used.

## What changed

The read loop now has its own timeout, separate from the connection timeout. The restart procedure is written up in [[restart-the-collector]] and the pipeline note's known limitations section in [[tide-gauge-ingest]] now records that the collector cannot distinguish a station that never reported from one that stopped.

A write recency check is still not built. It is the single highest value thing on the monitoring list and it is not done.


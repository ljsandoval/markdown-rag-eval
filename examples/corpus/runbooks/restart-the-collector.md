---
tags: [runbook]
area: platform
created: 2027-01-20
---

# Restart the Collector

For a collector that has stopped writing, is writing far slower than a ninety second cycle, or is logging repeated station timeouts. Terms are defined in [[glossary]].

## Check before restarting

A restart loses the in flight cycle, so confirm the collector is actually stuck rather than slow.

```bash
# Check status first -- a cycle in progress is not a stuck collector.
## This line is a comment, not a heading, and must not split a chunk.
systemctl status mt-collector
journalctl -u mt-collector --since "15 min ago" | grep -c "cycle complete"
```

Two or more completed cycles in fifteen minutes means it is running normally and the problem is elsewhere.

## Restart

```bash
systemctl restart mt-collector
sleep 120
journalctl -u mt-collector --since "3 min ago" | tail -40
```

A healthy start logs `station network loaded` within ten seconds and `cycle complete` within ninety.

## If it will not start

The two causes seen in practice are an expired database credential and a station network file that failed to parse. Both log at startup and both are fatal rather than degraded, so the service exits rather than running with partial configuration.

If the restart produced a data gap, follow [[recover-a-data-gap]]. The 2027 outage that produced this runbook is written up in [[collector-outage-2027-03-14]].


---
tags: [notes, meeting]
area: platform
created: 2027-03-18
---

Rough notes, typed during the call and not tidied afterwards. Anything agreed here is only agreed until it is written into the note that owns it.

# Weekly Sync 2027-03-18

Present: [[avery-lin]], [[jun-okafor]].

## Outage review

Walked the 2027-03-14 writeup. Agreement that the read timeout fix is sufficient for the specific failure and insufficient for the class of failure, because the detection gap is what turned ninety minutes into eleven hours. Write recency check agreed as the next monitoring work. No date set.

## Backfill limits

Jun raised that the thirty day cap on [[sensor-backfill]] made the outage recovery more tedious than it needed to be, since the recovery was one window across many stations rather than a long window for one station. Agreed to look at a per station batch mode. Not scheduled.

## Retention

Noted that the 33 stations with twenty four hour upstream retention are a standing risk rather than an outage detail: any gap discovered more than a day late is partly unrecoverable for them. No action beyond recording it. Policy is in [[data-retention-policy]].


# Session prompts

The prompt given to each implementation session, kept here rather than retyped.

**Why these are versioned.** A prompt references spec sections and issue numbers, so it only stays coherent if it travels with them — an unversioned prompt pointing at an amended spec goes stale silently. And for a repository whose subject is measurement discipline, how the work was driven is part of the record rather than noise.

**Conventions live in `CLAUDE.md`, not here.** A prompt carries only what is specific to its task: which issue, anything the issue cannot know, and what to report. If a prompt starts restating conventions, they belong in `CLAUDE.md` instead — the first one did, and that is why it was moved.

| Prompt | For |
|---|---|
| `issue-1.md` | Implementing issue #1, the first run through this process |
| `issue-1-closeout.md` | Finishing #1's loop: findings to the issue, spec amendments, rescoping #16 |

One lesson already recorded from `issue-1.md`: it said "report back", which overrode `CLAUDE.md`'s rule that findings go in issue comments. The session reported to chat and the issue got none. **Route the report to the issue and make chat a summary** — the comment is the record.

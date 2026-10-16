---
status: accepted
date: 2026-10-16
supplements: "0003"
---

# 0008. The private measurement artifacts live in the vault's own repository

## Context

ADR 0003 decided that the measurement artifacts stay private. It did not say where private is, and the gap was load-bearing: the spec and `.gitignore` both referred to a "private mirror" that did not exist, and `eval/private/` was only gitignored. The private eval set would have had no copy anywhere but one laptop, which is the same exposure that the Telegram bot's code sat in until 2026-09-10.

Issue #12 could not start without this, because the eval set has to be committed before any retrieval result is seen. Committed where was undefined.

## Decision

The private artifacts live at `~/Assistant/rag-eval/private/`, tracked in the private `assistant` repository that already holds the vault and already pushes to Forgejo on `motarta`.

Three properties make this the right home rather than a new repository:

**The eval set is a fact about the corpus, not a part of the tool.** This is the reasoning ADR 0003 already applies to `.mdragignore`: which notes must not be indexed belongs to the corpus that knows, so the tool reads it rather than carrying it. A question list whose answers are note paths in a particular vault is the same kind of fact. Co-locating it also means a note rename that invalidates an expected path shows up in the same diff as the rename.

**It needs no new infrastructure to be off-machine.** A second private repository would have to be created, remoted and remembered. The vault's repository is private, exists, and is pushed.

**The code is unaffected either way.** `mdrag eval` already takes `--questions PATH` and `--out FILE`, so the location is an argument. This decision moves files; it changes no module.

The directory sits **outside** `obsidian_vaults/brain/` deliberately. Generated YAML and JSON inside the vault folder would show up in Obsidian's file explorer and replicate over Syncthing to the Pi, neither of which anything needs.

## What is committed, and what is not

Split by churn, not by sensitivity - all of it is private either way.

| Artifact | Tracked | Why |
|---|---|---|
| The 25-question eval set | **Committed** | Hand-authored ground truth. The commit timestamp is the evidence it predates the results, which acceptance criterion 3 requires. |
| The failure analysis | **Committed**, as a vault note in `03-Resources/` | It is a document, not an output. It belongs where the other reference notes are. |
| Summary numbers per run | **Committed** | Small, and what gets discussed. |
| Per-question result dumps | **Gitignored** | Regenerable from a pinned `corpus_hash` and `model_revision`, which is what the criterion 8a provenance exists for. Verbatim chunk text at every k, every run, is churn. |

## Consequences

- Issue #12's blocker is removed. Its remaining work is writing the questions.
- Reproducing a reported number requires the private repository, so the README's "not reproducible by others" claim is unchanged and still has to be stated plainly.
- The public repo keeps no `eval/private/` directory at all. An empty gitignored path invites someone to put a private file in a public repo and trust a one-line rule; no path is safer than a trusted one.
- If the artifacts ever need to be shared with someone who has the vault but not this laptop, they travel with the vault, which is the correct coupling.

## Alternatives rejected

**A new private Forgejo repository under `~/code/personal/`.** The original assumption, and the reason it stalled. It treats the artifacts as code when they are measurements of a corpus, puts them next to repos they have nothing to do with, and needs setup before the eval set can be written. It also solves nothing the vault repository does not, since both are private and both push to the same host.

**Inside the vault folder, as notes.** The eval set is YAML consumed by a validator; writing it as markdown to satisfy Obsidian would mean parsing prose. Rejected for the generated files on the Syncthing and file-explorer noise above.

**Keep gitignoring `eval/private/` in the public repo.** The status quo, and the thing this ADR exists to end. One editing mistake or one `git add -f` puts private note paths in a public repository permanently.

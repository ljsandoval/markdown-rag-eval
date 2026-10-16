/*
 * Export Obsidian's own link resolution as ground truth.
 *
 * `app.metadataCache.resolvedLinks` is the authoritative resolver for a vault:
 * it is what Obsidian itself navigates by. The spec requires validating this
 * project's wikilink resolution against it rather than against a second
 * reimplementation, which would only prove the two agree with each other.
 *
 * HOW TO RUN
 *
 * 1. Open the vault you want to measure in Obsidian desktop. The snippet reads
 *    whichever vault is in front, so click into that window first.
 * 2. Cmd+Option+I (Ctrl+Shift+I on Windows and Linux) opens DevTools. Choose
 *    the Console tab.
 * 3. DevTools blocks the first paste into a console it does not trust: it asks
 *    you to type `allow pasting` and press Enter. Once per browser profile.
 * 4. Edit EXCLUDE below to mirror the corpus's `.mdragignore`, paste the whole
 *    file, press Enter. The last line logs the source and edge counts.
 * 5. The file lands at the vault root. Move it to wherever the corpus's private
 *    measurement artifacts live - it carries note paths, so for a private
 *    corpus it does not belong in a public repository.
 *
 * WAIT FOR THE CACHE. On a cold start Obsidian is still parsing, and
 * resolvedLinks fills in progressively with no error to say it is incomplete.
 * Check `Object.keys(app.metadataCache.resolvedLinks).length` against the
 * vault's note count first; re-run after a few seconds if it is short.
 *
 * WHAT YOU GET
 *
 *   resolved[source][target]  = count   // target is a real resolved file path
 *   unresolved[source][text]  = count   // key is the link text as written
 *
 * Both are keyed by vault-relative path including the `.md` extension, and both
 * aggregate by pair with a count. Keep the counts: a rule that double-counts a
 * link leaves every pair intact while changing its multiplicity, so a
 * comparison reduced to target sets cannot see that class of bug at all.
 *
 * WHAT IT CANNOT SEE: cross-boundary links. A link from a kept note to an
 * EXCLUDEd note is resolved by Obsidian and then dropped by the target filter,
 * so it appears in neither map. Anything reconciling totals against a
 * Python-side count has to account for them separately.
 */

const EXCLUDE = [/^00-Raw\//, /^private\//, /^Templates\//, /^CLAUDE\.md$/];
const keep = (p) => p.endsWith('.md') && !EXCLUDE.some((re) => re.test(p));

const pick = (obj, filterTargets) => {
  const out = {};
  for (const [src, targets] of Object.entries(obj)) {
    if (!keep(src)) continue;
    const kept = Object.entries(targets)
      .filter(([t]) => !filterTargets || keep(t))
      .sort(([a], [b]) => a.localeCompare(b));
    if (kept.length) out[src] = Object.fromEntries(kept);
  }
  return out;
};

const out = {
  exported: new Date().toISOString(),
  obsidian_version: app.appVersion ?? null,
  notes_in_vault: app.vault.getMarkdownFiles().length,
  exclude_patterns: EXCLUDE.map(String),
  resolved: pick(app.metadataCache.resolvedLinks, true),
  unresolved: pick(app.metadataCache.unresolvedLinks, false),
};

await app.vault.adapter.write(
  'obsidian-resolved-links.json',
  JSON.stringify(out, null, 2)
);

console.log(
  'sources:', Object.keys(out.resolved).length,
  'edges:', Object.values(out.resolved)
    .reduce((n, t) => n + Object.values(t).reduce((a, b) => a + b, 0), 0)
);

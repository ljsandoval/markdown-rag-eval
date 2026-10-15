# Test fixtures

Small, artificial inputs that exercise one code path each. Built for coverage, not for looking realistic.

**This is not the example corpus.** `examples/corpus/` is realistic, frozen, and published; it exists to prove the code runs and to let anyone reproduce a demo. The two have conflicting requirements, which is why they are separate directories — and why the thing in `examples/` is no longer called a fixture. See ADR 0007.

Add inputs here freely. Nothing published depends on them, so they are not frozen, and they should be as small and as ugly as the case requires. A file here exercising exactly one wikilink edge case with three lines of content is doing its job.

Prefer `tmp_path` for anything a single test constructs. Use a committed file here when the input is fiddly enough that building it inline would obscure the test.

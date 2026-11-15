# UT PoC execution ledger

Plan: 2026-11-15-unit-test-spec-poc.md. User explicitly requested execution on 2026-11-15.

- Scope: new unit-test specification package/job; preserve upstream code/spec and legacy packages.
- Ruling: isolate writes in new package/artifact directories in the shared workspace; .git is read-only, so no branch/worktree metadata is changed.
- Ruling: use Word/A4 per accepted execution plan and existing OfficeCLI backend. New document template, fixed after maintenance build.
- Ruling: fresh-context author sees only source specification/C/H and fixed contract; legacy C tests are compared only after authoring freeze. Main coordinator has prior history, so this is procedural separation rather than statistical independence.
- Ruling: actual generator initially Codex. Bob IDE execution will be attempted separately without changing auth/auto-approval; if unavailable, label that acceptance pending.
- Started: canonical contract and parallel ownership assigned. No implementation results claimed yet.

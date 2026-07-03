# Indico patch helper — retired

> [!NOTE]
> **`scripts/indico_patch.py` has been retired.** The external
> HTTP-write path it reverse-engineered is superseded by the
> `netsec-dispatch` Indico plugin's CLI. This page is kept as a
> stable landing spot for inbound links; the operational guide now
> lives in [`docs/indico-integration.md`](indico-integration.md)
> (Phase 2).

## What replaced it

Fix-plans are applied server-side through the plugin CLI, which runs
the corrections through Indico's own Python API inside a database
transaction — no CSRF, no wtforms scraping, no undocumented HTTP
endpoints:

```bash
ssh <vps> indico netsec apply-fixplan data/indico-fix-plans/YYYY-MM-DD-foo.yaml --dry-run
ssh <vps> indico netsec apply-fixplan data/indico-fix-plans/YYYY-MM-DD-foo.yaml
```

The **YAML fix-plan schema is unchanged** — the same `kind` / `by` /
`ref` / `set` files that `indico_patch.py` read still apply verbatim
(the plugin kept the schema byte-for-byte). See
[`data/indico-fix-plans/README.md`](../data/indico-fix-plans/README.md)
for authoring and the current apply workflow, and
[`data/indico-fix-plans/EXAMPLE.yaml`](../data/indico-fix-plans/EXAMPLE.yaml)
for the canonical reference.

Because the writes go through Indico's operations layer, a successful
apply fires the same lifecycle signals the Phase 1 push pipeline
listens for, so a fix-plan apply refreshes the live site with no manual
sync step.

## Where the history lives

- The retired tool, its ~950-line source, its test suite, and the full
  Phase 1 / Phase 1.5 endpoint reverse-engineering findings (the
  admin-flag unlock, the wtforms vs. clean-JSON route map, the
  read-back verification and pre-flight machinery) live in this
  repository's **git history**.
- Rationale and design: **#210** (the original write-side work) and
  **#323** (the read-back / verification / scope reverse-engineering,
  now fully superseded).
- The re-scope and end-to-end validation record for the replacement:
  **#824**.

## Where the replacement lives

- Plan and phasing:
  [`docs/indico-integration.md`](indico-integration.md) — Phase 2.
- Implementation: the
  [`netsec-indico-dispatch`](https://github.com/EISSeuropa/netsec-indico-dispatch)
  repository (`indico_netsec_dispatch/cli.py` + `fixplan.py`); see that
  repo's README for install and invocation.

## Companion tool: `scripts/indico_clean_duplicate.py`

The ESSC-N → ESSC-N+1 duplicate-cleanup script
(`scripts/indico_clean_duplicate.py`) is **not** retired. It removes
inherited content (contributions, sessions) from a freshly duplicated
event so friendly-ID counters reset, via read + `DELETE` against the
management API. It shares the admin-flagged-bot / `INDICO_WRITE_TOKEN`
precondition described above but is self-contained and is the only
remaining consumer of that token. See the script's own docstring for
usage and the `PROTECTED_EVENTS` safety net.

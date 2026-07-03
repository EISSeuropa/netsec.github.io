# Indico fix-plans

This folder holds committed YAML "fix-plans" — small files describing
metadata corrections to apply against the live Indico instance.

Fix-plans are applied by the `netsec-dispatch` Indico plugin's CLI,
`indico netsec apply-fixplan`, which runs the corrections server-side
through Indico's own Python API inside a single database transaction.
(This replaced the external `scripts/indico_patch.py` tool — retired
in #824; see [`docs/indico-patch.md`](../../docs/indico-patch.md) and
[`docs/indico-integration.md`](../../docs/indico-integration.md)
Phase 2. The **YAML schema below is unchanged**, so existing plans
apply verbatim.)

## Workflow

1. **Author a fix-plan.** Name it `YYYY-MM-DD-short-slug.yaml`. See
   `EXAMPLE.yaml` for the schema.
2. **Dry-run.** `ssh <vps> indico netsec apply-fixplan
   data/indico-fix-plans/YYYY-MM-DD-short-slug.yaml --dry-run` — the
   plugin resolves friendly IDs (e.g. "session 43", "Julia Carver") to
   internal database IDs via the ORM and prints what it would do,
   without writing.
3. **Eyeball + commit** the YAML. The committed file is the audit
   trail for the change.
4. **Apply.** Re-run without `--dry-run`. The whole plan applies in one
   transaction; any resolution failure, apply error, or read-back
   mismatch rolls the entire plan back and exits non-zero, so nothing
   is left half-applied.
5. **Site refresh is automatic.** Because the writes go through
   Indico's operations layer, the apply fires the Phase 1 lifecycle
   signals and triggers a `repository_dispatch` sync, refreshing the
   live site within a couple of minutes — no manual `sync-indico.py`
   step. The daily sync remains the fallback.

## Required env

The apply runs inside Indico on the VPS, so it needs no token in this
repo's CI. (The retired external tool required `INDICO_WRITE_TOKEN`;
that is no longer used by the fix-plan path.)

## Why this exists

Tracked in #210, and re-based onto the plugin in #824. Spring 2026's
ESSC prep cycle surfaced a recurring pattern: the authoritative
programme document (organisers' internal PDF) drifts from the live
Indico instance — wrong rooms, typoed titles, missing affiliations.
Hand-fixing six items in the UI took the admin about an hour. With a
fix-plan + the plugin CLI it's a couple of minutes.

Applying fix-plans is deliberately **not** part of the daily CI sync.
Writes are destructive and occasional; reads run every day. Different
blast radius → different tool.

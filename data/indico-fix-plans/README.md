# Indico fix-plans

This folder holds committed YAML "fix-plans" — small files describing
metadata corrections to apply against the live Indico instance.

## Workflow

1. **Author a fix-plan.** Name it `YYYY-MM-DD-short-slug.yaml`. See
   `EXAMPLE.yaml` for the schema.
2. **Dry-run.** `python3 scripts/indico_patch.py
   data/indico-fix-plans/YYYY-MM-DD-short-slug.yaml` — no `--apply`
   flag, no writes. The script resolves friendly IDs (e.g. "session
   43", "Julia Carver") to internal database IDs by querying the
   live read API and prints what it would do. The resolved IDs are
   written back into the YAML alongside the friendly refs, so
   subsequent runs skip the resolution step.
3. **Eyeball + commit** the YAML. The committed file is the audit
   trail for the change.
4. **Apply.** Re-run with `--apply`. Hits the write endpoints.
5. **Wait for daily sync.** The next `sync-indico.py` run pulls the
   corrected state into `data/indico.json`.

## Required env

- `INDICO_WRITE_TOKEN` — personal token from Indico with scope
  `full:everything`. Generated via Indico → My Profile → API Tokens.
  Stored as a GitHub Actions secret (same name).

## Why this exists

Tracked in #210. Spring 2026's ESSC prep cycle surfaced a recurring
pattern: the authoritative programme document (organisers' internal
PDF) drifts from the live Indico instance — wrong rooms, typoed
titles, missing affiliations. Hand-fixing six items in the UI took
the admin about an hour. With a fix-plan + this script it's two
minutes.

The script intentionally **isn't** part of the daily CI sync. Writes
are destructive and occasional; reads run every day. Different blast
radius → different tool.

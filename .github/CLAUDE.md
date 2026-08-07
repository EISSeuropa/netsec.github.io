# Release infrastructure (`.github/`)

Loaded when working under `.github/`. Moved out of the root `CLAUDE.md` so it
costs no per-session context, following the pattern §15 already uses for
`docs/claude-usage.md`.

## Release-infrastructure hygiene

Three conventions on the `.github/` tree, codified together so the
next maintainer inherits them rather than rederiving from
`anthropics/claude-code`'s shape (which is where these came from
in May 2026).

### SHA-pin third-party Actions

Every `uses:` line in `.github/workflows/*.yml` that references
a third-party action (anyone other than `actions/*` shipped by
GitHub) pins to a commit SHA, with a trailing `# vN (sha-pinned)`
comment for human readability:

```yaml
uses: peter-evans/create-pull-request@22a9089034f40e5a961c8808d113e2c98fb63676  # v7 (sha-pinned)
```

For consistency the convention covers `actions/*` too, even
though those are first-party. Dependabot continues to surface
updates via PR and bumps the SHA explicitly each time. Resolve
a fresh SHA with:

```bash
gh api repos/<owner>/<repo>/commits/<tag> --jq '.sha'
```

Don't paste a tag without a SHA. The CI bypass exists exactly to
keep workflows running under the permissions we already granted,
so a tag-based supply-chain compromise inherits those permissions
on the next sync.

### Issue templates are YAML forms, not free-form markdown

External contributors filing through the GitHub UI land on one
of three structured forms in `.github/ISSUE_TEMPLATE/`:
`bug_report.yml`, `enhancement.yml`, `documentation.yml`. The
chooser's `config.yml` sets `blank_issues_enabled: false` and
routes routine questions to the public site and the Wiki.

When adding a new template, follow the existing form-schema
shape: required preflight checkboxes (search existing, single
report), required textareas for the substantive content, and a
`labels:` block that auto-applies the matching label.

Maintainer-authored issues filed via `gh issue create` (the
common path for mid-session follow-up work) still use the
four-section body shape from rule §3: *What's happening / Why
it matters / Fix path / Target*. The forms enforce the same
shape on external contributors.

### Lifecycle-label vocabulary

Four labels drive the automated lifecycle workflows:

| Label | Applied when | What fires |
| --- | --- | --- |
| `needs-info` | The maintainer asks the reporter for more details. | `issue-lifecycle-comment.yml` posts the standard ask + the 14-day clock notice. `issue-sweep.yml` closes the issue if no human comment lands in 14 days. |
| `stale` | An open issue has 60+ days of no activity. | Auto-applied by `issue-sweep.yml`. `issue-lifecycle-comment.yml` posts the 14-day-to-close warning. Closes after another 14 days unless someone comments. |
| `duplicate` | The maintainer closes a duplicate of another issue. | `issue-lifecycle-comment.yml` posts the standard close message pointing at the original. |
| `wontfix` | The maintainer closes without acting on the request. | `issue-lifecycle-comment.yml` posts the standard close message recording the reasoning context. |

Issues stay open under `needs-info` and `stale` while the
clocks run. The `issue-sweep.yml` workflow runs once daily and
the `lock-closed-issues.yml` workflow locks any closed issue
14 days after closure (drive-by comment prevention).

When adding a new lifecycle label, update the `messages`
dictionary in `issue-lifecycle-comment.yml` and the table
above. Labels not in the dictionary are silently ignored by
the workflow, so a forgotten update is non-fatal.

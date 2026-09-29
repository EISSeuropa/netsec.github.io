# Release infrastructure (`.github/`)

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

Three labels drive the automated lifecycle workflows:

| Label | Applied when | What fires |
| --- | --- | --- |
| `needs-info` | The maintainer asks the reporter for more details. | `issue-lifecycle-comment.yml` posts the standard ask + the 60-day clock notice. `issue-sweep.yml` closes the issue if no human comment lands in 60 days. |
| `duplicate` | The maintainer closes a duplicate of another issue. | `issue-lifecycle-comment.yml` posts the standard close message pointing at the original. |
| `wontfix` | The maintainer closes without acting on the request. | `issue-lifecycle-comment.yml` posts the standard close message recording the reasoning context. |

Nothing else expires: an open issue is never closed for inactivity
(the 60-day `stale` close was removed after it shut real backlog
items). Issues stay open under `needs-info` while its clock runs. The `issue-sweep.yml` workflow runs once daily and
the `lock-closed-issues.yml` workflow silently locks any closed
issue after 14 days without activity (no bot comment).

When adding a new lifecycle label, update the `messages`
dictionary in `issue-lifecycle-comment.yml` and the table
above. Labels not in the dictionary are silently ignored by
the workflow, so a forgotten update is non-fatal.
